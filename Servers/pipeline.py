import json
import asyncio
from enum import Enum, auto

from utility.model import Metadata, ExecutionPlan, ConversationState
from Meta.pipeline import IntentPipeline
from router.planner import Planner
from router.ToolExecutor import ToolExecutor
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.StateManager import StateManager

class PipelineStage(Enum):
    IDLE = auto()
    METADATA_EXTRACTION = auto()
    PLANNING = auto()
    EXECUTION = auto()
    COMPLETED = auto()
    ERROR = auto()

class Pipeline:
    def __init__(self, user_query: str, state: ConversationState = None, log_file: str = "pipeline_log.txt"):
        self.user_query = user_query
        self.log_file = log_file
        self.stage = PipelineStage.IDLE
        self.status_message = "Initialized."
        self.metadata: Metadata | None = None
        self.plan: ExecutionPlan | None = None
        self.results = None

        # Maintain conversation state
        self.conversation_state = state if state is not None else ConversationState()

        # Clear previous logs
        open(self.log_file, "w").close()

    def log(self, content: str):
        with open(self.log_file, "a") as f:
            f.write(content + "\n\n")

    def set_stage(self, stage: PipelineStage, message: str):
        self.stage = stage
        self.status_message = message
        logger.info(f"[{stage.name}] {message}")
        self.log(f"{stage.name}:\n{message}")

    def extract_metadata(self):
        self.set_stage(PipelineStage.METADATA_EXTRACTION, "Extracting metadata from user query...")
        extractor = IntentPipeline()
        self.metadata = extractor.run(self.user_query, state=self.conversation_state)
        self.log(f"Extracted Metadata:\n{self.metadata.model_dump_json(indent=2)}")

        # --- State-aware topic switch detection ---
        state_manager = StateManager(initial_state=self.conversation_state)

        new_intent = self.metadata.intents[0] if self.metadata.intents else None
        new_scheme = self.metadata.entities.get("scheme") if self.metadata.entities else None

        last_intent = self.conversation_state.last_intent
        last_scheme = self.conversation_state.last_scheme_mentioned

        if (new_intent and new_intent != last_intent) or (new_scheme and new_scheme != last_scheme):
            logger.debug("[Pipeline] Detected topic switch. Resetting partial state.")
            state_manager.reset_on_topic_switch()

    def plan_execution(self):
        self.set_stage(PipelineStage.PLANNING, "Building execution plan...")
        planner = Planner()
        self.plan = planner.build_plan(self.metadata, state=self.conversation_state)
        self.log(f"Execution Plan:\n{self.plan.model_dump_json(indent=2)}")

        # --- Update intent and scheme in state ---
        state_manager = StateManager(initial_state=self.conversation_state)

        if self.metadata.intents:
            state_manager.set_last_intent(self.metadata.intents[0])

        if self.metadata.entities and "scheme" in self.metadata.entities:
            state_manager.set_last_scheme(self.metadata.entities["scheme"])

    async def execute_plan(self):
        self.set_stage(PipelineStage.EXECUTION, "Running execution plan with tool executor...")

        executor = ToolExecutor(conversation_state=self.conversation_state)
        self.results = await executor.run_execution_plan(self.plan, self.metadata)
        self.log(f"Execution Results:\n{json.dumps(self.results, indent=2)}")

        # --- Clear missing inputs for successful tools ---
        state_manager = StateManager(initial_state=self.conversation_state)

        for task in self.plan.task_list:
            tool_name = task.tool_name
            tool_output = self.results.get(tool_name)

            if tool_output and not tool_output.get("error"):
                state_manager.clear_missing_inputs(tool_name)

    async def run(self):
        try:
            self.log(f"User Query:\n{self.user_query}")
            self.extract_metadata()
            self.plan_execution()
            await self.execute_plan()

            self.set_stage(PipelineStage.COMPLETED, "Pipeline execution completed successfully.")

            with open("output.json", "w") as f:
                json.dump(self.results, f, indent=2)

            return {
                "results": self.results,
                "conversation_state": self.conversation_state.model_dump()
            }

        except UdayamitraException as ue:
            self.set_stage(PipelineStage.ERROR, f"UdayamitraException: {str(ue)}")
        except Exception as e:
            self.set_stage(PipelineStage.ERROR, f"Unexpected error: {str(e)}")

        return None

    def get_status(self):
        return {
            "stage": self.stage.name,
            "message": self.status_message,
            "results": self.results if self.stage == PipelineStage.COMPLETED else None,
            "state": self.conversation_state.model_dump()
        }