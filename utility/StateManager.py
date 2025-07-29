'''
StateManager.py - This module defines the state manager for our application.
'''

from utility.model import ConversationState, Message, ToolMemory, UserProfile
from typing import Optional, Dict, Any
from datetime import datetime
from Logging.logger import logger


class StateManager:
    def __init__(self, initial_state: Optional[ConversationState] = None):
        if initial_state:
            self.state = initial_state
            logger.debug("[StateManager] Initialized with existing conversation state.")
        else:
            self.state = ConversationState()
            logger.debug("[StateManager] Initialized with new conversation state.")

    def add_message(self, role: str, content: str, tool_used: Optional[str] = None):
        message = Message(
            role=role,
            content=content,
            tool_used=tool_used,
            timestamp=datetime.utcnow()
        )
        self.state.messages.append(message)

    def set_focus(self, focus: str):
        self.state.current_focus = focus

    def set_last_tool(self, tool_name: str):
        self.state.last_tool_used = tool_name

    def update_context_entities(self, new_entities: Dict[str, Any]):
        # Normalize location
        if "location" in new_entities and isinstance(new_entities["location"], dict):
            loc = new_entities["location"]
            new_entities["location"] = ", ".join(
                filter(None, [loc.get("city"), loc.get("state"), loc.get("country")])
            )
        self.state.context_entities.update(new_entities)

    def update_user_profile(self, profile: UserProfile):
        self.state.user_profile = profile
        logger.debug(f"[StateManager] Updated user profile: {profile}")

    def update_from_schema(self, structured_input: Any):
        if hasattr(structured_input, 'user_profile') and structured_input.user_profile:
            self.update_user_profile(structured_input.user_profile)
        if hasattr(structured_input, 'context_entities') and structured_input.context_entities:
            self.update_context_entities(structured_input.context_entities)
        if hasattr(structured_input, 'scheme_name') and structured_input.scheme_name:
            self.set_focus(structured_input.scheme_name)

    def set_tool_memory(self, tool_name: str, memory_data: Dict[str, Any]):
        self.state.tool_memory[tool_name] = ToolMemory(tool_name=tool_name, data=memory_data)

    def get_tool_memory(self, tool_name: str) -> Dict[str, Any]:
        return self.state.tool_memory.get(tool_name, ToolMemory(tool_name=tool_name)).data

    def get_state(self) -> ConversationState:
        return self.state

    def reset(self):
        self.state = ConversationState()