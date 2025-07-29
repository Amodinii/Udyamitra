'''
intent_pipeline.py - Combines metadata extraction and tool mapping into a single abstraction.
'''

import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.model import Metadata, ConversationState
from .extractor import MetadataExtractor
from .tool_mapper import ToolMapper

class IntentPipeline:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info(f"Initializing IntentPipeline")
            self.extractor = MetadataExtractor(model=model)
            self.tool_mapper = ToolMapper()
        except Exception as e:
            logger.error(f"Failed to initialize IntentPipeline: {e}")
            raise UdayamitraException("Failed to initialize IntentPipeline", sys)

    def run(self, query: str, state: ConversationState | None = None) -> Metadata:
        try:
            logger.info(f"Running IntentPipeline for query: {query}")
            metadata = self.extractor.extract_metadata(query, state)
            enriched_metadata = self.tool_mapper.map_tools(metadata)
            return enriched_metadata
        except Exception as e:
            logger.error(f"Error running IntentPipeline: {e}")
            raise UdayamitraException("Error running IntentPipeline", sys)