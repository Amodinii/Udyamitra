import json
import asyncio
from utility.ToolExecutor import run_plan

# Sample Execution Plan
example_plan = {
    "execution_type": "sequential",
    "tasks": [
        {
            "tool": "SchemeExplainer",
            "input": {
                "scheme": ["Karnataka ESDM subsidy", "SPECS scheme"]
            },
            "input_from": None
        },
        {
            "tool": "EligibilityChecker",
            "input": {
                "scheme": ["Karnataka ESDM subsidy", "SPECS scheme"],
                "user_profile": {
                    "user_type": "woman_entrepreneur",
                    "location": {
                        "state": "Karnataka",
                        "country": "India"
                    }
                }
            },
            "input_from": "SchemeExplainer"
        }
    ]
}

async def main():
    try:
        results = await run_plan(example_plan)
        print("\nExecution Results:")
        print(json.dumps(results, indent=2))

        # writing the output in the file
        with open("output.json", "w") as f:
            json.dump(results, f, indent=2)
        
    except Exception as e:
        print(f"\nError during plan execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())