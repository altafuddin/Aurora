# In: logic/ielts_logic.py

from typing import List, Dict
import gradio as gr
from .ielts_models import IELTSState, SessionPhase, IELTSFeedback, IELTSFinalReport, IELTSAnswer
from .prompts import create_structured_part_feedback_prompt, create_final_report_prompt
from utils.ielts_utils import format_feedback_for_display, format_transcript_text, format_prior_feedback, format_final_report_for_display  


def start_ielts_test(question_bank):
    """Initializes a new IELTS test session."""
    try:
        test_questions = question_bank.get_random_test()
        # Unpack the first question for immediate display
        first_question = test_questions["part1"]["questions"][0]  
        
        # Create a new instance of  dataclass with initial values
        new_state = IELTSState(
            questions=test_questions,
            current_part=1,
            current_question_index=0,
            test_started=True,
            current_question_text=first_question,
            session_phase=SessionPhase.IN_PROGRESS
        )
        
        # The formatted question for display
        formatted_question = f"**Part 1: {test_questions['part1']['topic']}**\n\n{first_question}"

        return (
            new_state,                      # >> Return the dataclass object as state
            gr.update(visible=False),       # Hide "Start Test" button
            gr.update(visible=True),        # Show the reset button
            gr.update(visible=True),        # Show the test interface
            formatted_question,
            "",
            gr.update(visible=True),         # Show recording interface
            gr.update(visible=False)        # Ensure feedback buttons are hidden
        )
    except Exception as e:
        error_message = f"Error starting test: {str(e)}"
        return (
            IELTSState(),                   # >> Return a default state on error
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            error_message,
            "",
            gr.update(visible=False),
            gr.update(visible=False)        # Hide feedback buttons on error
        )

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

def process_answer(user_audio, current_state: IELTSState, speech_service):
    """Processes a user's answer and determines the next state of the test."""
    # Check if test is started
    if not current_state.test_started:
        return (
            current_state,
            "Please start the test first.", 
            "", 
            gr.update(visible=True), 
            gr.update(visible=False)
        )

    # Check if it's the last question of the part BEFORE processing
    is_part_ending = current_state.is_last_question_of_part

    if not user_audio:
        # If no audio is provided, return the current state and question text
        transcript_text = format_transcript_text(current_state.answers)
        return (
            current_state,
            current_state.current_question_text,
            transcript_text,
            gr.update(visible=True),
            gr.update(visible=False)
        )

    # Guard clause: Ensure questions is not None
    if not current_state.questions:
        return (
            current_state,
            "Error: No questions loaded. Please restart the test.",
            "",
            gr.update(visible=False),
            gr.update(visible=False)
        )

    try:
        # Transcribe the user's audio input
        # 1. Call the new Azure service to get the full report
        report = speech_service.get_pronunciation_assessment(user_audio)

        # 2. Handle errors from the service
        if not report or report.recognition_status != "Success":
            error_message = "Sorry, I couldn't recognize any speech. Please try again."
            if report:
                error_message = f"Audio Error: {report.recognition_status}"
            # Even on error, we need to format the existing transcript for display
            transcript_text = format_transcript_text(current_state.answers)
            return (
                current_state, 
                current_state.current_question_text,
                transcript_text, 
                gr.update(), 
                gr.update())
        
        # 3. Create and store the new IELTSAnswer object
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

        # Format the transcript text for display
        transcript_text = format_transcript_text(current_state.answers)
        if transcript_text.startswith("Error:"):
            return (
                current_state,
                current_state.current_question_text,
                transcript_text,
                gr.update(visible=True),
                gr.update(visible=False)
            )

        # Handle the end-of-part case and return immediately.
        if is_part_ending:
            current_state.session_phase = SessionPhase.PART_ENDED
            next_question_text = f"**End of Part {current_state.current_part}**\n\nWhat would you like to do next?"
            # Hide recording interface, show feedback buttons
            return (
                current_state, 
                next_question_text, 
                transcript_text,  # Display all answers
                gr.update(visible=False), 
                gr.update(visible=True)
            )

        # --- If it's not the end of a part, determine the next question ---
        # This block will therefore primarily run for Part 1 and Part 3.
        current_state.current_question_index += 1
        part_key = f"part{current_state.current_part}"
        questions_in_part = current_state.questions[part_key]["questions"]
        next_question_text = questions_in_part[current_state.current_question_index]                      
        current_state.current_question_text = next_question_text       
        
        return (
            current_state,
            f"**Part {current_state.current_part}: {current_state.questions[f'part{current_state.current_part}']['topic']}**\n\n{next_question_text}",
            transcript_text, # Display all answers
            gr.update(visible=True),  # Show recording interface
            gr.update(visible=False)  # Hide feedback buttons after answering a question
        )
        
    except Exception as e:
        return (
            current_state,
            current_state.current_question_text,
            f"Error processing answer: {str(e)}",
            gr.update(visible=True),
            gr.update(visible=False)
        )

# --- Continue to Next Part Functionality ---    
def continue_to_next_part(current_state: IELTSState):
    """
    Transitions the test to the next part after a user decides to continue.
    """

    # Guard clause: Ensure questions is not None
    if not current_state.questions:
        return (
            current_state,
            "Error: No questions loaded. Please restart the test.",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(visible=False)
        )
    
    # Show the recording interface and hide final report button
    generate_final_report = False
    show_recording = True
    
    # Logic to transition from Part 1 to Part 2
    if current_state.current_part == 1:
        current_state.current_part = 2
        current_state.current_question_index = 0
        current_state.session_phase = SessionPhase.IN_PROGRESS
        
        # Prepare the Part 2 cue card
        next_question_text = (
            f"**Part 2**\n\n"
            f"**Topic:** {current_state.questions['part2']['topic']}\n\n"
            f"{current_state.questions['part2']['cue_card']}\n\n"
            f"*You have 1 minute to prepare, then speak for 1-2 minutes.*"
        )

    # Logic to transition from Part 2 to Part 3
    elif current_state.current_part == 2:
        current_state.current_part = 3
        current_state.current_question_index = 0
        current_state.session_phase = SessionPhase.IN_PROGRESS
        
        # Prepare the first question of Part 3
        part3_topic = current_state.questions['part3']['topic']
        first_part3_question = current_state.questions['part3']['questions'][0]
        next_question_text = f"**Part 3: {part3_topic}**\n\n{first_part3_question}"
    
    else:
        # This block is reached after the user finishes Part 3 and clicks "Continue".
        current_state.session_phase = SessionPhase.TEST_COMPLETED
        next_question_text = "### Test Completed!\n\nYou have now completed all three parts of the test. Click the button below to generate your final comprehensive report."
        show_recording = False
        generate_final_report = True

    current_state.current_question_text = next_question_text
    
    return (
        current_state,
        next_question_text,                       # Update question_display
        gr.update(visible=show_recording),        # Hide recording_interface
        gr.update(visible=False),                 # Hide feedback_buttons
        gr.update(value="", visible=False),       # Clear the feedback display
        gr.update(visible=generate_final_report)  # Show generate_final_report_button
    )

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
    full_transcript = format_transcript_text(current_state.answers)
    prior_feedback = format_prior_feedback(current_state.feedback_reports)

    # 3. Create the final "mega-prompt".
    prompt = create_final_report_prompt(full_transcript, prior_feedback)

    # 4. Call the LLM service.
    final_report_result = llm_service.get_final_report(prompt)

    # Reset the phase, as the process is complete.
    current_state.session_phase = SessionPhase.TEST_COMPLETED

    if isinstance(final_report_result, IELTSFinalReport):
        # --- Step 5a (REFINEMENT): Perform our own calculation ---
        scores_to_average = [
            final_report_result.estimated_scores.fluency_and_coherence.score,
            final_report_result.estimated_scores.lexical_resource.score,
            final_report_result.estimated_scores.grammatical_range_and_accuracy.score
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
    else:
        # Failure. The service returned an error string.
        error_message = final_report_result
        yield (
            current_state,
            gr.update(value=error_message, visible=True),
            gr.update(interactive=True)
        )