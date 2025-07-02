# In: logic/ielts_logic.py

import gradio as gr
from .ielts_models import IELTSState, SessionPhase, IELTSFeedback
from .prompts import create_single_part_feedback_prompt
from utils.ielts_utils import format_feedback_for_display


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

def process_answer(user_audio, current_state: IELTSState, stt_service):
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
        return (
            current_state,
            current_state.current_question_text,
            "\n\n---\n\n".join(current_state.answers),
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
        # Transcribe the user's audio input``
        transcript = stt_service.transcribe(user_audio)
        if transcript.startswith("Error:"):
            return (
                current_state,
                current_state.current_question_text,
                transcript,
                gr.update(visible=True),
                gr.update(visible=False)
            )

        # Append the transcript to the answers``
        current_state.answers.append(f"**Q:** {current_state.current_question_text}\n\n**A:** {transcript}")

        # Handle the end-of-part case and return immediately.
        if is_part_ending:
            current_state.session_phase = SessionPhase.PART_ENDED
            next_question_text = f"**End of Part {current_state.current_part}**\n\nWhat would you like to do next?"
            # Hide recording interface, show feedback buttons
            return (
                current_state, 
                next_question_text, 
                "\n\n---\n\n".join(current_state.answers), 
                gr.update(visible=False), 
                gr.update(visible=True)
            )
    
        # --- Determine the next question ---
        next_question_text = "Test completed!"

        # Part 1 Logic
        if current_state.current_part == 1:
            current_state.current_question_index += 1
            part1_questions = current_state.questions["part1"]["questions"]
            next_question_text = part1_questions[current_state.current_question_index]
            
        # Part 2 Logic (This is the transition from Part 1 to 2)
        # We need to adjust the logic slightly, as this code is now only reachable
        # after the last Part 1 question has been answered (in the previous turn).
        # The transition logic should happen when we press "Continue".
        # Let's simplify for now. The core logic will be in the new "continue" function.
        
        # The logic to transition between parts will be moved to a new function
        # triggered by the "Continue" button. For now, we just advance the question.
        current_state.current_question_index += 1
        part_key = f"part{current_state.current_part}"
        questions_in_part = current_state.questions[part_key]["questions"]
        next_question_text = questions_in_part[current_state.current_question_index]
        
        current_state.current_question_text = next_question_text       
        return (
            current_state, 
            next_question_text, 
            "\n\n---\n\n".join(current_state.answers),
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
            "",
            gr.update(visible=False),
            gr.update(visible=False)
        )
    
    # Hide feedback buttons and show the recording interface
    show_recording = True
    show_feedback_buttons = False
    
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
        # This case shouldn't be reached if the UI is controlled properly,
        # but it's good practice to handle it.
        next_question_text = "An unexpected error occurred."
        show_recording = False

    current_state.current_question_text = next_question_text
    
    return (
        current_state,
        next_question_text,
        gr.update(visible=show_recording),
        gr.update(visible=show_feedback_buttons),
        gr.update(value="", visible=False)
    )

# --- Feedback Functionality ---
def get_part_feedback_dummy(current_state: IELTSState):
    """
    A placeholder function for the 'Get Feedback' button.
    """
    # Placeholder logic:
    # 1. Set state.session_phase = SessionPhase.GENERATING_FEEDBACK
    # 2. Call LLM Service
    # 3. Add report to state.feedback_reports
    # 4. Return state and gr.update() for feedback display
    # For now, it just returns a simple message.
    feedback_report = "Feedback generation is not implemented yet. Coming soon!"
    
    # We also need to hide the feedback buttons and show the continue button again
    # or handle the next step. Let's decide the flow. For now, let's just show the message.
    # The function needs to return values for all its outputs. Let's add a new gr.Markdown for feedback
    return gr.update(value=feedback_report, visible=True), gr.update(visible=False)

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

def generate_feedback(current_state: IELTSState, llm_service):
    """
    Orchestrates the process of getting, parsing, and displaying IELTS feedback.
    """
    if not current_state.answers:
        return "Error: No answers were provided to generate feedback."
    
    # Set the session phase to show the app is "busy"
    current_state.session_phase = SessionPhase.GENERATING_FEEDBACK

    # 1. Set a "loading" state for the UI
    yield (
        current_state, 
        gr.update(value="Generating feedback, please wait..."), # For ielts_feedback_display
        gr.update(interactive=False), # Disable feedback button to prevent double-clicks
        gr.update(interactive=False)  # Disable continue button
    )

    
    # 2. Prepare data for the prompt
    # We get the answers for the part that just ended.
    # A more robust way would be to filter state.user_answers by part number,
    # but for now, we assume it contains only the answers for the last part.
    # Format the questions and answers into a single string for the prompt
    # TODO: Filtering answer based on part
    questions_and_answers = "\n\n".join(current_state.answers)
    part_number = current_state.current_part

    # 3. Create the detailed, structured prompt
    prompt = create_single_part_feedback_prompt(part_number, questions_and_answers)

    # 4. Call the LLM service to get structured feedback
    feedback_result = llm_service.get_structured_feedback(prompt)

    # --- Process the result ---
    if isinstance(feedback_result, IELTSFeedback):

        # Success! We got a valid, structured feedback object.
        current_state.feedback_reports.append(feedback_result)

        # Reset the phase to indicate the part has ended
        current_state.session_phase = SessionPhase.PART_ENDED
        # Format the structured data into nice Markdown for display
        report = format_feedback_for_display(feedback_result)
        
        yield (
            current_state,
            gr.update(value=report), # Show the formatted feedback
            gr.update(interactive=True), # Re-enable feedback button
            gr.update(interactive=True)  # Re-enable continue button
        )
    else:
        # Reset the phase even if there's an error
        current_state.session_phase = SessionPhase.PART_ENDED
        # Failure. The service returned an error string.
        error_message = feedback_result
        yield (
            current_state,
            gr.update(value=error_message), # Show the error message
            gr.update(interactive=True), # Re-enable feedback button
            gr.update(interactive=True)  # Re-enable continue button
        )