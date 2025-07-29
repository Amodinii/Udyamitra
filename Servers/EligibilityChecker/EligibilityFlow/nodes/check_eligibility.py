from ..state import EligibilityState
from ...EligibilityChecker import EligibilityChecker

checker = EligibilityChecker()

async def check_eligibility_node(state: EligibilityState) -> EligibilityState:
    result = checker.check_eligibility(
        request=state.to_request(),
        retrieved_documents=state.retrieved_documents
    )

    state.eligibility_response = result["eligibility"]
    state.follow_up_questions = result.get("follow_up_questions", [])
    state.missing_fields = result["eligibility"].get("missing_fields", [])
    state.final_explanation = result.get("explanation")
    return state
