'''
main.py - This is the main entry point for the Udayamitra server.
We are providing all our tools and database here as MCP servers.
'''

import os
import sys
import contextlib
import httpx

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from Logging.logger import logger
from Exception.exception import UdayamitraException

# Importing the MCP servers
from Servers.SchemeExplainer.server import mcp as scheme_explainer_mcp

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MCP server lifespan...")
    try:
        async with scheme_explainer_mcp.session_manager.run():
            logger.info("Scheme MCP server started successfully")
            yield
            logger.info("Shutting down Scheme MCP server...")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise UdayamitraException("Failed to start MCP server", sys)

try:
    logger.info("Creating FastAPI instance...")
    server = FastAPI(lifespan=lifespan)
    server.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:6274",
            "http://127.0.0.1:6274",
            "http://localhost:6277",
            "http://127.0.0.1:6277"
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info("FastAPI instance created successfully")
except Exception as e:
    logger.error(f"Failed to create FastAPI instance: {e}")
    raise UdayamitraException("Failed to create FastAPI instance", sys)

# Health and config endpoints
@server.options("/health")
@server.get("/health")
async def health_check():
    return {"status": "ok"}

@server.options("/config")
@server.get("/config")
async def config():
    return {
        "message": "Udayamitra MCP Server Configuration",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "scheme_explainer": "/explain-scheme"
        }
    }

@server.options("/")
@server.get("/")
async def root():
    return {"message": "Udayamitra MCP Server is running", "version": "1.0.0"}

# proxy endpoint for official MCP Inspector compatibility 
@server.post("/mcp")
async def proxy_mcp(request: Request):
    target_url = request.query_params.get("url")
    if not target_url:
        return {"error": "Missing 'url' query parameter"}
    
    try:
        body = await request.body()
        headers = {key: value for key, value in request.headers.items() if key.lower() != "host"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(target_url, content=body, headers=headers)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={k: v for k, v in resp.headers.items() if k.lower() not in {"content-encoding", "transfer-encoding", "connection"}}
            )
    except Exception as e:
        logger.error(f"Proxying to MCP endpoint failed: {e}")
        return {"error": "Failed to proxy request"}


server.mount("/explain-scheme", scheme_explainer_mcp.streamable_http_app())
PORT = int(os.getenv("SERVER_PORT", 10000))
if __name__ == "__main__":
    logger.info(f"Starting Udayamitra MCP Server on port {PORT}")
    import uvicorn
    uvicorn.run(server, host="0.0.0.0", port=PORT, log_level="debug")