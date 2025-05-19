#!/usr/bin/env python3
# Copyright 2023 Google LLC

"""
Demonstration script for running A2A agents.

This script starts all the necessary agents and demonstrates
how to use them for AWS to GCP migration tasks.
"""

import os
import sys
import logging
import asyncio
import argparse
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import agent implementations
from .agents import CodeConversionAgent, DataMigrationAgent
from .hosts import HostAgent

async def run_demo_async(
    host_port: int = 8000,
    code_port: int = 8001,
    data_port: int = 8002,
    host_url: str = "http://localhost:8000",
    code_url: str = "http://localhost:8001",
    data_url: str = "http://localhost:8002"
):
    """Run the A2A demonstration asynchronously."""
    # Get API key from environment variable
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("No GOOGLE_API_KEY environment variable found. Agents may not work properly.")
    
    # Create task to start code conversion agent
    code_agent_task = asyncio.create_task(
        start_code_agent(api_key, code_port, code_url)
    )
    
    # Create task to start data migration agent
    data_agent_task = asyncio.create_task(
        start_data_agent(api_key, data_port, data_url)
    )
    
    # Wait for agents to start
    await asyncio.sleep(2)
    
    # Create and start host agent
    host_agent = await start_host_agent(api_key, host_port, host_url, code_url, data_url)
    
    # Keep the server running
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        # Cancel agent tasks
        code_agent_task.cancel()
        data_agent_task.cancel()

async def start_code_agent(api_key: Optional[str], port: int, url: str):
    """Start the code conversion agent."""
    logger.info(f"Starting Code Conversion Agent on port {port}...")
    agent = CodeConversionAgent(
        api_key=api_key,
        base_url=url,
        port=port,
        log_level="info"
    )
    agent.run()

async def start_data_agent(api_key: Optional[str], port: int, url: str):
    """Start the data migration agent."""
    logger.info(f"Starting Data Migration Agent on port {port}...")
    agent = DataMigrationAgent(
        api_key=api_key,
        base_url=url,
        port=port,
        log_level="info"
    )
    agent.run()

async def start_host_agent(
    api_key: Optional[str], 
    port: int, 
    url: str, 
    code_agent_url: str, 
    data_agent_url: str
):
    """Start the host agent and connect to specialized agents."""
    logger.info(f"Starting Host Agent on port {port}...")
    
    # Define remote agents
    remote_agents = [
        {"url": code_agent_url, "api_key": api_key},
        {"url": data_agent_url, "api_key": api_key}
    ]
    
    # Create host agent
    agent = HostAgent(
        name="AWS to GCP Migration Host Agent",
        description="Orchestration agent for coordinating AWS to GCP migration tasks",
        base_url=url,
        port=port,
        log_level="info",
        remote_agents=remote_agents
    )
    
    # Run agent
    agent.run()
    
    return agent

def run_demo():
    """Run the A2A demonstration."""
    parser = argparse.ArgumentParser(description="Run A2A agents demonstration")
    parser.add_argument("--host-port", type=int, default=8000, help="Port for host agent")
    parser.add_argument("--code-port", type=int, default=8001, help="Port for code conversion agent")
    parser.add_argument("--data-port", type=int, default=8002, help="Port for data migration agent")
    parser.add_argument("--host", type=str, default="localhost", help="Host address")
    
    args = parser.parse_args()
    
    # Build URLs
    host_url = f"http://{args.host}:{args.host_port}"
    code_url = f"http://{args.host}:{args.code_port}"
    data_url = f"http://{args.host}:{args.data_port}"
    
    try:
        asyncio.run(run_demo_async(
            host_port=args.host_port,
            code_port=args.code_port,
            data_port=args.data_port,
            host_url=host_url,
            code_url=code_url,
            data_url=data_url
        ))
    except KeyboardInterrupt:
        logger.info("Demo stopped.")

if __name__ == "__main__":
    run_demo() 