'''
test.py - Unit test for IntentPipeline abstraction
'''

from Meta.pipeline import IntentPipeline
from utility.model import Metadata

# Sample mapping file (should match your test config)
MAPPING_FILE = "Meta/mapping.json"

def test_pipeline():
    pipeline = IntentPipeline(mapping_file=MAPPING_FILE)
    query = "Is there a capital subsidy if I expand my unit into a Tier-2 city like Dharwad instead of Bengaluru?"

    metadata: Metadata = pipeline.run(query)
    print(metadata)
    print("\n--- Metadata Extracted ---")
    print(f"Query: {metadata.query}")
    print(f"Intents: {metadata.intents}")
    print(f"Tools Required: {metadata.tools_required}")
    print(f"Entities: {metadata.entities}")
    print(f"User Profile: {metadata.user_profile}")

if __name__ == "__main__":
    test_pipeline()