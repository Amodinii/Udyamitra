'''
intent_pipeline.py - Combines metadata extraction and tool mapping into a single abstraction.
'''

from router.model import Metadata
from .extractor import MetadataExtractor
from .tool_mapper import ToolMapper

class IntentPipeline:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct", mapping_file: str = "Meta/mapping.json"):
        self.extractor = MetadataExtractor(model=model)
        self.tool_mapper = ToolMapper(mapping_file=mapping_file)

    def run(self, query: str) -> Metadata:
        metadata = self.extractor.extract_metadata(query)
        enriched_metadata = self.tool_mapper.map_tools(metadata)
        return enriched_metadata
