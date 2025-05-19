import asyncio
import os
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
from datetime import datetime, timezone

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from ..common import (
    A2AServer, TaskManager, InMemoryTaskManager, 
    AgentCard, AgentCapabilities, AgentProvider, AgentAuthentication, AgentSkill,
    Task, TaskStatus, TaskState, Message, Artifact, TextPart, TaskSendParams,
    JWTUtils, create_jwks_endpoint
)

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for implementing A2A-compatible agents."""
    
    def __init__(self, 
                 name: str,
                 description: Optional[str] = None,
                 base_url: str = "http://localhost:8000",
                 agent_id: Optional[str] = None,
                 version: str = "1.0.0",
                 supports_streaming: bool = True,
                 supports_push_notifications: bool = False,
                 provider_name: Optional[str] = None,
                 provider_url: Optional[str] = None,
                 documentation_url: Optional[str] = None,
                 skills: Optional[List[AgentSkill]] = None,
                 input_modes: Optional[List[str]] = None,
                 output_modes: Optional[List[str]] = None,
                 jwks_path: Optional[str] = None,
                 host: str = "0.0.0.0",
                 port: int = 8000,
                 log_level: str = "info",
                 cors_origins: Optional[List[str]] = None):
        """Initialize base agent.
        
        Args:
            name: Agent name
            description: Agent description
            base_url: Base URL for the agent's A2A service
            agent_id: Unique ID for the agent (default: generated UUID)
            version: Agent version
            supports_streaming: Whether the agent supports streaming
            supports_push_notifications: Whether the agent supports push notifications
            provider_name: Provider name (organization)
            provider_url: Provider URL
            documentation_url: Documentation URL
            skills: List of agent skills
            input_modes: Supported input modes (default: ["text"])
            output_modes: Supported output modes (default: ["text"])
            jwks_path: Path to store JWKS file
            host: Host to listen on
            port: Port to listen on
            log_level: Logging level
            cors_origins: CORS origins (default: ["*"])
        """
        self.name = name
        self.description = description
        self.base_url = base_url
        self.agent_id = agent_id or str(uuid.uuid4())
        self.version = version
        self.supports_streaming = supports_streaming
        self.supports_push_notifications = supports_push_notifications
        self.provider_name = provider_name
        self.provider_url = provider_url
        self.documentation_url = documentation_url
        self.skills = skills or []
        self.input_modes = input_modes or ["text"]
        self.output_modes = output_modes or ["text"]
        self.jwks_path = jwks_path
        self.host = host
        self.port = port
        self.log_level = log_level
        self.cors_origins = cors_origins or ["*"]
        
        # Set up JWT utils
        self.jwt_utils = JWTUtils(
            jwks_path=self.jwks_path,
            issuer=self.base_url
        )
        
        # Create agent card
        self.agent_card = self._create_agent_card()
        
        # Set up task manager
        self.task_manager = InMemoryTaskManager(
            task_processor=self.process_task,
            supports_streaming=self.supports_streaming,
            supports_push_notifications=self.supports_push_notifications
        )
        
        # Set up A2A server
        self.server = self._create_server()
    
    def _create_agent_card(self) -> AgentCard:
        """Create agent card."""
        provider = None
        if self.provider_name:
            provider = AgentProvider(
                name=self.provider_name,
                url=self.provider_url
            )
            
        capabilities = AgentCapabilities(
            streaming=self.supports_streaming,
            pushNotifications=self.supports_push_notifications,
            stateTransitionHistory=False  # Not implemented yet
        )
        
        authentication = None
        if self.supports_push_notifications:
            authentication = AgentAuthentication(
                type="jwt",
                url=f"{self.base_url}/.well-known/jwks.json",
                scheme="Bearer"
            )
        
        card = AgentCard(
            name=self.name,
            description=self.description,
            url=self.base_url,
            provider=provider,
            version=self.version,
            documentationUrl=self.documentation_url,
            capabilities=capabilities,
            authentication=authentication,
            defaultInputModes=self.input_modes,
            defaultOutputModes=self.output_modes,
            skills=self.skills
        )
        
        return card
    
    def _create_server(self) -> A2AServer:
        """Create A2A server."""
        # Add additional routes
        additional_routes = []
        
        # Add JWKS endpoint if push notifications are supported
        if self.supports_push_notifications:
            additional_routes.append(
                Route("/.well-known/jwks.json", create_jwks_endpoint(self.jwt_utils))
            )
        
        # Add custom middleware
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_methods=["GET", "POST"],
                allow_headers=["*"]
            )
        ]
        
        # Create server
        server = A2AServer(
            task_manager=self.task_manager,
            agent_card=self.agent_card,
            middleware=middleware
        )
        
        # Add additional routes
        if additional_routes:
            server.app.routes.extend(additional_routes)
        
        return server
    
    async def process_task(self, params: TaskSendParams) -> Task:
        """Process a task (to be implemented by subclasses)."""
        # Create basic task
        task = Task(
            id=params.id,
            sessionId=params.sessionId,
            status=TaskStatus(
                state=TaskState.WORKING,
                message=None,
                timestamp=datetime.now(timezone.utc).isoformat()
            ),
            artifacts=[],
            metadata=params.metadata or {}
        )
        
        # Process message based on content
        message_text = self._extract_message_text(params.message)
        
        try:
            # Process the message
            response_text = await self._process_message(message_text, params)
            
            # Create response message
            response_message = Message(
                role="agent",
                parts=[TextPart(text=response_text)]
            )
            
            # Update task status
            task.status = TaskStatus(
                state=TaskState.COMPLETED,
                message=response_message,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Add response as artifact
            task.artifacts = [
                Artifact(
                    name="response",
                    description="Task response",
                    parts=[TextPart(text=response_text)]
                )
            ]
        except Exception as e:
            logger.exception(f"Error processing task: {e}")
            
            # Create error message
            error_message = Message(
                role="agent",
                parts=[TextPart(text=f"Error: {str(e)}")]
            )
            
            # Update task status
            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=error_message,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        return task
    
    def _extract_message_text(self, message: Message) -> str:
        """Extract text from message parts."""
        texts = []
        for part in message.parts:
            if hasattr(part, "text"):
                texts.append(part.text)
        return " ".join(texts)
    
    async def _process_message(self, message: str, params: TaskSendParams) -> str:
        """Process a message (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _process_message method")
    
    def run(self):
        """Run the agent server."""
        uvicorn.run(
            self.server.app,
            host=self.host,
            port=self.port,
            log_level=self.log_level
        )
    
    async def add_artifact(self, task_id: str, artifact: Artifact, final: bool = False):
        """Add artifact to a task (for streaming)."""
        self.task_manager.send_artifact_update(task_id, artifact, final)
    
    def register_skill(self, skill: AgentSkill):
        """Register a new skill."""
        self.skills.append(skill)
        self.agent_card.skills.append(skill)
    
    def add_skill(self, 
                 id: str, 
                 name: str, 
                 description: Optional[str] = None,
                 tags: Optional[List[str]] = None,
                 examples: Optional[List[str]] = None,
                 input_modes: Optional[List[str]] = None,
                 output_modes: Optional[List[str]] = None):
        """Add a new skill."""
        skill = AgentSkill(
            id=id,
            name=name,
            description=description,
            tags=tags,
            examples=examples,
            inputModes=input_modes,
            outputModes=output_modes
        )
        self.register_skill(skill) 