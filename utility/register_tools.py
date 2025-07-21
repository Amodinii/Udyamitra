import json
from typing import Dict
from pathlib import Path
from utility.model import ToolRegistryEntry

TOOL_REGISTRY: Dict[str, ToolRegistryEntry] = {}
REGISTRY_FILE = Path("Meta/tool_registry.json")


def register_tool(tool: ToolRegistryEntry):
    # Fix: Load existing registry first before updating
    global TOOL_REGISTRY
    if not TOOL_REGISTRY:
        existing_registry = load_registry_from_file()
        if existing_registry:
            TOOL_REGISTRY.update(existing_registry)

    TOOL_REGISTRY[tool.tool_name] = tool
    save_registry_to_file()


def save_registry_to_file():
    with open(REGISTRY_FILE, "w") as f:
        json.dump(
            {name: entry.dict() for name, entry in TOOL_REGISTRY.items()},
            f,
            indent=2
        )
    print(f"Registry saved to {REGISTRY_FILE}")


def load_registry_from_file():
    if not REGISTRY_FILE.exists():
        return {}
    with open(REGISTRY_FILE, "r") as f:
        data = json.load(f)
        return {name: ToolRegistryEntry(**entry) for name, entry in data.items()}


def generate_tool_registry_entry() -> ToolRegistryEntry:
    print("\n🔧 Register a New Tool")
    tool_name = input("Tool Name (e.g., SchemeExplainer): ").strip()
    intents = input("Associated Intents (comma-separated, e.g., explain,understand): ").strip().split(",")
    intents = [i.strip().strip('"').strip("'") for i in intents if i.strip()]
    endpoint = input("Endpoint URL (e.g., http://localhost:10001/explain): ").strip()
    input_schema = input("Input Schema (e.g., SchemeMetadata): ").strip()
    output_schema = input("Output Schema (e.g., SchemeExplanationResponse): ").strip()
    model = input("Model used (optional, e.g., llama-4): ").strip()
    description = input("Short Description (optional): ").strip()

    entry = ToolRegistryEntry(
        tool_name=tool_name,
        intents=intents,
        endpoint=endpoint,
        input_schema=input_schema,
        output_schema=output_schema,
        model=model or None,
        description=description or None
    )

    register_tool(entry)
    print(f"Tool '{tool_name}' registered successfully!\n")
    return entry
