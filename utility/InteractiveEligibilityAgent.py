from utility.model import EligibilityCheckRequest
from Servers.EligibilityChecker.EligibilityChecker import EligibilityChecker

class InteractiveEligibilityAgent:
    def __init__(self, checker=None):
        self.checker = checker or EligibilityChecker()
        self.collected_fields = {}

    def is_missing(self, response):
        return response.eligible is None and response.missing_fields

    def generate_question(self, missing_field: str) -> str:
        return f"Can you tell me your {missing_field}?"

    def update_user_profile(self, field_name, value):
        self.collected_fields[field_name] = value

    def build_request(self, previous_request: EligibilityCheckRequest):
        new_profile = previous_request.user_profile.model_dump()
        new_profile.update(self.collected_fields)
        return EligibilityCheckRequest(
            scheme_name=previous_request.scheme_name,
            user_profile=new_profile,
            query=previous_request.query,
            context_entities=previous_request.context_entities,
            detected_intents=previous_request.detected_intents,
        )

    def rerun(self, prev_request, prev_response):
        if not self.is_missing(prev_response):
            return prev_response

        for field in prev_response.missing_fields:
            question = self.generate_question(field)
            print(question)
            answer = input("> ")
            self.update_user_profile(field, answer)

        new_request = self.build_request(prev_request)
        return self.checker.check_eligibility(new_request)
