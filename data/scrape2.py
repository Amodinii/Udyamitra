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
  "source_url": {source_url},
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
    webpage_txt = "data/raw/webpages/NSIC/Digital service felicitation.txt"
    pdf_files = [
        "data/raw/pdfs/NSIC/3.OnlineWorkshopsolarBusiness02082021.pdf",
        "data/raw/pdfs/NSIC/3DModelingAnalysis_21022023.pdf",
        "data/raw/pdfs/NSIC/24.TestingFacilities03082021.pdf",
        "data/raw/pdfs/NSIC/activity-brochure01072021.pdf",
        "data/raw/pdfs/NSIC/Beautician_04072024.pdf",
        "data/raw/pdfs/NSIC/BoutiqueManagement_04072024.pdf",
        "data/raw/pdfs/NSIC/COAL_FY_2021-22_07062024.pdf",
        "data/raw/pdfs/NSIC/COAL_FY_2022-23_07062024.pdf",
        "data/raw/pdfs/NSIC/COAL_FY_2023-24_07062024.pdf",
        "data/raw/pdfs/NSIC/design-training-calendar_28082024.pdf",
        "data/raw/pdfs/NSIC/Details_of_Testing_23042024.pdf",
        "data/raw/pdfs/NSIC/DIC29072019.pdf",
        "data/raw/pdfs/NSIC/DNB_PNP_LIST_25012023.pdf",
        "data/raw/pdfs/NSIC/DSF_Customer_Application_Form_17072023.pdf",
        "data/raw/pdfs/NSIC/EDPFORM052022_U20062022.pdf",
        "data/raw/pdfs/NSIC/Entrepreneurship_Development_Programme_04072024.pdf",
        "data/raw/pdfs/NSIC/FAQs-NSIC.pdf",
        "data/raw/pdfs/NSIC/Incubator_Training_Calendar_04072024.pdf",
        "data/raw/pdfs/NSIC/Job_oriented_courses_04072024.pdf",
        "data/raw/pdfs/NSIC/Job-fair-24012025.pdf",
        "data/raw/pdfs/NSIC/Job-fair-27092024.pdf",
        "data/raw/pdfs/NSIC/KMC29072019.pdf",
        "data/raw/pdfs/NSIC/Mechanical_Training_Calendar_20022023.pdf",
        "data/raw/pdfs/NSIC/NCVT_Advetisement_04072023.pdf",
        "data/raw/pdfs/NSIC/new29072019.pdf",
        "data/raw/pdfs/NSIC/NTSC_Okhla_ElectronicsElectricalCourses_11022025.pdf",
        "data/raw/pdfs/NSIC/PDReverseEngg_21022023.pdf",
        "data/raw/pdfs/NSIC/RapidPrototyping-3DPrinting_21022023.pdf",
        "data/raw/pdfs/NSIC/RawMaterialAssistance.pdf",
        "data/raw/pdfs/NSIC/RMA-APP-14072023.pdf",
        "data/raw/pdfs/NSIC/RMDFAQs_04112022.pdf",
        "data/raw/pdfs/NSIC/tmscheme.pdf",
        "data/raw/pdfs/NSIC/Tool_Room_MechanicalDesign_21022023.pdf",
        "data/raw/pdfs/NSIC/Training_Calendar_2023-24_27092023.pdf",
        "data/raw/pdfs/NSIC/Training_Calendar_Multimedia_Website_Development_Digital_Marketing_08072024.pdf",
        "data/raw/pdfs/NSIC/Trainingon_ANSYS_Software_21022023.pdf",
        "data/raw/pdfs/NSIC/TrainingReverseEngg_21022023.pdf",
        "data/raw/pdfs/NSIC/trg_cal_Computer_Course_Calender_08082024.pdf",
        "data/raw/pdfs/NSIC/Workshop_CMM_Leaflet_20022023.pdf",
        "data/raw/pdfs/NSIC/Workshop_SPARE_CAPACITY_AND_JOB WORK_20022023.pdf"
    ]
    output_file = "output/nsic_schema.json"
    # =======================

    logger.info("Reading webpage text...")
    all_text = read_text_file(webpage_txt)

    logger.info("Reading PDFs...")
    for pdf in pdf_files:
        pdf_text = extract_text_from_pdf(pdf)
        all_text += f"\n\n--- PDF: {os.path.basename(pdf)} ---\n" + pdf_text

    logger.info("Generating schema from LLM...")
    schema = generate_schema(all_text, [webpage_txt] + pdf_files, source_url = "https://msme.gov.in/schemes/schemes-national-small-industries-corporation" )

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    logger.info(f"Schema written to {output_file}")

if __name__ == "__main__":
    main()
