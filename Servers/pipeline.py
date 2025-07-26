import json
import asyncio
from enum import Enum, auto

from utility.model import Metadata, ExecutionPlan
from Meta.pipeline import IntentPipeline
from router.planner import Planner
from router.ToolExecutor import ToolExecutor
from Logging.logger import logger
from Exception.exception import UdayamitraException

class PipelineStage(Enum):
    IDLE = auto()
    METADATA_EXTRACTION = auto()
    PLANNING = auto()
    EXECUTION = auto()
    COMPLETED = auto()
    ERROR = auto()

class Pipeline:
    def __init__(self, user_query: str, log_file: str = "pipeline_log.txt"):
        self.user_query = user_query
        self.log_file = log_file
        self.stage = PipelineStage.IDLE
        self.status_message = "Initialized."
        self.metadata: Metadata | None = None
        self.plan: ExecutionPlan | None = None
        self.results = None

        # Clear previous logs
        open(self.log_file, "w").close()

    # Logging utility
    def log(self, content: str):
        with open(self.log_file, "a") as f:
            f.write(content + "\n\n")

    # Stage transition utility
    def set_stage(self, stage: PipelineStage, message: str):
        self.stage = stage
        self.status_message = message
        logger.info(f"[{stage.name}] {message}")
        self.log(f"{stage.name}:\n{message}")

    def extract_metadata(self):
        self.set_stage(PipelineStage.METADATA_EXTRACTION, "Extracting metadata from user query...")
        extractor = IntentPipeline()
        self.metadata = extractor.run(self.user_query)
        self.log(f"Extracted Metadata:\n{self.metadata.model_dump_json(indent=2)}")

    def plan_execution(self):
        self.set_stage(PipelineStage.PLANNING, "Building execution plan...")
        planner = Planner()
        self.plan = planner.build_plan(self.metadata)
        self.log(f"Execution Plan:\n{self.plan.model_dump_json(indent=2)}")

    async def execute_plan(self):
        self.set_stage(PipelineStage.EXECUTION, "Running execution plan with tool executor...")
        executor = ToolExecutor()
        self.results = await executor.run_execution_plan(self.plan, self.metadata)
        self.log(f"Execution Results:\n{json.dumps(self.results, indent=2)}")

    async def run(self):
        try:
            self.log(f"User Query:\n{self.user_query}")
            self.extract_metadata()
            self.plan_execution()
            await self.execute_plan()

            self.set_stage(PipelineStage.COMPLETED, "Pipeline execution completed successfully.")

            # Save final output
            with open("output.json", "w") as f:
                json.dump(self.results, f, indent=2)

            return self.results  # ✅ Return result to whoever awaits it

        except UdayamitraException as ue:
            self.set_stage(PipelineStage.ERROR, f"UdayamitraException: {str(ue)}")
        except Exception as e:
            self.set_stage(PipelineStage.ERROR, f"Unexpected error: {str(e)}")

        return None  # return None on error


    # Expose status for frontend
    def get_status(self):
        return {
            "stage": self.stage.name,
            "message": self.status_message,
            "results": self.results if self.stage == PipelineStage.COMPLETED else None
        }