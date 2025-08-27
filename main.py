import gradio as gr
# from fastapi import FastAPI
from pyngrok import ngrok
from gradio_app import create_gradio_interface
from core.logger_config import setup_logger

setup_logger()

# Create the Gradio interface
gradio_interface = create_gradio_interface()

# try:
#     # Try to create ngrok tunnel
#     public_url = ngrok.connect(7860)
#     print(f"🌐 Public URL: {public_url}")
#     use_ngrok = True
# except Exception as e:
#     print(f"❌ ngrok failed: {e}")
#     print("📡 Falling back to Gradio share...")
#     use_ngrok = False

print("🚀 Starting Aurora Gradio Interface...")
use_ngrok = None
if use_ngrok:
    # Launch with ngrok
    gradio_interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # Don't use Gradio share with ngrok
        show_error=True,
        debug=True
    )
else:
    # Fallback to Gradio share
    gradio_interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,  
        show_error=True,
        debug=True
    )