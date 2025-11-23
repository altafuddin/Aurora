# In: logic/ielts_logic.py

from typing import List, Dict
import gradio as gr
import logging
import time
from .ielts_models import IELTSState, SessionPhase, IELTSFeedback, IELTSFinalReport, IELTSAnswer
from .audio_models import AzurePronunciationReport
from .session_models import StreamingSessionState
from .prompts import create_structured_part_feedback_prompt, create_final_report_prompt
from utils.ielts_utils import format_feedback_for_display, format_transcript_text, format_prior_feedback, format_final_report_for_display  

def format_answers_with_scores(answers_dict: Dict[str, List[IELTSAnswer]]) -> str:
    """
    Formats all user answers, including their audio scores, into a single
    string for the LLM prompt.
    """
    full_transcript_blocks = []
    
    for part_num in range(1, 4):
        part_key = f"part{part_num}"
        if answers_dict[part_key]:
            full_transcript_blocks.append(f"--- Part {part_num} Answers ---")
            for answer in answers_dict[part_key]:
                report = answer.pronunciation_report
                fluency = "N/A"
                accuracy = "N/A"
                if report and report.primary_result:
                    fluency = report.primary_result.assessment.fluency_score
                    accuracy = report.primary_result.assessment.accuracy_score
                
                block = (
                    f"Question: {answer.question}\n"
                    f"Transcript: \"{answer.transcript}\"\n"
                    f"Audio Analysis:\n"
                    f"  - Fluency Score: {fluency}\n"
                    f"  - Pronunciation Accuracy Score: {accuracy}"
                )
                full_transcript_blocks.append(block)
    
    return "\n\n".join(full_transcript_blocks)

def start_ielts_test(question_bank) -> IELTSState:    
    """Creates and returns a new IELTSState object for a fresh test."""
    test_questions = question_bank.get_random_test()
    first_question = test_questions["part1"]["questions"][0]
    
    new_state = IELTSState(
        questions=test_questions,
        current_part=1,
        current_question_index=0,
        test_started=True,
        current_question_text=first_question,
        session_phase=SessionPhase.IN_PROGRESS
    )
    return new_state

def format_transcript_text(answers_dict: Dict[str, List[IELTSAnswer]]) -> str:
    """Formats the user's answers from the state for display in the UI."""
    answer_blocks = []
    for part_num in range(1, 4):
        part_key = f"part{part_num}"
        if answers_dict[part_key]:
            formatted_answers = [answer.formatted_text for answer in answers_dict[part_key]]
            block = f"--- Part {part_num} Answers ---\n" + "\n\n".join(formatted_answers)
            answer_blocks.append(block)

    return "\n\n---\n\n".join(answer_blocks) if answer_blocks else ""

def process_answer(current_state: IELTSState, report: AzurePronunciationReport):
    """
    Processes a new answer, adds it to the state, and updates the question index.
    Returns the updated state.
    """
    # Check if test is started
    if not current_state.test_started or not current_state.questions:
        logging.error("process_answer called on an inactive or invalid test state.")
        return current_state

    # Create and store the new IELTSAnswer object
    transcript = report.display_text
    part_key = f"part{current_state.current_part}"
    
    new_answer = IELTSAnswer(
        question=current_state.current_question_text,
        transcript=transcript,
        pronunciation_report=report,
        formatted_text=f"**Q:** {current_state.current_question_text}\n\n**A:** {transcript}"
    )
    # Append the transcript to the answers
    current_state.answers[part_key].append(new_answer)

    if not current_state.is_last_question_of_part:
        current_state.current_question_index += 1
        questions_in_part = current_state.questions[part_key]["questions"]
        current_state.current_question_text = questions_in_part[current_state.current_question_index]
    else:
        logging.info(f"End of Part{part_key}")
        current_state.session_phase = SessionPhase.PART_ENDED
        current_state.current_question_text = f"**End of Part {current_state.current_part}**"

    return current_state

# --- Continue to Next Part Functionality ---    
def continue_to_next_part(current_state: IELTSState):
    """
    Transitions the test to the next part after a user decides to continue.
    """

    # Guard clause: Ensure questions is not None
    if not current_state.questions:
        return current_state
    
    # Show the recording interface and hide final report button
    generate_final_report = False
    show_recording = True
    
    # Logic to transition from Part 1 to Part 2
    if current_state.current_part == 1:
        current_state.current_part = 2
        logging.info("Transitioning from Part 1 to Part 2")
        current_state.current_question_index = 0
        current_state.session_phase = SessionPhase.IN_PROGRESS
        cue_card_info = current_state.questions['part2']
        current_state.current_question_text = (
            f"**Part 2**\n\n**Topic:** {cue_card_info['topic']}\n\n"
            f"{cue_card_info['cue_card']}\n\n"
            f"*You have 1 minute to prepare, then speak for 1-2 minutes.*"
        )
    # Logic to transition from Part 2 to Part 3
    elif current_state.current_part == 2:
        logging.info("Transitioning from Part 2 to Part 3")
        current_state.current_part = 3
        current_state.current_question_index = 0
        current_state.session_phase = SessionPhase.IN_PROGRESS
        part3_info = current_state.questions['part3']
        current_state.current_question_text = f"**Part 3: {part3_info['topic']}**\n\n{part3_info['questions'][0]}"
    else:
        # This block is reached after the user finishes Part 3 and clicks "Continue".
        current_state.session_phase = SessionPhase.TEST_COMPLETED
        current_state.current_question_text = "### Test Completed!\n\nYou have now completed all three parts of the test. Click the button below to generate your final comprehensive report."
        logging.info("Test Completed!")


    return current_state

# --- Reset Functionality ---
def reset_test():
    """Resets the UI and the state to its initial condition."""
    # Return a new, empty IELTSState object to fully reset the state
    return (
        IELTSState(),
        gr.update(visible=True),   # 1. start_button
        gr.update(visible=False),  # 2. reset_button
        gr.update(visible=False),  # 3. test_interface
        "Click 'Start Test' to begin a new IELTS Speaking simulation.",  # 4. question_display
        "",                        # 5. transcripts_display
        gr.update(visible=False),  # 6. recording_interface
        gr.update(visible=False),  # 7. feedback_buttons
        gr.update(value="", visible=False)  # 8. feedback_display
    )

# --- Generate Feedback Functionality ---
def generate_feedback(current_state: IELTSState, llm_service):
    """
    Orchestrates the process of getting, parsing, and displaying IELTS feedback.
    """
    start_time = time.time()
    part_key = f"part{current_state.current_part}"
    answers_for_part = current_state.answers[part_key]
    # Check if there are answers for the current part
    if not answers_for_part:
        yield (
            current_state,
            gr.update(value="Error: No answers were provided to generate feedback.", visible=True),
            gr.update(interactive=False, visible=True),
            gr.update(interactive=False, visible=True)
        )
        return
    
    # Set the session phase to show the app is "busy"
    current_state.session_phase = SessionPhase.GENERATING_FEEDBACK

    # 1. Set a "loading" state for the UI
    yield (
        current_state, 
        gr.update(value="Generating feedback, please wait...", visible=True), # For ielts_feedback_display
        gr.update(interactive=False, visible=True), # Disable feedback button to prevent double-clicks
        gr.update(interactive=False, visible=True)  # Disable continue button
    )

    # Check for a previously generated report for this part
    if stored_report := current_state.feedback_reports.get(part_key):
        print(f"LOG: Found cached feedback for {part_key}. Displaying now.")
        report_markdown = format_feedback_for_display(stored_report)
        yield (
            current_state,
            gr.update(value=report_markdown, visible=True),
            gr.update(interactive=True),
            gr.update(interactive=True)
        )
        return
        
    # 2. Prepare data for the prompt
    questions_and_answers = "Haven't worked on this part, cant give feedback now"  #"\n\n".join(answers_for_part) 
    part_number = current_state.current_part

    # 3. Create the detailed, structured prompt
    prompt = create_structured_part_feedback_prompt(part_number, questions_and_answers)

    # 4. Call the LLM service to get structured feedback
    feedback_result = llm_service.get_structured_feedback(prompt)

    # --- Process the result ---
    if isinstance(feedback_result, IELTSFeedback):

        # Success! We got a valid, structured feedback object.
        part_key = f"part{current_state.current_part}"
        current_state.feedback_reports[part_key] = feedback_result

        # Reset the phase to indicate the part has ended
        current_state.session_phase = SessionPhase.PART_ENDED
        # Format the structured data into nice Markdown for display
        report = format_feedback_for_display(feedback_result)
        
        yield (
            current_state,
            gr.update(value=report, visible=True), # Show the formatted feedback
            gr.update(interactive=True, visible=True), # Re-enable feedback button
            gr.update(interactive=True, visible=True)  # Re-enable continue button
        )
        elapsed = time.time() - start_time
        logging.info(f"TIMING: generate_feedback completed in {elapsed:.2f}s")
    else:
        # Reset the phase even if there's an error
        current_state.session_phase = SessionPhase.PART_ENDED
        # Failure. The service returned an error string.
        error_message = feedback_result
        yield (
            current_state,
            gr.update(value=error_message, visible=True), # Show the error message
            gr.update(interactive=True, visible=True), # Re-enable feedback button
            gr.update(interactive=True, visible=True)  # Re-enable continue button
        )

def calculate_overall_band_score(scores: list[float]) -> float:
    """Calculates and rounds the overall band score according to IELTS rules."""
    if not scores:
        return 0.0
    average = sum(scores) / len(scores)
    # Round to the nearest 0.5
    return round(average * 2) / 2

def generate_final_report(current_state: IELTSState, llm_service):
    """
    Orchestrates the generation of the final, comprehensive IELTS report.
    """
    start_time = time.time()
    # --- Step 1: Caching Logic ---
    if current_state.final_report:
        print("LOG: Found cached final report. Displaying now.")
        report_markdown = format_final_report_for_display(current_state.final_report)
        yield (
            current_state, 
            gr.update(value=report_markdown, visible=True), 
            gr.update(interactive=True)
        )
        return
    
    # Set the session phase to indicate the app is busy generating the final report.
    current_state.session_phase = SessionPhase.GENERATING_FEEDBACK
    
    # 1. First `yield` to update the UI with a loading state.
    yield (
        current_state,
        gr.update(value="⏳ Generating your final comprehensive report, please wait...", visible=True),
        gr.update(interactive=False)
    )

    # 2. Prepare the data for the prompt using our utility functions.
    # 1. Format the detailed, answer-by-answer data string
    answers_with_scores_str = format_answers_with_scores(current_state.answers)
    # full_transcript = format_transcript_text(current_state.answers)
    # 2. Format the prior qualitative feedback reports
    prior_feedback_str = format_prior_feedback(current_state.feedback_reports)

    # 3. Calculate the overall average scores as a summary
    all_reports = [
        answer.pronunciation_report for part in current_state.answers.values() 
        for answer in part if answer.pronunciation_report and answer.pronunciation_report.primary_result
    ]

    if all_reports:
        avg_fluency = sum(r.primary_result.assessment.fluency_score for r in all_reports if r.primary_result) / len(all_reports)
        avg_accuracy = sum(r.primary_result.assessment.accuracy_score for r in all_reports if r.primary_result) / len(all_reports)
        summary_scores_str = (
            f"Overall Average Fluency Score: {avg_fluency:.2f}\n"
            f"Overall Average Pronunciation Accuracy Score: {avg_accuracy:.2f}"
        )
    else:
        summary_scores_str = "No audio analysis data available."
    

    # 3. Create the final "mega-prompt".
    prompt = create_final_report_prompt(
        answers_with_scores=answers_with_scores_str,
        summary_scores=summary_scores_str,
        prior_feedback_reports=prior_feedback_str
    )

    # 4. Call the LLM service.
    final_report_result = llm_service.get_final_report(prompt)

    # Reset the phase, as the process is complete.
    current_state.session_phase = SessionPhase.TEST_COMPLETED

    if isinstance(final_report_result, IELTSFinalReport):
        # --- Step 5a (REFINEMENT): Perform our own calculation ---
        scores_to_average = [
            final_report_result.estimated_scores.fluency_and_coherence.score,
            final_report_result.estimated_scores.lexical_resource.score,
            final_report_result.estimated_scores.grammatical_range_and_accuracy.score,
            final_report_result.estimated_scores.pronunciation.score
        ]
        calculated_overall_score = calculate_overall_band_score(scores_to_average)
        
        # Override the LLM's calculation with our reliable one.
        final_report_result.overall_band_score = calculated_overall_score

        # Success! Store and format the report.
        current_state.final_report = final_report_result
        report_markdown = format_final_report_for_display(final_report_result)

        yield (
            current_state,
            gr.update(value=report_markdown, visible=True),
            gr.update(interactive=True)
        )
        elapsed = time.time() - start_time
        logging.info(f"TIMING: generate_final_report completed in {elapsed:.2f}s")
    else:
        # Failure. The service returned an error string.
        error_message = final_report_result
        yield (
            current_state,
            gr.update(value=error_message, visible=True),
            gr.update(interactive=True)
        )