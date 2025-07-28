from EligibilityFlow.state import EligibilityState
from EligibilityFlow.graph import build_eligibility_graph
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

    # Initialize graph and state
    graph = build_eligibility_graph()

    # Build initial state
    state = EligibilityState(
        request=request,
        retrieved_documents=documents,
        current_field=None,
        current_question=None,
        collected_answers={},
        latest_result=None
    )

    # Stream execution
    async for step in graph.astream(input=state, stream_mode="values"):
        state = step  # LangGraph returns updated state at each step

        # If done, yield final explanation
        if step.done:
            yield step.latest_result.get("explanation")
            break

        # Otherwise yield next follow-up question
        elif step.current_question:
            yield step.current_question
