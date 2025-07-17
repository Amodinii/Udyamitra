'''
test.py - Unit test for IntentPipeline abstraction
'''

from Meta.pipeline import IntentPipeline
from utility.model import Metadata

def test_pipeline():
    pipeline = IntentPipeline()
    query = "Can you explain the benefits of the PMEGP scheme for women entrepreneurs in Maharashtra?"

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