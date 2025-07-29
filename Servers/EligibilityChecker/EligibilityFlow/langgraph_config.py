from .state import EligibilityState
from .graph import build_eligibility_graph
from utility.model import EligibilityCheckRequest
from typing import AsyncGenerator

async def run_interactive_eligibility_flow(
    request: EligibilityCheckRequest,
    documents: str = None
) -> AsyncGenerator[str, None]:
    """
    Runs the LangGraph-based eligibility flow for a given request.
    Yields follow-up questions or the final eligibility explanation.
    """

    graph = build_eligibility_graph()

    state = EligibilityState(
        scheme_name=request.scheme_name,
        user_profile=request.user_profile,
        query=request.query,
        context_entities=request.context_entities,
        retrieved_documents=documents,
        eligibility_response=None,
        follow_up_questions=[],
        missing_fields=[],
        final_explanation=None,
        last_answer_field=None
    )

    # Use stream_mode="values" to access `step["state"]`
    async for step in graph.astream(input=state):
        state = state

        if state.final_explanation:
            yield state.final_explanation
            break
        elif state.follow_up_questions:
            yield state.follow_up_questions[0]
