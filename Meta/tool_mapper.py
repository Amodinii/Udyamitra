'''
tool_mapper.py - Maps extracted intents to actual tool names, ensuring validation and reducing hallucinations.
'''
from utility.model import Metadata
from typing import Dict
import json
import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException

class ToolMapper:
    def __init__(self, mapping_file: str = "Meta/mapping.json"):
        try:
            logger.info(f"Initializing ToolMapper with mapping file: {mapping_file}")
            self.mapping_file = mapping_file
            self.intent_to_tool = self.load_mapping()
            self.available_tools = set(self.intent_to_tool.values())
        except Exception as e:
            logger.error(f"Failed to initialize ToolMapper: {e}")
            raise UdayamitraException("Failed to initialize ToolMapper", sys)

    def load_mapping(self) -> Dict[str, str]:
        try:
            logger.info(f"Loading mapping from file: {self.mapping_file}")
            with open(self.mapping_file, 'r') as f:
                tool_to_intents = json.load(f)
            # Reverse mapping
            intent_to_tool = {}
            for tool, intents in tool_to_intents.items():
                for intent in intents:
                    intent_to_tool[intent] = tool
            return intent_to_tool
        except Exception as e:
            logger.error(f"Failed to load mapping: {e}")
            raise UdayamitraException("Failed to load mapping", sys)

    def map_tools(self, metadata: Metadata) -> Metadata:
        try:
            logger.info(f"Mapping tools for metadata: {metadata}")
            if not metadata.intents:
                logger.warning("No intents found in metadata, skipping tool mapping.")
                return metadata
            mapped_tools = []

            for intent in metadata.intents:
                if intent in self.intent_to_tool:
                    tool = self.intent_to_tool[intent]
                    if tool in self.available_tools:
                        mapped_tools.append(tool)
                else:
                    print(f"Warning: Unrecognized intent '{intent}' — skipping.")

            metadata.tools_required = list(set(mapped_tools))
            return metadata
        except UdayamitraException as e:
            logger.error(f"Error mapping tools: {e}")
            raise e
