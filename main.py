# <-- FastAPI app definition, mounts the fastrtc stream
# and serves the Gradio interface.
import gradio as gr
from fastapi import FastAPI
from gradio_app import create_gradio_interface

# Create a FastAPI app instance
app = FastAPI()

# Create the Gradio interface
gradio_interface = create_gradio_interface()

# Mount the Gradio app on the FastAPI server
app = gr.mount_gradio_app(app, gradio_interface, path="/gradio")

# Optional: Add a root endpoint for API health check
@app.get("/api")
def read_root():
    return {"status": "Aurora API is running"}