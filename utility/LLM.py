import os
import re
import json
from typing import List, Dict
from groq import Groq

class LLMClient:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
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