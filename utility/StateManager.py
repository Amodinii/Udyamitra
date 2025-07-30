from utility.model import (
    ConversationState, Message, ToolMemory, UserProfile
)
from typing import Optional, Dict, Any, List
from datetime import datetime
from Logging.logger import logger

MAX_MESSAGE_HISTORY = 7

class StateManager:
    def __init__(self, initial_state: Optional[ConversationState] = None):
        if initial_state:
            self.state = initial_state
            logger.debug("[StateManager] Initialized with existing conversation state.")
        else:
            self.state = ConversationState()
            logger.debug("[StateManager] Initialized with new conversation state.")

    # Message Handling

    def add_message(self, role: str, content: str, tool_used: Optional[str] = None):
        message = Message(
            role=role,
            content=content,
            tool_used=tool_used,
            timestamp=datetime.utcnow()
        )
        self.state.messages.append(message)
        self.trim_messages()

    def trim_messages(self):
        if len(self.state.messages) > MAX_MESSAGE_HISTORY:
            self.state.messages = self.state.messages[-MAX_MESSAGE_HISTORY:]

    # Focus / Intent / Context

    def set_last_scheme(self, scheme_name: str):
        self.state.last_scheme_mentioned = scheme_name

    def set_last_tool(self, tool_name: str):
        self.state.last_tool_used = tool_name

    def set_last_intent(self, intent: str):
        self.state.last_intent = intent

    def update_context_entities(self, new_entities: Dict[str, Any]):
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
            self.set_last_scheme(structured_input.scheme_name)

    # Tool Memory

    def set_tool_memory(self, tool_name: str, memory_data: Dict[str, Any]):
        self.state.tool_memory[tool_name] = ToolMemory(tool_name=tool_name, data=memory_data)

    def get_tool_memory(self, tool_name: str) -> Dict[str, Any]:
        return self.state.tool_memory.get(tool_name, ToolMemory(tool_name=tool_name)).data

    #  Missing Input Tracking 

    def set_missing_inputs(self, tool_name: str, missing_fields: List[str]):
        self.state.missing_inputs[tool_name] = missing_fields

    def clear_missing_inputs(self, tool_name: str):
        if tool_name in self.state.missing_inputs:
            del self.state.missing_inputs[tool_name]

    def get_missing_inputs(self, tool_name: str) -> List[str]:
        return self.state.missing_inputs.get(tool_name, [])

    #  Reset Logic 

    def reset(self):
        """Full reset of conversation state"""
        self.state = ConversationState()

    def reset_on_topic_switch(self):
        """Partial reset for context-sensitive fields"""
        logger.debug("[StateManager] Partial reset due to topic switch.")
        self.state.last_scheme_mentioned = None
        self.state.last_intent = None
        self.state.last_tool_used = None
        self.state.context_entities = {}
        self.state.missing_inputs = {}

    #  State Access

    def get_state(self) -> ConversationState:
        return self.state