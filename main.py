# <-- FastAPI app definition, mounts the fastrtc stream
# and serves the Gradio interface.
import gradio as gr
from fastapi import FastAPI
from gradio_app import create_gradio_interface
from core.logger_config import setup_logger
setup_logger()

# Create the Gradio interface
gradio_interface = create_gradio_interface()

# Launch directly with Gradio - this works reliably on HF Spaces
print("🚀 Starting Aurora Gradio Interface...")
gradio_interface.launch(
    server_name="0.0.0.0",   # "127.0.0.1" - for local run
    server_port=7860,
    share=False,             # True - for local run
    show_error=True,
    debug=True
)