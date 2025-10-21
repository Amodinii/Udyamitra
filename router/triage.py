from enum import Enum
from pydantic import BaseModel, Field
from utility.LLM import LLMClient
from Logging.logger import logger

class TriageResult(Enum):
    CHIT_CHAT = "chit_chat"
    KNOWLEDGE_BASED = "knowledge_based"

class ChitChatArgs(BaseModel):
    message: str = Field(..., description="A conversational greeting, follow-up, or non-task-oriented small talk.")

class KnowledgeQueryArgs(BaseModel):
    query: str = Field(..., description="Any user query that requires information, an explanation, or an answer from the knowledge base.")

class TriageClassifier:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        self.llm_client = LLMClient(model=model)
        self.tools = [
            {"type": "function", "function": {"name": "handle_chit_chat", "description": "Route conversational small talk here.", "parameters": ChitChatArgs.model_json_schema()}},
            {"type": "function", "function": {"name": "handle_knowledge_query", "description": "Route any query that requires information or an answer from the knowledge base here. This is the default choice.", "parameters": KnowledgeQueryArgs.model_json_schema()}},
        ]

    def classify(self, query: str) -> TriageResult:
        logger.info(f"[Triage] Classifying query: '{query}'")
        system_prompt = "You are an efficient query routing assistant. Choose the single best function to handle the user's query. Your default choice should be 'handle_knowledge_query' unless it is clearly just small talk."
        
        response = self.llm_client.run_chat(
            system_prompt,
            query,
            tools=self.tools,
            tool_choice="auto"
        )

        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls or tool_calls[0].function.name == "handle_knowledge_query":
            logger.info(f"[Triage] LLM chose route: handle_knowledge_query")
            return TriageResult.KNOWLEDGE_BASED
        else:
            logger.info(f"[Triage] LLM chose route: handle_chit_chat")
            return TriageResult.CHIT_CHAT