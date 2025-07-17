import os
from dotenv import load_dotenv
from astrapy.db import AstraDB
from langchain_community.document_loaders import PlaywrightURLLoader, PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()
ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_DB_APPLICATION_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
COLLECTION_NAME = "electronic_schemes"

# Web Page Definitions
web_pages = [
    {
        "url": "https://www.meity.gov.in/offerings/schemes-and-services/details/production-linked-incentive-scheme-pli-2-0-for-it-hardware-wM0MDOtQWa",
        "metadata": {
            "scheme_name": "PLI 2.0 for IT Hardware",
            "scheme_type": "National",
            "admin_body": "MeitY",
            "location_scope": "Pan-India",
            "user_stage": ["Awareness", "Research", "Decision", "Application"],
            "sector_tags": ["Electronics", "IT Hardware"],
            "pre_approval_required": True
        }
    },
    {
    "url": "https://ism.gov.in/design-linked-incentive",
    "metadata": {
        "scheme_name": "Design Linked Incentive (DLI) Scheme",
        "scheme_type": "National",
        "admin_body": "MeitY / India Semiconductor Mission",
        "location_scope": "Pan-India",
        "duration": "2022-2025",
        "sector_tags": ["Semiconductor", "EDA Tools", "IP Cores", "Design"],
        "target_entities": ["Startups", "MSMEs", "Domestic Companies"],
        "user_stage": ["Research", "Decision", "Application", "Follow-up"],
        "pre_approval_required": True,
        "source_url": "https://ism.gov.in/design-linked-incentive"
        }
    },
    {
    "url":"https://www.meity.gov.in/offerings/schemes-and-services/details/production-linked-incentive-scheme-pli-2-0-for-it-hardware-wM0MDOtQWa",
    "metadata": {
        "scheme_name": "PLI 2.0 for IT Hardware",
        "scheme_type": "National",
        "admin_body": "MeitY",
        "location_scope": "Pan-India",
        "duration": "2023-2031",
        "sector_tags": ["Electronics", "IT Hardware", "Manufacturing"],
        "target_entities": ["Global Companies", "Hybrid Companies", "Domestic MSMEs"],
        "user_stage": ["Research", "Decision", "Application", "Follow-up"],
        "pre_approval_required": True,
        "source_url": "https://www.meity.gov.in/offerings/schemes-and-services/details/production-linked-incentive-scheme-pli-2-0-for-it-hardware-wM0MDOtQWa"
        }
    },
    {
    "url":"https://www.meity.gov.in/offerings/schemes-and-services/details/scheme-for-promotion-of-manufacturing-of-electronic-components-and-semiconductors-specs-AMxIDOtQWa",
    "metadata":{
        "scheme_name": "SPECS (Scheme for Promotion of Manufacturing of Electronic Components and Semiconductors)",
        "scheme_type": "National",
        "admin_body": "MeitY",
        "location_scope": "Pan-India",
        "duration": "2020-2023 (applications open until 31 Mar 2023)",
        "sector_tags": ["Electronics", "Semiconductors", "Components", "Manufacturing"],
        "target_entities": ["Domestic electronics manufacturers", "New units", "Expansion units"],
        "user_stage": ["Research", "Decision", "Application", "Follow-up"],
        "pre_approval_required": True,
        "source_url": "https://www.meity.gov.in/offerings/schemes-and-services/details/scheme-for-promotion-of-manufacturing-of-electronic-components-and-semiconductors-specs-AMxIDOtQWa"
        }
    }

]

#PDF File Definitions
pdf_files = [
    {
        "file_path": "docs/MSIPS_Guidelines_2022.pdf",  # You download this manually beforehand
        "metadata": {
            "scheme_name": "MSIPS",
            "scheme_type": "National",
            "admin_body": "MeitY",
            "location_scope": "Pan-India",
            "user_stage": ["Application"],
            "sector_tags": ["Electronics", "Capital Subsidy"],
            "pre_approval_required": True,
            "source_type": "pdf",
            "source_title": "MSIPS Guidelines 2022",
            "source_url": "https://www.meity.gov.in/path-to/msips-guidelines-2022.pdf"
        }
    },
    # Add more PDFs here...
]

# Load Web Pages
loader = PlaywrightURLLoader(urls=[p["url"] for p in web_pages], remove_selectors=["header", "footer"])
web_docs = loader.load()

# Attach metadata to web chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
all_chunks = []

for i, doc in enumerate(web_docs):
    base_meta = web_pages[i]["metadata"]
    chunks = splitter.split_documents([doc])
    for chunk in chunks:
        chunk.metadata.update(base_meta)
    all_chunks.extend(chunks)

# Load PDF Files
for pdf in pdf_files:
    pdf_loader = PyMuPDFLoader(pdf["file_path"])
    pdf_docs = pdf_loader.load()
    chunks = splitter.split_documents(pdf_docs)
    for chunk in chunks:
        chunk.metadata.update(pdf["metadata"])
    all_chunks.extend(chunks)

print(f"Total chunks prepared: {len(all_chunks)}")

#Embed & Upload to AstraDB
embedder = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = embedder.encode([chunk.page_content for chunk in all_chunks], show_progress_bar=True)

astra_db = AstraDB(
    token=ASTRA_DB_APPLICATION_TOKEN,
    api_endpoint=ASTRA_DB_API_ENDPOINT
)
collection = astra_db.collection(COLLECTION_NAME)

docs_to_upload = []
for i, chunk in enumerate(all_chunks):
    docs_to_upload.append({
        "_id": f"chunk_{i}",
        "text": chunk.page_content,
        "metadata": chunk.metadata,
        "$vector": embeddings[i].tolist()
    })

result = collection.insert_many(docs_to_upload)
print(f"Uploaded {len(docs_to_upload)} chunks to AstraDB successfully.")
