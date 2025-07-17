import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PlaywrightURLLoader, PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# === Load env vars ===
load_dotenv()

# === Re-fetch target URLs ===
refetch_urls = [
    "https://ism.gov.in/design-linked-incentive",
    "https://www.meity.gov.in/offerings/schemes-and-services/details/production-linked-incentive-scheme-pli-2-0-for-it-hardware-wM0MDOtQWa",
    "https://www.meity.gov.in/offerings/schemes-and-services/details/scheme-for-promotion-of-manufacturing-of-electronic-components-and-semiconductors-specs-AMxIDOtQWa",
    "https://www.meity.gov.in/offerings/schemes-and-services/details/modified-special-incentive-package-scheme-m-sips-IDNyETMtQWa",
    "https://www.meity.gov.in/offerings/schemes-and-services/details/electronic-manufacturing-clusters-emc-scheme-kTO5EjMtQWa",
    "https://www.meity.gov.in/offerings/schemes-and-services/details/modified-electronics-manufacturing-clusters-emc-2-0-scheme-wNyEDOtQWa",
    "https://www.meity.gov.in/offerings/schemes-and-services/details/electronic-hardware-schemes-AN1MDOtQWa",
    "https://msh.meity.gov.in/",
    "https://cleartax.in/s/support-international-patent-protection-electronics-information-technology-sip-eit",
    "https://riscvindia.org/",
    "https://wordpress.missionstartupkarnataka.org/wp-content/uploads/2021/07/Special-Incentives-Scheme-for-ESDM-OPG-Approval.pdf",
    "https://eitbt.karnataka.gov.in/startup/public/policy/en",
    "http://www.kitven.in/funds/karsemven-fund",
    "https://itbtst.karnataka.gov.in/storage/pdf-files/EoI%20for%20Anchor%20Units%20FOR%20emc2ENG.pdf",
    "https://www.coe-iot.com/"
]

# === Directory to save extracted content ===
Path("rerun_results").mkdir(exist_ok=True)

# === Scrape text from webpages ===
def scrape_web(urls):
    print("\n[INFO] Starting Playwright scrape...")
    loader = PlaywrightURLLoader(urls=urls, remove_selectors=["header", "footer", "nav", "script", "style"])
    docs = loader.load()
    print(f"[INFO] Loaded {len(docs)} documents from web.")
    return docs

# === Scrape PDFs (if file extension ends with .pdf) ===
def scrape_pdf(url):
    filename = url.split("/")[-1].split("?")[0]
    pdf_path = f"temp_pdfs/{filename}"
    Path("temp_pdfs").mkdir(exist_ok=True)
    try:
        # Download PDF
        with open(pdf_path, "wb") as f:
            f.write(requests.get(url, timeout=15).content)

        loader = PyMuPDFLoader(pdf_path)
        return loader.load()
    except Exception as e:
        print(f"[ERROR] Failed to load PDF from {url}: {e}")
        return []

# === Split and save chunks ===
def save_chunks(documents, name):
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    texts = [doc.page_content for doc in chunks]
    with open(f"rerun_results/{name}.json", "w", encoding="utf-8") as f:
        json.dump(texts, f, indent=2)
    print(f"[SAVED] {len(texts)} chunks → rerun_results/{name}.json")

# === Main Loop ===
if __name__ == "__main__":
    import requests

    for url in refetch_urls:
        print(f"\nProcessing {url}...")

        if url.endswith(".pdf"):
            docs = scrape_pdf(url)
            key = Path(url).stem.replace(" ", "_").lower()
        else:
            try:
                docs = scrape_web([url])
                key = url.split("/")[2].replace(".", "_")
            except Exception as e:
                print(f"[SKIPPED] Could not fetch: {e}")
                continue

        if docs:
            save_chunks(docs, key)
        else:
            print("[WARNING] No docs found. Skipped.")
