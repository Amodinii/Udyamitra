import json
import asyncio
from utility.model import Metadata, ExecutionPlan
from Meta.pipeline import IntentPipeline
from router.planner import Planner
from router.ToolExecutor import ToolExecutor
from Logging.logger import logger
from Exception.exception import UdayamitraException

USER_QUERY = "Is my small PCB assembly unit in Mysore eligible for PLI? Or is it only for big companies?"
LOG_FILE = "pipeline_log.txt"

def append_to_log(content: str):
    with open(LOG_FILE, "a") as f:
        f.write(content + "\n\n")

async def main():
    try:
        # Clear old logs
        open(LOG_FILE, "w").close()
        append_to_log(f"User Query:\n{USER_QUERY}")

        # Step 1: Metadata Extraction
        logger.info("Extracting metadata...")
        metadata_extractor = IntentPipeline()
        metadata: Metadata = metadata_extractor.run(USER_QUERY)
        append_to_log(f"Extracted Metadata:\n{metadata.model_dump_json(indent=2)}")

        # Step 2: Execution Planning
        logger.info("Creating execution plan...")
        planner = Planner()
        plan: ExecutionPlan = planner.build_plan(metadata)
        append_to_log(f"Execution Plan:\n{plan.model_dump_json(indent=2)}")

        # Step 3: Tool Execution using LLM-resolved input
        logger.info("Running execution plan...")
        executor = ToolExecutor()
        results = await executor.run_execution_plan(plan, metadata)
        append_to_log(f"Execution Results:\n{json.dumps(results, indent=2)}")

        # Print results to console
        print("\n Final Execution Results:\n")
        print(json.dumps(results, indent=2))

        # Write output to file
        with open("output.json", "w") as f:
            json.dump(results, f, indent=2)

    except UdayamitraException as ue:
        logger.error(f"Udayamitra-specific error: {str(ue)}")
        append_to_log(f"UdayamitraException:\n{str(ue)}")
    except Exception as e:
        logger.exception(f"Unexpected error during pipeline execution: {str(e)}")
        append_to_log(f"Exception:\n{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())