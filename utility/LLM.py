import os
import re
import json
from typing import List, Dict
from groq import Groq

class LLMClient:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        if os.getenv("GROQ_API_KEY"):
            print("Groq API key is there")
        else:
            print("Cant find Groq API key")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model

    def run_chat(self, system_message: str, user_message: str) -> str:
        """Run a chat completion with the LLM and return the response"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content.strip()

    def run_json(self, system_message: str, user_message: str) -> Dict:
        """Return parsed JSON from the LLM"""
        output = self.run_chat(system_message, user_message)
        print(f"Raw output from LLM: {output}")

        # Try extracting markdown-style JSON blocks
        json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', output, re.DOTALL)

        # Fallback: Try to find a top-level JSON object
        if not json_blocks:
            json_blocks = re.findall(r'(\{.*\})', output, re.DOTALL)

        if not json_blocks:
            raise ValueError("No valid JSON block found in LLM response.")

        last_block = json_blocks[-1]

        return json.loads(last_block)
    
    def summarize_json_output(self, explanation_json: dict, context: str = None) -> str:
        system_prompt = (
            "You are a helpful assistant that explains structured eligibility results in clear, user-friendly language. "
            "Highlight whether the user is eligible or not, and if not, explain why and what is missing."
        )

        user_message = f"""
        Context: {context or "Eligibility check for a government scheme"}
        JSON Response:
        {explanation_json}

        Write a clear, human-friendly summary of this information.
        """

        # Get raw response
        response = self.run_chat(system_prompt, user_message)

        # Extract just the final explanation string
        if isinstance(response, dict):
            if "content" in response:
                # Groq-like format
                text_parts = [c["text"] for c in response["content"] if c["type"] == "text"]
                return "\n".join(text_parts).strip() if text_parts else str(response)
            elif "text" in response:
                return response["text"].strip()
        elif isinstance(response, str):
            return response.strip()

        return str(response)
