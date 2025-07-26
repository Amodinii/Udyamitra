from utility.LLM import LLMClient

class QuestionGenerator:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        self.llm = LLMClient(model=model)

    def generate_questions(self, missing_fields: list[str], scheme_name: str = None) -> list[str]:
        prompt = f"""
        You are an assistant that generates follow-up questions to collect missing information for checking eligibility in a government scheme.
        
        Scheme: {scheme_name or "Unknown"}
        Missing Fields: {', '.join(missing_fields)}

        Write clear, simple questions for each field.

        Return a JSON object like:
        {{
            "questions": [
                "Question 1?",
                "Question 2?"
            ]
        }}
        """
        response = self.llm.run_json("Generate follow-up questions.", prompt)
        return response["questions"]

