import json
import asyncio

from Meta.pipeline import IntentPipeline
from router.planner import Planner
from router.ToolExecutor import run_plan
from utility.input_schema_generator import generate_tool_input  

from Logging.logger import logger
from Exception.exception import UdayamitraException

from utility.model import Metadata, ExecutionPlan

# Sample query
USER_QUERY = "Is my small PCB assembly unit in Mysore eligible for PLI? Or is it only for big companies?"

LOG_FILE = "pipeline_log.txt"

def append_to_log(content: str):
    with open(LOG_FILE, "a") as f:
        f.write(content + "\n\n")

async def main():
    try:
        # Clear previous log
        open(LOG_FILE, "w").close()
        append_to_log(f"User Query:\n{USER_QUERY}")

        # Step 1: Metadata Extraction
        logger.info("Extracting metadata...")
        metadata_extractor = IntentPipeline()
        metadata: Metadata = metadata_extractor.run(USER_QUERY)
        metadata_json = metadata.model_dump_json(indent=2)
        append_to_log(f"Extracted Metadata:\n{metadata_json}")

        # Step 2: Planning
        logger.info("Creating execution plan...")
        planner = Planner()
        plan: ExecutionPlan = planner.build_plan(metadata)
        plan_json = plan.model_dump_json(indent=2)
        append_to_log(f"Execution Plan:\n{plan_json}")

        # Step 2.5: Input Schema Generation (for testing)
        logger.info("Generating input schema from metadata...")
        input_schema = generate_tool_input(input_data=metadata, input_schema_name=plan.task_list[0].input_schema)
        append_to_log(f"Generated Input for First Tool:\n{json.dumps(input_schema, indent=2)}")

        # Step 3: Tool Execution
        logger.info("Running execution plan...")
        results = await run_plan(plan)
        results_json = json.dumps(results, indent=2)
        append_to_log(f"Execution Results:\n{results_json}")
        logger.info("Execution completed successfully.")

        # Print results
        print("\nExecution Results:")
        print(results_json)

        # Also write raw results to separate structured output file
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
