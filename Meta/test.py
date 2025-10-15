'''
test.py - Unit test for IntentPipeline abstraction
'''

from Meta.pipeline import IntentPipeline
from utility.model import Metadata

def test_pipeline():
    pipeline = IntentPipeline()
    #query = "Does Middle East import capacitors from India?"
    query = "Which are the Top Countries Importing Capacitors from India?"

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