from EligibilityFlow.state import EligibilityState

def is_done_node(state: EligibilityState) -> str:
    eligibility = state.eligibility_result.get("eligibility", {})
    missing_fields = eligibility.get("missing_fields", [])

    if not missing_fields:
        return "done"
    return "ask_next"
