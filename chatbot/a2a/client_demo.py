#!/usr/bin/env python3
"""
Demonstration script for using the A2A client to interact with agents.

This script shows how to use the A2A client to send tasks to agents
and process the responses.
"""

import os
import sys
import logging
import asyncio
import argparse
import json
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import A2A client
from common import A2AClient, Message, TextPart

async def run_client_demo(
    host_url: str = "http://localhost:8000",
    code_url: str = "http://localhost:8001",
    data_url: str = "http://localhost:8002",
    query: Optional[str] = None
):
    """Run the A2A client demonstration."""
    # Get API key from environment variable
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("No GOOGLE_API_KEY environment variable found. Client may not authenticate properly.")
    
    # Create host agent client
    logger.info(f"Connecting to host agent at {host_url}...")
    host_client = A2AClient(agent_url=host_url, api_key=api_key)
    
    try:
        # Get agent card
        host_card = await host_client.card_resolver.get_agent_card(host_url)
        logger.info(f"Connected to {host_card.name}: {host_card.description}")
        
        # List agent skills
        if host_card.skills:
            logger.info("Available skills:")
            for skill in host_card.skills:
                logger.info(f"  - {skill.name}: {skill.description}")
        
        # If no query provided, use an interactive loop
        if not query:
            print("\nInteractive A2A Client Demo")
            print("Type 'exit' or 'quit' to end the demo")
            print("Type 'help' to see available commands")
            
            while True:
                try:
                    # Get user input
                    query = input("\nEnter query or command: ")
                    
                    # Check for exit commands
                    if query.lower() in ["exit", "quit"]:
                        break
                    
                    # Check for help command
                    if query.lower() == "help":
                        print("\nAvailable commands:")
                        print("  help - Show this help message")
                        print("  exit, quit - Exit the demo")
                        print("  card - Show agent card details")
                        print("  skills - List available skills")
                        print("  code <query> - Send query directly to code agent")
                        print("  data <query> - Send query directly to data agent")
                        print("  Or just type your query to use the host agent")
                        continue
                    
                    # Check for card command
                    if query.lower() == "card":
                        print(f"\nAgent Card: {host_card.name} (v{host_card.version})")
                        print(f"Description: {host_card.description}")
                        print(f"URL: {host_card.url}")
                        print(f"Documentation: {host_card.documentationUrl}")
                        print(f"Capabilities: streaming={host_card.capabilities.streaming}, "
                              f"pushNotifications={host_card.capabilities.pushNotifications}")
                        continue
                    
                    # Check for skills command
                    if query.lower() == "skills":
                        print("\nAvailable Skills:")
                        for skill in host_card.skills:
                            print(f"  - {skill.name}: {skill.description}")
                        continue
                    
                    # Check for direct agent commands
                    if query.lower().startswith("code "):
                        # Send to code agent directly
                        code_client = A2AClient(agent_url=code_url, api_key=api_key)
                        code_query = query[5:]  # Remove "code " prefix
                        await send_query_to_agent(code_client, code_query)
                        continue
                    
                    if query.lower().startswith("data "):
                        # Send to data agent directly
                        data_client = A2AClient(agent_url=data_url, api_key=api_key)
                        data_query = query[5:]  # Remove "data " prefix
                        await send_query_to_agent(data_client, data_query)
                        continue
                    
                    # Regular query to host agent
                    await send_query_to_agent(host_client, query)
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error processing query: {e}")
        else:
            # Send single query
            await send_query_to_agent(host_client, query)
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Close client
        await host_client.close()

async def send_query_to_agent(client: A2AClient, query: str):
    """Send a query to an agent and print the response."""
    logger.info(f"Sending query: {query}")
    
    # Create message with query
    message = Message(
        role="user",
        parts=[TextPart(text=query)]
    )
    
    # Check if streaming is supported
    card = await client.card_resolver.get_agent_card(client.agent_url)
    
    if card.capabilities.streaming:
        # Use streaming
        print("\nStreaming response:")
        
        try:
            async for event in client.send_subscribe(message):
                if hasattr(event, "status") and event.status.message:
                    message = event.status.message
                    for part in message.parts:
                        if hasattr(part, "text"):
                            print(part.text, end="")
                            sys.stdout.flush()
                
                if hasattr(event, "artifact"):
                    artifact = event.artifact
                    for part in artifact.parts:
                        if hasattr(part, "text"):
                            print(part.text, end="")
                            sys.stdout.flush()
                
                if getattr(event, "final", False):
                    break
            
            print()  # Add newline after streaming completes
            
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            # Fall back to non-streaming
            print("Falling back to non-streaming mode...")
            task = await client.send_task(message)
            await print_task_result(client, task)
    else:
        # Use non-streaming
        task = await client.send_task(message)
        await print_task_result(client, task)

async def print_task_result(client: A2AClient, task):
    """Print the result of a task."""
    # Poll until task is done
    while task.status.state not in ["completed", "failed", "canceled"]:
        await asyncio.sleep(0.5)
        task = await client.get_task(task.id)
    
    # Print result
    if task.status.state == "completed":
        if task.status.message:
            for part in task.status.message.parts:
                if hasattr(part, "text"):
                    print(f"\nResponse: {part.text}")
        
        if task.artifacts:
            for artifact in task.artifacts:
                for part in artifact.parts:
                    if hasattr(part, "text"):
                        print(f"\nArtifact ({artifact.name}): {part.text}")
    else:
        print(f"\nTask {task.status.state}: {task.status.message}")

def run_demo():
    """Run the A2A client demonstration."""
    parser = argparse.ArgumentParser(description="A2A client demonstration")
    parser.add_argument("--host-url", type=str, default="http://localhost:8000", help="URL for host agent")
    parser.add_argument("--code-url", type=str, default="http://localhost:8001", help="URL for code conversion agent")
    parser.add_argument("--data-url", type=str, default="http://localhost:8002", help="URL for data migration agent")
    parser.add_argument("--query", type=str, help="Query to send to the host agent (if not provided, interactive mode is used)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_client_demo(
            host_url=args.host_url,
            code_url=args.code_url,
            data_url=args.data_url,
            query=args.query
        ))
    except KeyboardInterrupt:
        logger.info("Demo stopped.")

if __name__ == "__main__":
    run_demo() 