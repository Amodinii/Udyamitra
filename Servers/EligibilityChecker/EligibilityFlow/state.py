from typing import Optional, List, Dict, Union
from pydantic import BaseModel
from utility.model import EligibilityCheckRequest, UserProfile

class EligibilityState(BaseModel):
    user_profile: UserProfile
    scheme_name: str
    context_entities: Optional[Dict[str, Union[str, List[str]]]] = None
    query: Optional[str] = None
    retrieved_documents: Optional[str] = None

    # Eligibility flow data
    eligibility_response: Optional[Dict] = None
    follow_up_questions: Optional[List[str]] = []
    missing_fields: Optional[List[str]] = []
    final_explanation: Optional[str] = None
    last_answer_field: Optional[str] = None

    # NEW FIELDS for interaction
    current_field: Optional[str] = None
    latest_answer: Optional[str] = None

    def to_request(self) -> EligibilityCheckRequest:
        return EligibilityCheckRequest(
            scheme_name=self.scheme_name,
            user_profile=self.user_profile, 
            context_entities=self.context_entities,
            query=self.query
        )

