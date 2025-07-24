import json
from typing import Dict, Any, Type
from pydantic import BaseModel, ValidationError
from utility.LLM import LLMClient

class SchemaGenerator:
    def __init__(self):
        self.llm = LLMClient(model="meta-llama/llama-4-maverick-17b-128e-instruct")

    def generate(
        self,
        metadata: Dict[str, Any],
        execution_plan: Dict[str, Any],
        model_class: Type[BaseModel],
        user_input: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Uses the LLM to generate missing parts of the input schema.
        Optionally merges user_input to override/fill known fields.
        """
        user_input = user_input or {}

        system_message = (
            "You are an intelligent assistant that helps populate structured input schemas "
            "based on metadata about a user query and a target input schema. "
            "Only return valid JSON matching the target schema's structure."
        )

        user_message = (
            f"The following is the metadata extracted from a user query:\n\n"
            f"{json.dumps(metadata, indent=2)}\n\n"
            f"And this is the execution plan:\n\n"
            f"{json.dumps(execution_plan, indent=2)}\n\n"
            f"Based on this information, fill the input for this schema:\n\n"
            f"{model_class.schema_json(indent=2)}\n\n"
            "Return only a valid JSON object matching this schema."
        )

        try:
            llm_output = self.llm.run_json(system_message, user_message)
        except Exception as e:
            raise ValueError(f"Failed to generate schema input via LLM: {e}")

        # Merge user_input (planner/handoff) into LLM result, taking precedence
        final_input = {**llm_output, **user_input}
        return final_input

    def generate_instance(
        self,
        metadata: Dict[str, Any],
        execution_plan: Dict[str, Any],
        model_class: Type[BaseModel],
        user_input: Dict[str, Any] = None,
    ) -> BaseModel:
        """
        Returns a fully validated Pydantic model instance using LLM-generated fields,
        optionally merging in user-supplied input.
        """
        raw_input = self.generate(metadata, execution_plan, model_class, user_input)

        try:
            return model_class(**raw_input)
        except ValidationError as e:
            raise ValueError(f"LLM output did not match schema requirements:\n{e}")