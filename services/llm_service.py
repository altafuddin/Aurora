# <-- Gemini Adapter: handles all LLM interaction
# In: services/llm_service.py

import google.generativeai as genai
from config import GEMINI_API_KEY
import sys
import json
from logic.ielts_models import IELTSFeedback, IELTSFinalReport  # Import our Pydantic models
from pydantic import ValidationError

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
            self.model = genai.GenerativeModel('gemini-2.0-flash')
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
        
    def get_structured_feedback(self, prompt: str) -> IELTSFeedback | str:
        """
        Gets a structured JSON response from the Gemini model and parses it
        into our IELTSFeedback Pydantic model.
        """
        if not self.model:
            return "Error: Gemini model is not initialized."

        try:
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,  # Adjust temperature for creativity vs. accuracy
            )

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            raw_response_text = response.text

            # --- Step 1: Clean the response to isolate the JSON object ---
            start_index = raw_response_text.find('{')
            end_index = raw_response_text.rfind('}')
            
            if start_index == -1 or end_index == -1:
                error_msg = f"Error: LLM response did not contain a valid JSON object. Response: {raw_response_text}"
                print(error_msg, file=sys.stderr)
                return error_msg

            json_string = raw_response_text[start_index : end_index + 1]
            
            # --- Step 2: Parse and validate the JSON string into our Pydantic model ---
            print("LOG: Received response. Validating JSON...")
            feedback_data = IELTSFeedback.model_validate_json(json_string)
            print("LOG: JSON validation successful.")
            
            return feedback_data

        except ValidationError as e:
            # Pydantic will raise a ValidationError if the JSON is malformed
            # or missing fields. This is our safety net.
            error_message = f"Error: Pydantic validation failed. The LLM's JSON output did not match our schema. Details: {e}"
            print(error_message, file=sys.stderr)
            return error_message
        except Exception as e:
            # This block is crucial for debugging when the LLM fails to produce valid JSON
            error_message = f"Error generating or parsing structured feedback: {e}"
            print(error_message, file=sys.stderr)
            try:
                # Add this to see what the model actually returned
                print("---RAW LLM RESPONSE---")
                print(response.text)
                print("------------------------")
            except NameError:
                pass # response might not exist if the error was earlier
            return "Sorry, I encountered an error while generating feedback. The format of the response was not as expected."
    
    def get_final_report(self, prompt: str) -> IELTSFinalReport | str:
        """
        Gets a structured JSON response for the final report and parses it
        into our IELTSFinalReport Pydantic model.
        """
        if not self.model:
            return "Error: Gemini model is not initialized."

        try:
            # Use the same robust method as before: instruct via prompt
            # and validate the response.
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Clean the response to find the JSON object
            json_text = response.text[response.text.find('{'):response.text.rfind('}')+1]
            
            # Parse and validate the JSON against our final report model
            # --- Step 2: Parse and validate the JSON string into our Pydantic model ---
            print("LOG: Received response. Validating JSON...")
            final_report_data = IELTSFinalReport.model_validate_json(json_text)
            print("LOG: JSON validation successful.")
            return final_report_data

        except Exception as e:
            error_message = f"Error generating or parsing final report: {e}"
            print(error_message, file=sys.stderr)
            try:
                print("---RAW LLM RESPONSE (Final Report)---")
                print(response.text)
                print("------------------------------------")
            except NameError:
                pass
            return "Sorry, I encountered an error while generating the final report."