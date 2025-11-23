# <-- Gemini Adapter: handles all LLM interaction
# In: services/llm_service.py

import google.generativeai as genai
from config import GEMINI_API_KEY
import sys
import time
import logging
from logic.ielts_models import IELTSFeedback, IELTSFinalReport  # our Pydantic models
from pydantic import ValidationError
from typing import Optional

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

    def get_response(
        self, 
        full_prompt: str, 
        chat_history: Optional[list] = None
    ) -> str:
        """
        Gets a response from the Gemini model. This method is flexible and can handle:
        1. A simple user_prompt for single-shot tasks.
        2. A user_prompt with a chat_history and a system_prompt for conversations.
        
        Args:
            full_prompt: The final, complete prompt to be sent to the model.
            chat_history: A list of previous turns in the conversation.

        Returns:
            The model's text response.
        """
        if not self.model:
            return "Error: Gemini model is not initialized."

        start_time = time.time()
        try:
            logging.info(f"API: Gemini.generate_content | status=starting")
            # --- Build the message list in the format the API expects ---
            messages = chat_history or []
            messages.append({"role": "user", "parts": [{"text": full_prompt}]})

            # --- Generate the content ---
            response = self.model.generate_content(messages)
            elapsed = time.time() - start_time
            
            # Try to get token count if available
            token_info = ""
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    token_info = f" | tokens={response.usage_metadata.total_token_count}"
            except:
                pass
            
            logging.info(f"API: Gemini.generate_content | status=success | duration={elapsed:.2f}s{token_info}")
            
            if response and response.parts:
                return response.text
            # Handle cases where the response might be blocked or empty
            elif response.prompt_feedback and str(response.prompt_feedback.block_reason) != "BlockReason.BLOCK_REASON_UNSPECIFIED":
                error_msg = f"LLM response blocked due to: {response.prompt_feedback.block_reason}"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                return f"Sorry, I can't respond to that. ({response.prompt_feedback.block_reason})"
            else:
                return "Sorry, I couldn't think of a response."
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(f"API: Gemini.generate_content | status=error | duration={elapsed:.2f}s | error={str(e)}")
            print(f"Error getting response from Gemini: {e}", file=sys.stderr)
            return "Sorry, I encountered an error. Could you please repeat that?"
        
    def get_structured_feedback(self, prompt: str) -> IELTSFeedback | str:
        """
        Gets a structured JSON response from the Gemini model and parses it
        into our IELTSFeedback Pydantic model.
        """
        if not self.model:
            return "Error: Gemini model is not initialized."

        start_time = time.time()
        try:
            logging.info(f"API: Gemini.get_structured_feedback | status=starting")
            generation_config = genai.types.GenerationConfig(
                temperature=0.75,  # Adjust temperature for creativity vs. accuracy
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
            
            elapsed = time.time() - start_time
            logging.info(f"API: Gemini.get_structured_feedback | status=success | duration={elapsed:.2f}s")
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
            
            elapsed = time.time() - start_time
            logging.error(f"API: Gemini.get_structured_feedback | status=error | duration={elapsed:.2f}s")
            return "Sorry, I encountered an error while generating feedback. The format of the response was not as expected."
    
    def get_final_report(self, prompt: str) -> IELTSFinalReport | str:
        """
        Gets a structured JSON response for the final report and parses it
        into our IELTSFinalReport Pydantic model.
        """
        if not self.model:
            return "Error: Gemini model is not initialized."

        start_time = time.time()
        try:
            logging.info(f"API: Gemini.get_final_report | status=starting")
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
            
            elapsed = time.time() - start_time
            logging.info(f"API: Gemini.get_final_report | status=success | duration={elapsed:.2f}s")
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
            
            elapsed = time.time() - start_time
            logging.error(f"API: Gemini.get_final_report | status=error | duration={elapsed:.2f}s")
            return "Sorry, I encountered an error while generating the final report."