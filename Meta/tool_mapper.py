'''
tool_mapper.py - Maps extracted intents to actual tool names, ensuring validation and reducing hallucinations.
'''
from router.model import Metadata
from typing import Dict
import json
import os

class ToolMapper:
    def __init__(self, mapping_file: str = "Meta/mapping.json"):
        self.mapping_file = mapping_file
        self.intent_to_tool = self.load_mapping()
        self.available_tools = set(self.intent_to_tool.values())

    def load_mapping(self) -> Dict[str, str]:
        with open(self.mapping_file, 'r') as f:
            tool_to_intents = json.load(f)
        
        # Reverse mapping
        intent_to_tool = {}
        for tool, intents in tool_to_intents.items():
            for intent in intents:
                intent_to_tool[intent] = tool

        return intent_to_tool


    def map_tools(self, metadata: Metadata) -> Metadata:
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
