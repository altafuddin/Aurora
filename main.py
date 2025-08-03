# <-- FastAPI app definition, mounts the fastrtc stream
# and serves the Gradio interface.
import gradio as gr
from fastapi import FastAPI
from gradio_app import create_gradio_interface
from core.logger_config import setup_logger
setup_logger()

# Create a FastAPI app instance
app = FastAPI()

# Create the Gradio interface
gradio_interface = create_gradio_interface()

# Optional: Add an API endpoint for health check
@app.get("/api")
def read_root():
    return {"status": "Aurora API is running"}

# Mount the Gradio app at /gradio path
gr.mount_gradio_app(app, gradio_interface, path="/gradio")

# Add a redirect from root to /gradio
@app.get("/")
def redirect_to_gradio():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/gradio")
