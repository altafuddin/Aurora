# In: gradio_app.py

import gradio as gr
from functools import partial

# --- Import services and models ---
from services.stt_service import AssemblyAITranscriber
from services.azure_speech_service import AzureSpeechService
from services.llm_service import GeminiChat
from services.tts_service import GoogleTTS
from data.ielts_questions import IELTSQuestionBank
from logic.ielts_models import IELTSState
from logic.chat_models import ChatTurn
from logic.ielts_logic import (
    start_ielts_test, 
    process_answer, 
    reset_test, 
    continue_to_next_part, 
    generate_feedback,
    generate_final_report
)
from logic.chat_logic import chat_function

# --- Initialize services and data handlers once when the app starts ---
# These are the "global" resources our app will use.
azure_speech_service = AzureSpeechService()
stt_service = AssemblyAITranscriber()
llm_service = GeminiChat()
tts_service = GoogleTTS()
question_bank = IELTSQuestionBank()

# --- Main UI Function ---
def create_gradio_interface():
    """
    Defines the Gradio user interface and connects it to the logic functions.
    This file is now only responsible for the 'view' of our application.
    """
    with gr.Blocks(theme=gr.themes.Soft(), title="Aurora AI") as interface: # type: ignore
        gr.Markdown("# Aurora: Your AI English Speaking Coach")
        
        # --- Tab 1: Free Chat Mode ---
        with gr.Tab("Free Chat Mode"):
            chatbot_display = gr.Chatbot(label="Conversation", height=500)
            ai_audio_output = gr.Audio(visible=False, autoplay=True)
            chat_history_state = gr.State([])
            with gr.Row():
                mic_input_chat = gr.Audio(sources=["microphone"], type="filepath", label="Speak Here")
            
            mic_input_chat.stop_recording(
                fn=partial(
                    chat_function,
                    speech_service=azure_speech_service,
                    llm_service=llm_service,
                    tts_service=tts_service
                ),
                inputs=[mic_input_chat, chat_history_state],
                outputs=[chatbot_display, ai_audio_output, chat_history_state]
            )

        # --- Tab 2: IELTS Practice Mode ---
        with gr.Tab("IELTS Practice Mode"):
            gr.Markdown("""
            ## IELTS Speaking Test Simulation
            
            This is a complete IELTS Speaking test simulation with all three parts:
            - **Part 1**: Introduction and interview (4-5 minutes)
            - **Part 2**: Long turn with cue card (3-4 minutes)
            - **Part 3**: Discussion (4-5 minutes)
            
            Click 'Start Test' to begin a IELTS Speaking simulation set.
            """)
            
            # >> Initialize the state component with our new dataclass
            ielts_state = gr.State(IELTSState())

            with gr.Row():
                start_button = gr.Button("🎯 Start New IELTS Test", variant="primary", size="lg")
                reset_button = gr.Button("🔄 Reset", variant="secondary", visible=False)
            
            with gr.Column(visible=False) as test_interface:
                question_display = gr.Markdown("### Question will appear here")
                
                with gr.Column(visible=True) as recording_interface:
                    mic_input_ielts = gr.Audio(
                        sources=["microphone"], 
                        type="filepath", 
                        label="🎤 Record Your Answer"
                    )
                    gr.Markdown("*Speak clearly and naturally.*")
                
                with gr.Row(visible=False) as feedback_buttons:
                    get_part_feedback_button = gr.Button("📊 Get Feedback for This Part", variant="primary", scale=1, min_width=180)
                    continue_to_next_part_button = gr.Button("➡️ Continue ", variant="secondary", scale=1, min_width=180)
                
                generate_final_report_button = gr.Button(
                    "🏆 Generate Final Comprehensive Report",
                    variant="primary",
                    visible=False,
                    scale=1,
                    size="lg"
                )

                # Component to display the feedback report
                feedback_display = gr.Markdown(visible=False)


                with gr.Accordion("📝 Your Answers", open=False):
                    transcripts_display = gr.Textbox(
                        label="Recorded Answers", 
                        lines=10, 
                        interactive=False,
                        placeholder="Your transcribed answers will appear here..."
                    )

            # --- Event Listeners for IELTS Mode ---
            start_button.click(
                fn=lambda: start_ielts_test(question_bank),
                inputs=[],
                outputs=[
                    ielts_state, 
                    start_button,
                    reset_button, 
                    test_interface, 
                    question_display, 
                    transcripts_display,
                    recording_interface,
                    feedback_buttons
                ]
            )
            
            mic_input_ielts.stop_recording(
                fn=lambda audio, state: process_answer(audio, state, stt_service),
                inputs=[mic_input_ielts, ielts_state],
                outputs=[
                    ielts_state, 
                    question_display, 
                    transcripts_display, 
                    recording_interface,
                    feedback_buttons
                ]
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
                    recording_interface,
                    feedback_buttons,
                    feedback_display
                ]
            )

            continue_to_next_part_button.click(
                fn=continue_to_next_part,
                inputs=[ielts_state],
                outputs=[
                    ielts_state, 
                    question_display, 
                    recording_interface, 
                    feedback_buttons,
                    feedback_display,
                    generate_final_report_button
                ]
            )

            # click handler for the get_part_feedback_button
            get_part_feedback_button.click(
                fn=partial(generate_feedback, llm_service=llm_service),
                inputs=[ielts_state],
                outputs=[
                    ielts_state, 
                    feedback_display, 
                    get_part_feedback_button, 
                    continue_to_next_part_button
                ]
            )

            generate_final_report_button.click(
                fn=partial(generate_final_report, llm_service=llm_service),
                inputs=[ielts_state],
                outputs=[
                    ielts_state,
                    feedback_display,
                    generate_final_report_button
                ]
            )

    return interface