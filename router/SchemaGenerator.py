import json
from typing import Dict, Any, Type
from pydantic import BaseModel, ValidationError
from utility.LLM import LLMClient
from utility.model import ConversationState

class SchemaGenerator:
    def __init__(self):
        self.llm = LLMClient(model="meta-llama/llama-4-maverick-17b-128e-instruct")

    def generate(
    self,
    metadata: Dict[str, Any],
    execution_plan: Dict[str, Any],
    model_class: Type[BaseModel],
    user_input: Dict[str, Any] = None,
    state: ConversationState | None = None,
    ) -> Dict[str, Any]:
        user_input = user_input or {}
        context_hint = ""
        if state:
            last_tool = state.last_tool_used or ""
            last_msg = state.messages[-1].content if state.messages else ""
            last_entities = state.context_entities or {}

            context_hint = f"""
            Previous tool used: {last_tool}
            Last assistant message: {last_msg}
            Previously detected entities (if any): {json.dumps(last_entities)}
            Use this context if the current query is ambiguous or a follow-up.
            """
        system_message = (
            "You are an intelligent assistant that helps populate structured input schemas "
            "based on metadata about a user query, a conversation history, and a target schema. "
            "Only return valid JSON matching the schema structure."
        )

        user_message = (
            f"The following is the metadata extracted from a user query:\n\n"
            f"{json.dumps(metadata, indent=2)}\n\n"
            f"And this is the execution plan:\n\n"
            f"{json.dumps(execution_plan, indent=2)}\n\n"
            f"{'Conversation history:\n' + context_hint if state else ''}\n\n"
            f"Based on this information, fill the input for this schema:\n\n"
            f"{model_class.schema_json(indent=2)}\n\n"
            "Return only a valid JSON object matching this schema."
        )

        try:
            llm_output = self.llm.run_json(system_message, user_message)
        except Exception as e:
            raise ValueError(f"Failed to generate schema input via LLM: {e}")

        final_input = {**llm_output, **user_input}
        return final_input


    def generate_instance(
        self,
        metadata: Dict[str, Any],
        execution_plan: Dict[str, Any],
        model_class: Type[BaseModel],
        user_input: Dict[str, Any] = None,
        state: ConversationState | None = None,
    ) -> BaseModel:
        raw_input = self.generate(metadata, execution_plan, model_class, user_input, state)

        try:
            return model_class(**raw_input)
        except ValidationError as e:
            raise ValueError(f"LLM output did not match schema requirements:\n{e}")
