'''
main.py - This is the main entry point for the Udayamitra server.
We are providing all our tools and database here as MCP servers.
'''

import os
import sys
import contextlib
import uvicorn
from fastapi import FastAPI
from Logging.logger import logger
from Exception.exception import UdayamitraException

# Importing the MCP servers
from Servers.SchemeExplainer.server import mcp as scheme_explainer_mcp

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MCP server lifespan...")
    try:
        # MCP servers
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
    logger.info("FastAPI instance created successfully")
except Exception as e:
    logger.error(f"Failed to create FastAPI instance: {e}")
    raise UdayamitraException("Failed to create FastAPI instance", sys)

# Adding some health checks
@server.get("/health")
async def health_check():
    return {"status": "ok"}

@server.get("/")
async def root():
    return {"message": "Udayamitra MCP Server is running", "version": "1.0.0"}


server.mount("/explain-scheme", scheme_explainer_mcp.streamable_http_app())
PORT = int(os.getenv("SERVER_PORT", 10000))

if __name__ == "__main__":
    logger.info(f"Starting Udayamitra MCP Server on port {PORT}")
    uvicorn.run(server, host="0.0.0.0", port=PORT, log_level="debug")