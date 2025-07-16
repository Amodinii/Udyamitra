import os
import json
import re
import requests
from bs4 import BeautifulSoup
from time import sleep
from typing import List, Dict
from groq import Groq

# === YOUR EXISTING CLIENT ===
class LLMClient:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model

    def run_chat(self, system_message: str, user_message: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content.strip()

    def run_json(self, system_message: str, user_message: str) -> Dict:
        output = self.run_chat(system_message, user_message)
        print(f"\nRaw output:\n{output}\n")

        json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', output, re.DOTALL)
        if not json_blocks:
            json_blocks = re.findall(r'(\{.*\})', output, re.DOTALL)

        if not json_blocks:
            raise ValueError("No valid JSON block found in LLM response.")

        return json.loads(json_blocks[-1])

# === SCRAPER ===
def get_clean_text_from_url(url: str) -> str:
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        clean_lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(clean_lines)[:8000]  # Limit for safety
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

# === PROMPT ===
SYSTEM_MSG = "You extract structured metadata from government scheme webpages."
PROMPT_TEMPLATE = """
Extract JSON metadata from the scheme page below using this schema:

{{
  "scheme_name": ...,
  "scheme_type": "National" or "State",
  "admin_body": ...,
  "location_scope": "Pan-India" or state name,
  "duration": ...,
  "sector_tags": [...],
  "target_entities": [...],
  "user_stage": [...],
  "pre_approval_required": true or false,
  "source_url": "{source_url}"
}}

Only return a clean JSON object. Do not explain anything. Skip missing fields.

--- PAGE CONTENT START ---
{page_content}
--- PAGE CONTENT END ---
"""

# === MAIN ===
if __name__ == "__main__":
    url_list = [
        "https://ism.gov.in/design-linked-incentive",
        "https://www.meity.gov.in/offerings/schemes-and-services/details/production-linked-incentive-scheme-pli-2-0-for-it-hardware-wM0MDOtQWa",
        "https://www.meity.gov.in/offerings/schemes-and-services/details/scheme-for-promotion-of-manufacturing-of-electronic-components-and-semiconductors-specs-AMxIDOtQWa",
        "https://www.meity.gov.in/offerings/schemes-and-services/details/modified-special-incentive-package-scheme-m-sips-IDNyETMtQWa",
        "https://msh.meity.gov.in/",
        "https://cleartax.in/s/support-international-patent-protection-electronics-information-technology-sip-eit",
        "https://ism.gov.in/",
        "https://www.meity.gov.in/offerings/schemes-and-services/details/electronic-manufacturing-clusters-emc-scheme-kTO5EjMtQWa",
    ]

    llm = LLMClient()
    all_metadata = []

    for url in url_list:
        print(f"\nProcessing {url}")
        content = get_clean_text_from_url(url)
        if not content:
            print("Skipping due to fetch failure.")
            continue

        user_prompt = PROMPT_TEMPLATE.format(source_url=url, page_content=content)
        try:
            metadata = llm.run_json(SYSTEM_MSG, user_prompt)
            print("Extracted:")
            print(json.dumps(metadata, indent=2))
            all_metadata.append(metadata)
        except Exception as e:
            print(f"LLM parsing failed for {url}: {e}")

        sleep(1)

    # Optionally save
    with open("metadata_llama4.json", "w") as f:
        json.dump(all_metadata, f, indent=2)

    print(f"\nCompleted {len(all_metadata)} successful extractions.")
