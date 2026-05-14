#!/usr/bin/env python3
"""
main.py
-------
Main entry point to run the FastAPI server.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.core.config import settings
from app.core.logging import logger


def main():
    """Start the FastAPI server."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Server: {settings.api_host}:{settings.api_port}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Primary LLM: {settings.primary_model}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
