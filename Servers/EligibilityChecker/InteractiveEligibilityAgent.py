from utility.model import EligibilityCheckRequest
from .EligibilityChecker import EligibilityChecker
from .QuestionGenerator import QuestionGenerator

class InteractiveEligibilityAgent:
    def __init__(self, checker=None):
        self.checker = checker or EligibilityChecker()
        self.question_generator = QuestionGenerator()

        # Internal state
        self.collected_fields = {}
        self.follow_ups = []
        self.missing_fields = []
        self.prev_request = None
        self.scheme_name = None
        self.retrieved_documents = None

    def start(self, request: EligibilityCheckRequest, retrieved_documents: str = None):
        """
        Kicks off the interactive eligibility check.
        Stores the initial request and prepares follow-up questions.
        """
        self.prev_request = request
        self.scheme_name = request.scheme_name
        self.retrieved_documents = retrieved_documents

        result = self.checker.check_eligibility(request, retrieved_documents)

        # If already eligible or ineligible
        if "follow_up_questions" not in result or not result.get("follow_up_questions"):
            return {"done": True, "result": result}

        self.follow_ups = result["follow_up_questions"]
        self.missing_fields = result["eligibility"].get("missing_fields", [])

        return self.ask_next_question()

    def ask_next_question(self):
        """
        Pops and returns the next follow-up question.
        """
        if not self.follow_ups or not self.missing_fields:
            return {"done": True}

        question = self.follow_ups.pop(0)
        field = self.missing_fields.pop(0)

        return {
            "done": False,
            "field": field,
            "question": question
        }

    def receive_answer(self, field_name: str, answer: str):
        """
        Stores the user’s answer against the field.
        """
        self.collected_fields[field_name] = answer

    def finalize(self):
        """
        Builds a new request with updated user profile and rechecks eligibility.
        """
        if not self.prev_request:
            raise ValueError("Eligibility session not started. Call `start()` first.")

        updated_profile = self.prev_request.user_profile.model_dump()
        updated_profile.update(self.collected_fields)

        new_request = EligibilityCheckRequest(
            scheme_name=self.scheme_name,
            user_profile=updated_profile,
            query=self.prev_request.query,
            context_entities=self.prev_request.context_entities,
            detected_intents=self.prev_request.detected_intents,
        )

        final_result = self.checker.check_eligibility(new_request, self.retrieved_documents)

        return {
            "done": True,
            "result": final_result
        }
