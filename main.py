# <-- FastAPI app definition, mounts the fastrtc stream
# and serves the Gradio interface.
import gradio as gr
from fastapi import FastAPI
from gradio_app import create_gradio_interface
from core.logger_config import setup_logger
setup_logger()

# Simple Gradio-only approach for HF Spaces
import gradio as gr
from gradio_app import create_gradio_interface
from core.logger_config import setup_logger

setup_logger()

# Create the Gradio interface
gradio_interface = create_gradio_interface()

# Launch directly with Gradio - this works reliably on HF Spaces
print("🚀 Starting Aurora Gradio Interface...")
gradio_interface.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=False,
    show_error=True,
    debug=True
)