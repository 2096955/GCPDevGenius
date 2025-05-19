import os
import json
import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple

from ..common import (
    AgentCard, AgentSkill, Task, TaskStatus, TaskState,
    A2AClient, A2AClientError, TaskSendParams, Message, TextPart
)
from ..agents import BaseAgent

logger = logging.getLogger(__name__)

class RemoteAgentConnection:
    """Connection to a remote A2A agent."""
    
    def __init__(self, url: str, api_key: Optional[str] = None):
        """Initialize remote agent connection.
        
        Args:
            url: URL of the remote agent
            api_key: API key for authentication (optional)
        """
        self.url = url
        self.api_key = api_key
        self.client = A2AClient(agent_url=url, api_key=api_key)
        self.card: Optional[AgentCard] = None
    
    async def get_card(self) -> AgentCard:
        """Get the agent card for the remote agent."""
        if self.card is None:
            try:
                self.card = await self.client.card_resolver.get_agent_card(self.url)
            except A2AClientError as e:
                logger.error(f"Failed to get agent card from {self.url}: {e}")
                raise
        return self.card
    
    async def send_task(self, message: Union[str, Message], session_id: Optional[str] = None) -> Task:
        """Send a task to the remote agent."""
        if isinstance(message, str):
            message = Message(
                role="user",
                parts=[TextPart(text=message)]
            )
        
        try:
            return await self.client.send_task(message, session_id)
        except A2AClientError as e:
            logger.error(f"Failed to send task to {self.url}: {e}")
            raise
    
    async def get_task(self, task_id: str) -> Task:
        """Get task details from the remote agent."""
        try:
            return await self.client.get_task(task_id)
        except A2AClientError as e:
            logger.error(f"Failed to get task from {self.url}: {e}")
            raise
    
    async def close(self):
        """Close the client connection."""
        await self.client.close()


class HostAgent(BaseAgent):
    """Host agent that orchestrates multiple specialized agents."""
    
    def __init__(self, 
                 name: str = "DevGenius Host Agent",
                 description: str = "Orchestration agent for managing and coordinating specialized agents",
                 base_url: str = "http://localhost:8000",
                 remote_agents: Optional[List[Dict[str, Any]]] = None,
                 **kwargs):
        """Initialize host agent.
        
        Args:
            name: Agent name
            description: Agent description
            base_url: Base URL for the agent's A2A service
            remote_agents: List of dictionaries with remote agent configurations
            **kwargs: Additional arguments to pass to BaseAgent
        """
        self.remote_agents: Dict[str, RemoteAgentConnection] = {}
        self.agent_skills: Dict[str, List[str]] = {}  # Map agent URLs to skill IDs
        
        # Initialize base agent
        super().__init__(
            name=name,
            description=description,
            base_url=base_url,
            **kwargs
        )
        
        # Connect to remote agents if provided
        if remote_agents:
            asyncio.create_task(self.connect_to_agents(remote_agents))
    
    async def connect_to_agents(self, agent_configs: List[Dict[str, Any]]):
        """Connect to remote agents.
        
        Args:
            agent_configs: List of dictionaries with agent configurations
                Each dictionary should have at least a 'url' key.
        """
        for config in agent_configs:
            url = config.get('url')
            api_key = config.get('api_key')
            
            if not url:
                logger.warning("Agent configuration missing 'url'. Skipping.")
                continue
            
            try:
                await self.connect_to_agent(url, api_key)
            except Exception as e:
                logger.error(f"Failed to connect to agent at {url}: {e}")
    
    async def connect_to_agent(self, url: str, api_key: Optional[str] = None) -> RemoteAgentConnection:
        """Connect to a remote agent.
        
        Args:
            url: URL of the remote agent
            api_key: API key for authentication (optional)
            
        Returns:
            RemoteAgentConnection instance
        """
        if url in self.remote_agents:
            return self.remote_agents[url]
        
        agent_conn = RemoteAgentConnection(url, api_key)
        
        try:
            # Get agent card to verify connection
            card = await agent_conn.get_card()
            
            # Store connection
            self.remote_agents[url] = agent_conn
            
            # Store agent skills
            self.agent_skills[url] = [skill.id for skill in card.skills]
            
            # Register skills in the host agent
            for skill in card.skills:
                skill_with_source = AgentSkill(
                    id=f"{url}:{skill.id}",
                    name=skill.name,
                    description=f"[From {card.name}] {skill.description}",
                    tags=skill.tags,
                    examples=skill.examples,
                    inputModes=skill.inputModes or card.defaultInputModes,
                    outputModes=skill.outputModes or card.defaultOutputModes
                )
                self.register_skill(skill_with_source)
            
            logger.info(f"Connected to agent at {url} with {len(card.skills)} skills")
            return agent_conn
        except Exception as e:
            logger.error(f"Failed to connect to agent at {url}: {e}")
            raise
    
    async def disconnect_from_agent(self, url: str):
        """Disconnect from a remote agent.
        
        Args:
            url: URL of the remote agent
        """
        if url in self.remote_agents:
            try:
                await self.remote_agents[url].close()
            except Exception as e:
                logger.error(f"Error closing connection to {url}: {e}")
            
            # Remove from remote agents
            del self.remote_agents[url]
            
            # Remove skills
            if url in self.agent_skills:
                skill_ids = [f"{url}:{skill_id}" for skill_id in self.agent_skills[url]]
                self.skills = [skill for skill in self.skills if skill.id not in skill_ids]
                del self.agent_skills[url]
    
    def _extract_skill_info(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract skill info from message.
        
        Args:
            message: Message to analyze
            
        Returns:
            Tuple of (agent_url, skill_id) or (None, None) if no match
        """
        # Simple keyword matching - could be more sophisticated in a real implementation
        for url, skill_ids in self.agent_skills.items():
            for skill_id in skill_ids:
                if skill_id in message.lower():
                    return url, skill_id
        
        # No specific skill match, try to match by keywords
        if "code" in message.lower() or "convert" in message.lower():
            for url, skill_ids in self.agent_skills.items():
                if any("code" in skill_id for skill_id in skill_ids):
                    return url, "code-conversion"
        
        if "data" in message.lower() or "migration" in message.lower() or "database" in message.lower():
            for url, skill_ids in self.agent_skills.items():
                if any("data" in skill_id for skill_id in skill_ids):
                    return url, "data-migration"
        
        return None, None
    
    async def _process_message(self, message: str, params: TaskSendParams) -> str:
        """Process a message (route to appropriate agent).
        
        Args:
            message: Message to process
            params: Task parameters
            
        Returns:
            Response text
        """
        if not self.remote_agents:
            return "No remote agents connected. Please connect to some agents first."
        
        # Extract skill info from message
        agent_url, skill_id = self._extract_skill_info(message)
        
        if agent_url:
            agent_conn = self.remote_agents[agent_url]
            try:
                # Send task to remote agent
                card = await agent_conn.get_card()
                logger.info(f"Routing task to {card.name} for skill {skill_id}")
                
                task = await agent_conn.send_task(message, params.sessionId)
                
                # Wait for the task to complete or fail
                while task.status.state not in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
                    await asyncio.sleep(0.5)
                    task = await agent_conn.get_task(task.id)
                
                # Extract response from task
                if task.status.state == TaskState.COMPLETED:
                    if task.status.message:
                        return self._extract_message_text(task.status.message)
                    if task.artifacts:
                        texts = []
                        for artifact in task.artifacts:
                            for part in artifact.parts:
                                if hasattr(part, "text"):
                                    texts.append(part.text)
                        return "\n\n".join(texts)
                    return "Task completed successfully, but no response was provided."
                else:
                    return f"Task failed: {self._extract_message_text(task.status.message) if task.status.message else 'Unknown error'}"
            except Exception as e:
                logger.exception(f"Error processing task with remote agent: {e}")
                return f"Error processing task with remote agent: {str(e)}"
        else:
            # No specific agent identified, use a general response
            general_response = f"""As the DevGenius Host Agent, I can help route your request to specialized agents for:

1. Code Conversion (AWS to GCP)
2. Data Migration (DynamoDB to Firestore/Spanner, S3 to GCS, etc.)
3. Schema Translation
4. Architecture Design
5. Security Validation

Your request: "{message}"

To help you better, please specify which type of task you're looking to accomplish. For example:
- "Convert this AWS Lambda code to Google Cloud Function"
- "Migrate my DynamoDB schema to Firestore"
- "Design a GCP architecture equivalent to my AWS setup"
"""
            return general_response
    
    async def close(self):
        """Close all agent connections."""
        for url in list(self.remote_agents.keys()):
            await self.disconnect_from_agent(url) 