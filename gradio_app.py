# In: gradio_app.py

import gradio as gr

# --- Import services and models ---
from services.stt_service import AssemblyAITranscriber
from services.llm_service import GeminiChat
from services.tts_service import GoogleTTS
from utils.text_cleaner import clean_text_for_speech
from data.ielts_questions import IELTSQuestionBank
from logic.ielts_models import IELTSState

# --- Initialize services once when the app starts ---
stt_service = AssemblyAITranscriber()
llm_service = GeminiChat()
tts_service = GoogleTTS()
question_bank = IELTSQuestionBank()

# --- IELTS Test Logic ---

def start_ielts_test():
    """Initializes a new IELTS test, pulling random questions."""
    try:
        test_questions = question_bank.get_random_test()
        first_question = test_questions["part1"]["questions"][0] # Unpack the first question for immediate display
        
        # Create a new instance of  dataclass with initial values
        new_state = IELTSState(
            questions=test_questions,
            current_part=1,
            current_question_index=0,
            test_started=True,
            current_question_text=first_question
        )

        # >> The formatted question for display
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

def process_answer(user_audio, current_state: IELTSState):
    """Processes a user's answer, transcribes it, and moves to the next question."""
    # Check if test is started
    if not current_state.test_started:
        return current_state, "Please start the test first.", "", gr.update(visible=False)

    if not user_audio:
        # If no audio, just return the current state without change
        return current_state, current_state.current_question_text, "\n\n---\n\n".join(current_state.answers), gr.update(visible=True)

    # Guard clause: Ensure questions is not None
    if not current_state.questions:
        return (
            current_state,
            "Error: No questions loaded. Please restart the test.",
            "",
            gr.update(visible=False)
        )
    
    try:
        # Transcribe the user's answer
        transcript = stt_service.transcribe(user_audio)
        if transcript.startswith("Error:"):
            return current_state, current_state.current_question_text, transcript, gr.update(visible=True)
        
        # Store the answer
        current_state.answers.append(f"**Q:** {current_state.current_question_text}\n\n**A:** {transcript}")

        # --- Determine the next question ---
        next_question_text = "Test completed!"
        show_recording = False
        
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

# --- Free Chat Logic ---
def chat_function(user_audio, chat_history_state):
    if user_audio is None:
        return chat_history_state, None, chat_history_state

    user_text = stt_service.transcribe(user_audio)
    if user_text.startswith("Error:"):
        chat_history_state.append((user_text, None))
        return chat_history_state, None, chat_history_state

    chat_history_state.append((user_text, None))

    gemini_history = [{'role': 'user' if i % 2 == 0 else 'model', 'parts': [msg[0] if i % 2 == 0 else msg[1]]} for i, msg in enumerate(chat_history_state)]
    
    *_, last_user_prompt = gemini_history
    ai_response_text = llm_service.get_response(gemini_history[:-1], last_user_prompt['parts'][0])
    
    chat_history_state[-1] = (user_text, ai_response_text)

    cleaned_text = clean_text_for_speech(ai_response_text)
    ai_audio_path = tts_service.synthesize_speech(cleaned_text)

    return chat_history_state, ai_audio_path, chat_history_state

# --- Main UI Function ---
def create_gradio_interface():
    with gr.Blocks(theme=gr.themes.Soft(), title="Aurora AI") as interface: # type: ignore
        gr.Markdown("# Aurora: Your AI English Speaking Coach")
        
        with gr.Tab("Free Chat Mode"):
            chatbot_display = gr.Chatbot(label="Conversation", height=500)
            ai_audio_output = gr.Audio(visible=False, autoplay=True)
            chat_history_state = gr.State([])
            with gr.Row():
                mic_input_chat = gr.Audio(sources=["microphone"], type="filepath", label="Speak Here")
            mic_input_chat.stop_recording(
                fn=chat_function, 
                inputs=[mic_input_chat, chat_history_state], 
                outputs=[chatbot_display, ai_audio_output, chat_history_state]
            )

        with gr.Tab("IELTS Practice Mode"):
            gr.Markdown("""
            ## IELTS Speaking Test Simulation
            
            This is a complete IELTS Speaking test simulation with all three parts:
            - **Part 1**: Introduction and interview (4-5 minutes)
            - **Part 2**: Long turn with cue card (3-4 minutes)
            - **Part 3**: Discussion (4-5 minutes)
            
            Click 'Start Test' to begin with a random question set.
            """)
            
            # >> Initialize the state component with our new dataclass
            ielts_state = gr.State(IELTSState())

            with gr.Row():
                start_button = gr.Button("🎯 Start New IELTS Test", variant="primary", size="lg")
                reset_button = gr.Button("🔄 Reset", variant="secondary")
            
            with gr.Column(visible=False) as test_interface:
                question_display = gr.Markdown("### Question will appear here")
                
                with gr.Column(visible=False) as recording_interface:
                    mic_input_ielts = gr.Audio(
                        sources=["microphone"], 
                        type="filepath", 
                        label="🎤 Record Your Answer"
                    )
                    gr.Markdown("*Speak clearly and naturally.*")
                
                with gr.Accordion("📝 Your Answers", open=False):
                    transcripts_display = gr.Textbox(
                        label="Recorded Answers", 
                        lines=10, 
                        interactive=False,
                        placeholder="Your transcribed answers will appear here..."
                    )

            # --- Event Listeners for IELTS Mode ---
            start_button.click(
                fn=start_ielts_test,
                inputs=[],
                outputs=[
                    ielts_state, 
                    start_button,
                    reset_button, 
                    test_interface, 
                    question_display, 
                    transcripts_display,
                    recording_interface
                ]
            )
            
            mic_input_ielts.stop_recording(
                fn=process_answer,
                inputs=[mic_input_ielts, ielts_state],
                outputs=[
                    ielts_state, 
                    question_display, 
                    transcripts_display, 
                    recording_interface]
            )
            
            reset_button.click(
                fn=reset_test,
                inputs=[],
                outputs=[
                    ielts_state, 
                    start_button, 
                    reset_button,
                    test_interface, 
                    question_display, 
                    transcripts_display, 
                    recording_interface
                ]
            )

    return interface

