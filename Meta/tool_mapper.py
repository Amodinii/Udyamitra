'''
tool_mapper.py - Maps extracted intents to actual tool names, ensuring validation and reducing hallucinations.
'''
from utility.model import Metadata, ToolRegistryEntry
from utility.register_tools import load_registry_from_file
from typing import Dict
from pathlib import Path
import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException

class ToolMapper:
    def __init__(self):
        try:
            logger.info(f"Initializing ToolMapper")
            self.tool_registry: Dict[str, ToolRegistryEntry] = load_registry_from_file()
            self.intent_to_tool: Dict[str, str] = self.build_reverse_mapping()
        except Exception as e:
            logger.error(f"Failed to initialize ToolMapper: {e}")
            raise UdayamitraException("Failed to initialize ToolMapper", sys)

    def build_reverse_mapping(self) -> Dict[str, str]:
        intent_to_tool = {}
        for tool_name, entry in self.tool_registry.items():
            for intent in entry.intents:
                intent_to_tool[intent] = tool_name
        return intent_to_tool

    def map_tools(self, metadata: Metadata) -> Metadata:
        try:
            if not metadata.intents:
                logger.warning("No intents found in metadata, skipping tool mapping.")
                return metadata

            mapped_tools = set()
            for intent in metadata.intents:
                tool = self.intent_to_tool.get(intent)
                if tool:
                    mapped_tools.add(tool)
                else:
                    logger.warning(f"Unrecognized intent '{intent}' — skipping.")

            metadata.tools_required = list(mapped_tools)
            return metadata

        except Exception as e:
            logger.error(f"Error mapping tools: {e}")
            raise UdayamitraException("Failed to map tools", sys)