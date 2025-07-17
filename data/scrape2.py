import os
import json
import fitz
from utility.LLM import LLMClient
from Logging.logger import logger

def read_text_file(filepath: str) -> str:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read text file {filepath}: {e}")
        return ""

def extract_text_from_pdf(filepath: str) -> str:
    try:
        doc = fitz.open(filepath)
        text = "\n".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        logger.error(f"Failed to extract PDF {filepath}: {e}")
        return ""

def generate_schema(text_content: str, source_files: list, source_url: str) -> dict:
    llm = LLMClient()

    SYSTEM_MSG = "You are an expert data extractor who creates metadata for government scheme documents."

    USER_PROMPT = f"""
Given the following content from a government scheme (webpage + PDFs), extract structured metadata using this schema:

{{
  "scheme_name": ...,
  "scheme_type": "National" or "State",
  "admin_body": ...,
  "location_scope": "Pan-India" or state name,
  "duration": ...,
  "sector_tags": [...],
  "target_entities": [...],
  "user_stage": [...],
  "pre_approval_required": True or False,
  "source_url": {source_url}
  "source_files": {json.dumps(source_files)}
}}

--- START CONTENT ---
{text_content[:8000]}
--- END CONTENT ---
Only return the JSON.
"""

    return llm.run_json(SYSTEM_MSG, USER_PROMPT)

def main():
    # ==== UPDATE THESE ====
    webpage_txt = ""
    pdf_files = [
        "data/raw/pdfs/karnataka_industrial_policy.pdf"
    ]
    output_file = "output/kip_schema.json"
    # =======================

    logger.info("Reading webpage text...")
    all_text = read_text_file(webpage_txt)

    logger.info("Reading PDFs...")
    for pdf in pdf_files:
        pdf_text = extract_text_from_pdf(pdf)
        all_text += f"\n\n--- PDF: {os.path.basename(pdf)} ---\n" + pdf_text

    logger.info("Generating schema from LLM...")
    schema = generate_schema(all_text, [webpage_txt] + pdf_files, source_url = "https://investkarnataka.co.in/wp-content/uploads/2025/02/IndustrialPolicy2025_PrintPagesSingle_.pdf" )

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    logger.info(f"Schema written to {output_file}")

if __name__ == "__main__":
    main()
