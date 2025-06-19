# <-- Gemini Adapter: handles all LLM interaction
# In: services/llm_service.py

import google.generativeai as genai
from config import GEMINI_API_KEY
import sys

class GeminiChat:
    def __init__(self):
        """
        Initializes the Gemini model.
        """
        if not GEMINI_API_KEY:
            print("FATAL ERROR: GEMINI_API_KEY is not set.", file=sys.stderr)
            self.model = None
            return

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Using Gemini 1.5 Flash for speed and cost-effectiveness
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            print("--- Gemini Model Initialized Successfully ---")
        except Exception as e:
            print(f"Error initializing Gemini Model: {e}", file=sys.stderr)
            self.model = None

    def get_response(self, chat_history: list, user_prompt: str) -> str:
        """
        Gets a response from the Gemini model based on the chat history and new prompt.
        
        Args:
            chat_history: A list of previous turns in the conversation.
            user_prompt: The user's latest message.

        Returns:
            The model's text response.
        """
        if not self.model:
            return "Error: Gemini model is not initialized."

        try:
            # The chat object maintains conversation history
            chat = self.model.start_chat(history=chat_history)
            response = chat.send_message(user_prompt)
            return response.text
        except Exception as e:
            print(f"Error getting response from Gemini: {e}", file=sys.stderr)
            return "Sorry, I encountered an error. Could you please repeat that?"