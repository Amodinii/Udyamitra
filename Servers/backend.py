from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

from .pipeline import Pipeline  # adjust import if needed
from utility.model import ConversationState, Message

app = FastAPI(title="Pipeline API")

# Allow CORS (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
pipeline_instance = None
conversation_state = ConversationState()

# Request schema
class StartRequest(BaseModel):
    user_query: str

class ContinueRequest(BaseModel):
    user_query: str

# POST /start (fresh chat)
@app.post("/start")
async def start_pipeline(request: StartRequest):
    global pipeline_instance, conversation_state

    # Reset memory at start
    conversation_state = ConversationState()
    conversation_state.messages.append(
        Message(role="user", content=request.user_query, timestamp=datetime.now())
    )

    # Initialize and run pipeline with fresh state
    pipeline_instance = Pipeline(request.user_query, state=conversation_state)
    output = await pipeline_instance.run()

    print("Pipeline output:", output)  # ✅ Debugging output

    # Safely extract assistant reply
    if output and "results" in output:
        result_messages = []
        for tool_name, result_text in output["results"].items():
            result_messages.append(f"### Tool used: {tool_name}\n\n{result_text}")
        assistant_response = "\n\n".join(result_messages)

        # Add assistant message to conversation
        conversation_state.messages.append(
            Message(role="assistant", content=assistant_response, timestamp=datetime.now())
        )
    else:
        assistant_response = "I'm sorry, I couldn't generate a response."

    return {
        "message": assistant_response,
        "stage": pipeline_instance.stage.name,
        "result": output["results"] if output else None,
        "state": conversation_state.model_dump()
    }

# POST /continue (follow-up query)
@app.post("/continue")
async def continue_pipeline(request: ContinueRequest):
    global pipeline_instance, conversation_state

    # Add follow-up message to history
    conversation_state.messages.append(
        Message(role="user", content=request.user_query, timestamp=datetime.now())
    )

    if pipeline_instance is None:
        # Fallback: no prior pipeline, create one with current state
        pipeline_instance = Pipeline(request.user_query, state=conversation_state)
    else:
        # Update query and preserve pipeline + state
        pipeline_instance.user_query = request.user_query
        pipeline_instance.conversation_state = conversation_state

    output = await pipeline_instance.run()

    if output:
        # Add assistant response from this run
        assistant_response = output.get("output_text", "")
        conversation_state.messages.append(
            Message(role="assistant", content=assistant_response, timestamp=datetime.now())
        )
    else:
        assistant_response = "I'm sorry, something went wrong while continuing."

    return {
        "message": assistant_response,
        "stage": pipeline_instance.stage.name,
        "result": output.get("results") if output else None,
        "state": conversation_state.model_dump()
    }

# GET /status
@app.get("/status")
async def get_status():
    if pipeline_instance is None:
        return {"message": "No pipeline started yet"}
    return pipeline_instance.get_status()