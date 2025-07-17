import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict
from langchain_community.document_loaders import PlaywrightURLLoader, PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from utility.LLM import LLMClient

def get_clean_web_content(url: str) -> str:
    try:
        loader = PlaywrightURLLoader(urls=[url], remove_selectors=["header", "footer", "nav", ".navbar", ".footer"])
        docs = loader.load()
        if docs:
            return docs[0].page_content[:8000]  # Trimming for LLM safety
    except Exception as e:
        print(f"[ERROR] Web scrape failed for {url} → {e}")
    return ""

def extract_pdfs_from_page(url: str) -> List[str]:
    try:
        html = requests.get(url, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        return [urljoin(base_url, a['href']) for a in soup.find_all('a', href=True) if a['href'].lower().endswith('.pdf')]
    except Exception as e:
        print(f"[ERROR] Failed to extract PDFs from {url} → {e}")
        return []

def extract_pdf_content(pdf_urls: List[str]) -> str:
    combined_text = ""
    for pdf_url in pdf_urls:
        try:
            response = requests.get(pdf_url, timeout=10)
            filename = f"temp_{os.path.basename(pdf_url).split('?')[0]}"
            with open(filename, 'wb') as f:
                f.write(response.content)

            loader = PyMuPDFLoader(filename)
            docs = loader.load()
            combined_text += "\n".join([doc.page_content for doc in docs])
            os.remove(filename)

        except Exception as e:
            print(f"[WARN] Skipping PDF {pdf_url} → {e}")
    return combined_text.strip()

def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
    return [chunk.page_content for chunk in splitter.create_documents([text])]

# === PROMPT & METADATA ===
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
        "https://www.meity.gov.in/offerings/schemes-and-services/details/modified-electronics-manufacturing-clusters-emc-2-0-scheme-wNyEDOtQWa",
        "https://www.meity.gov.in/offerings/schemes-and-services/details/electronic-hardware-schemes-AN1MDOtQWa",
        "https://clcss.dcmsme.gov.in/",
        "https://msme.gov.in/schemes/schemes-national-small-industries-corporation",
        "https://riscvindia.org/#:~:text=RISC%2DV%20is%20an%20open,compared%20to%20closed%2Dsource%20alternatives",
        "https://wordpress.missionstartupkarnataka.org/wp-content/uploads/2021/07/Special-Incentives-Scheme-for-ESDM-OPG-Approval.pdf",
        "https://eitbt.karnataka.gov.in/startup/public/policy/en",
        "http://www.kitven.in/funds/karsemven-fund",
        "https://itbtst.karnataka.gov.in/storage/pdf-files/EoI%20for%20Anchor%20Units%20FOR%20emc2ENG.pdf",
        "https://www.coe-iot.com/"
    ]    
    llm = LLMClient()
    final_records = []

    for url in url_list:
        print(f"\nProcessing {url}...")
        web_text = get_clean_web_content(url)
        if not web_text:
            print("Skipped due to page scrape failure.")
            continue

        # Extract metadata
        try:
            prompt = PROMPT_TEMPLATE.format(source_url=url, page_content=web_text)
            metadata = llm.run_json(SYSTEM_MSG, prompt)
        except Exception as e:
            print(f"[ERROR] Metadata extraction failed for {url} → {e}")
            continue

        # Extract PDF content
        pdf_urls = extract_pdfs_from_page(url)
        pdf_text = extract_pdf_content(pdf_urls)

        # Combine all raw text and chunk
        raw_text = web_text + "\n\n" + pdf_text
        chunks = chunk_text(raw_text)

        # Prepare output
        record = {
            "id": re.sub(r'\W+', '_', metadata.get("scheme_name", "unnamed").lower()),
            "scheme_name": metadata.get("scheme_name", ""),
            "aliases": [],
            "source_urls": [url] + pdf_urls,
            "raw_text": raw_text[:5000], 
            "chunks": chunks,
            "metadata": {k: v for k, v in metadata.items() if k not in ["scheme_name", "source_url"]}
        }

        final_records.append(record)
        print(f"Completed {record['id']}")

    # Save result
    with open("processed_scheme_docs.json", "w", encoding="utf-8") as f:
        json.dump(final_records, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(final_records)} records to processed_scheme_docs.json")
