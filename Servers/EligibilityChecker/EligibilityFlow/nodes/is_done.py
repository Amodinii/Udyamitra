from ..state import EligibilityState

def is_done_node(state: EligibilityState) -> str:
    if not state.missing_fields:
        return "done"
    return "ask"
