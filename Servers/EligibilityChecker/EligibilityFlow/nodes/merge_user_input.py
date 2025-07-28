from EligibilityFlow.state import EligibilityState

async def merge_user_input_node(state: EligibilityState) -> EligibilityState:
    if state.current_field and state.latest_answer:
        state.user_profile[state.current_field] = state.latest_answer

    # Reset for next round
    state.current_field = None
    state.latest_answer = None
    return state
