'''
model.py - This module defines the data model for the router configuration.
'''

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class UserProfile(BaseModel):
    user_type: str #e.g., "woman-entrepreneur", "student"
    location: str

class Metadata(BaseModel):
    intents: List[str]
    tools_required: List[str]
    entities: Dict[str, str]  # e.g., {"scheme": "PMEGP"}
    user_profile: Optional[UserProfile]

class ToolTask(BaseModel):
    tool_name: str
    input: Dict[str, Any]
    input_from: Optional[str] = None # incase there is dependency on another tool's output

class ExecutionPlan(BaseModel):
    execution_type:  Literal["sequential", "parallel"]
    task_list: List[ToolTask]