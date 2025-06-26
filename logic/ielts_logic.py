# In: logic/ielts_logic.py

import gradio as gr
from .ielts_models import IELTSState

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
            current_question_text=first_question
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
            gr.update(visible=True)         # Show recording interface
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
            gr.update(visible=False)
        )

def process_answer(user_audio, current_state: IELTSState, stt_service):
    """Processes a user's answer and determines the next state of the test."""
    # Check if test is started
    if not current_state.test_started:
        return current_state, "Please start the test first.", ""

    if not user_audio:
        # If no audio is provided, return the current state and question text
        return current_state, current_state.current_question_text, "\n\n---\n\n".join(current_state.answers)

    # Guard clause: Ensure questions is not None
    if not current_state.questions:
        return (
            current_state,
            "Error: No questions loaded. Please restart the test.",
            "",
            gr.update(visible=False)
        )

    try:
        # Transcribe the user's audio input``
        transcript = stt_service.transcribe(user_audio)
        if transcript.startswith("Error:"):
            return current_state, current_state.current_question_text, transcript

        # Append the transcript to the answers``
        current_state.answers.append(f"**Q:** {current_state.current_question_text}\n\n**A:** {transcript}")

        # --- Determine the next question ---
        next_question_text = "Test completed!"
        show_recording = True

        # Part 1 Logic
        if current_state.current_part == 1:
            current_state.current_question_index += 1
            part1_questions = current_state.questions["part1"]["questions"]
            if current_state.current_question_index < len(part1_questions):
                next_question_text = part1_questions[current_state.current_question_index]
                show_recording = True
            else:
                # Transition to Part 2
                current_state.current_part = 2
                current_state.current_question_index = 0
                next_question_text = f"**Part 2**\n\n**Topic:** {current_state.questions['part2']['topic']}\n\n{current_state.questions['part2']['cue_card']}\n\n*You have 1 minute to prepare, then speak for 1-2 minutes.*"
                show_recording = True
                # TODO: Add logic to show timers here
        
        # Part 2 Logic
        elif current_state.current_part == 2:
            # After answering Part 2, transition to Part 3
            current_state.current_part = 3
            current_state.current_question_index = 0
            next_question_text = current_state.questions["part3"]["questions"][0]
            show_recording = True

        # Part 3 Logic
        elif current_state.current_part == 3:
            current_state.current_question_index += 1
            part3_questions = current_state.questions["part3"]["questions"]
            if current_state.current_question_index < len(part3_questions):
                next_question_text = part3_questions[current_state.current_question_index]
                show_recording = True
            else:
                # End of Test
                current_state.current_part = 0 # Test is over
                current_state.test_started = False
                next_question_text = "🎉 **Congratulations!** You have completed the IELTS Speaking test.\n\nYour answers are recorded below. Review them to see how you performed!"
                show_recording = False # Hide recording interface

        current_state.current_question_text = next_question_text       
        return (
            current_state, 
            next_question_text, 
            "\n\n---\n\n".join(current_state.answers),
            gr.update(visible=show_recording)
        )
        
    except Exception as e:
        return (
            current_state,
            current_state.current_question_text,
            f"Error processing answer: {str(e)}",
            gr.update(visible=True)
        )

# --- Reset Functionality ---
def reset_test():
    """Resets the UI and the state to its initial condition."""
    # Return a new, empty IELTSState object to fully reset the state
    return (
        IELTSState(),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        "Click 'Start Test' to begin a new IELTS Speaking simulation.",
        "",
        gr.update(visible=False)
    )