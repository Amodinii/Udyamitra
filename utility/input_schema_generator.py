from pydantic import BaseModel, ValidationError
from typing import Dict, Any
from utility.schema_registry import SCHEMA_REGISTRY
from Exception.exception import UdayamitraException
import sys

def generate_tool_input(input_data: Dict[str, Any], input_schema_name: str) -> BaseModel:
    """
    Validate and instantiate a Pydantic model given its name and raw input.
    """
    if input_schema_name not in SCHEMA_REGISTRY:
        raise UdayamitraException(f"Unknown input schema: {input_schema_name}", sys)

    schema_class = SCHEMA_REGISTRY[input_schema_name]
    
    try:
        return schema_class(**input_data)
    except ValidationError as e:
        raise UdayamitraException(f"Validation failed for input to {input_schema_name}: {e}", sys)
