from EligibilityFlow.state import EligibilityState
from QuestionGenerator import QuestionGenerator

question_generator = QuestionGenerator()

async def generate_question_node(state: EligibilityState) -> EligibilityState:
    if not state.missing_fields:
        # Nothing to ask
        state.follow_up_questions = []
        return state

    questions = question_generator.generate_questions(
        missing_fields=state.missing_fields,
        scheme_name=state.scheme_name
    )
    state.follow_up_questions = questions
    return state
