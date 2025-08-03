# <-- Loads settings from.env using python-dotenv
# In: config.py (Root Folder)

import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# Handle Google TTS credentials for Hugging Face Spaces
def setup_google_credentials():
    """Setup Google credentials for TTS service"""
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if credentials_json:
        # Running on Hugging Face Spaces
        credentials_path = "/tmp/google-credentials.json"
        with open(credentials_path, "w") as f:
            f.write(credentials_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        return credentials_path
    else:
        # Running locally - use existing file
        local_path = "secrets/aurora-tts-key.json"
        if os.path.exists(local_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_path
            return local_path
    return None

# Setup credentials on import
setup_google_credentials()