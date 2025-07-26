from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .pipeline import Pipeline  # adjust if you're not inside a module
import asyncio

app = FastAPI(title="Pipeline API")

# Allow CORS (needed for frontend requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memory store for the pipeline
pipeline_instance = None

# ✅ Create request schema for the POST body
class StartRequest(BaseModel):
    user_query: str

# Start pipeline endpoint
@app.post("/start")
async def start_pipeline(request: StartRequest):
    global pipeline_instance
    pipeline_instance = Pipeline(request.user_query)
    result = await pipeline_instance.run()  
    return {
        "message": "Pipeline completed",
        "stage": pipeline_instance.stage.name,
        "result": result
    }


# Check status endpoint
@app.get("/status")
async def get_status():
    if pipeline_instance is None:
        return {"message": "No pipeline started yet"}
    return pipeline_instance.get_status()