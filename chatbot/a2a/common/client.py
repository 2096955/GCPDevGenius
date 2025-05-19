import json
import uuid
import httpx
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, AsyncGenerator, Tuple
import urllib.parse

from .types import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCError,
    Task, TaskStatus, TaskState, Message, Artifact,
    TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
    TaskIdParams, TaskQueryParams, TaskSendParams,
    PushNotificationConfig, TaskPushNotificationConfig,
    AgentCard, TextPart
)

logger = logging.getLogger(__name__)

class A2AClientError(Exception):
    """Base exception for A2A client errors."""
    pass

class A2ACardResolver:
    """Resolver for fetching and caching Agent Cards."""
    
    def __init__(self):
        self.cache: Dict[str, AgentCard] = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def get_agent_card(self, agent_url: str) -> AgentCard:
        """Fetch agent card from the given URL."""
        if agent_url in self.cache:
            return self.cache[agent_url]
        
        # Normalize URL
        base_url = agent_url.rstrip('/')
        well_known_url = f"{base_url}/.well-known/agent.json"
        
        try:
            response = await self.http_client.get(well_known_url)
            response.raise_for_status()
            agent_data = response.json()
            card = AgentCard(**agent_data)
            self.cache[agent_url] = card
            return card
        except Exception as e:
            raise A2AClientError(f"Failed to fetch agent card from {well_known_url}: {e}")

class A2AClient:
    """Client for making A2A protocol requests to agents."""
    
    def __init__(self, agent_url: str, api_key: Optional[str] = None):
        """Initialize an A2A client for a specific agent."""
        self.agent_url = agent_url.rstrip('/')
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.card_resolver = A2ACardResolver()
        self.agent_card: Optional[AgentCard] = None
    
    async def _ensure_agent_card(self):
        """Ensure we have the agent card loaded."""
        if self.agent_card is None:
            self.agent_card = await self.card_resolver.get_agent_card(self.agent_url)
    
    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for requests."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _build_jsonrpc_request(self, method: str, params: Any) -> Dict[str, Any]:
        """Build a JSON-RPC request object."""
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid.uuid4())
        }
    
    async def _make_request(self, method: str, params: Any) -> Any:
        """Make a JSON-RPC request to the agent."""
        await self._ensure_agent_card()
        request_data = self._build_jsonrpc_request(method, params)
        headers = self._build_headers()
        
        try:
            response = await self.http_client.post(
                f"{self.agent_url}",
                json=request_data,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Check for JSON-RPC error
            if "error" in result:
                error = JSONRPCError(**result["error"])
                raise A2AClientError(f"JSON-RPC error: {error.message} (code: {error.code})")
            
            return result.get("result")
        except httpx.HTTPStatusError as e:
            raise A2AClientError(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise A2AClientError(f"Request failed: {str(e)}")
    
    async def send_task(self, 
                         message: Union[str, Message], 
                         session_id: Optional[str] = None,
                         push_notification: Optional[PushNotificationConfig] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Task:
        """Send a task to the agent."""
        # Convert string to Message if needed
        if isinstance(message, str):
            message = Message(
                role="user",
                parts=[TextPart(text=message)]
            )
        
        params = TaskSendParams(
            id=str(uuid.uuid4()),
            sessionId=session_id,
            message=message,
            pushNotification=push_notification,
            metadata=metadata
        )
        
        result = await self._make_request("tasks/send", params.dict(exclude_none=True))
        return Task(**result)
    
    async def get_task(self, task_id: str, history_length: Optional[int] = None) -> Task:
        """Get task details by ID."""
        params = TaskQueryParams(
            id=task_id,
            historyLength=history_length
        )
        
        result = await self._make_request("tasks/get", params.dict(exclude_none=True))
        return Task(**result)
    
    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a running task."""
        params = TaskIdParams(id=task_id)
        
        result = await self._make_request("tasks/cancel", params.dict())
        return Task(**result)
    
    async def set_push_notification(self, 
                                    task_id: str, 
                                    config: PushNotificationConfig) -> TaskPushNotificationConfig:
        """Set push notification configuration for a task."""
        params = TaskPushNotificationConfig(
            id=task_id,
            pushNotification=config
        )
        
        result = await self._make_request("tasks/pushNotification/set", params.dict())
        return TaskPushNotificationConfig(**result)
    
    async def get_push_notification(self, task_id: str) -> TaskPushNotificationConfig:
        """Get push notification configuration for a task."""
        params = TaskIdParams(id=task_id)
        
        result = await self._make_request("tasks/pushNotification/get", params.dict())
        return TaskPushNotificationConfig(**result)
    
    async def send_subscribe(self, 
                             message: Union[str, Message], 
                             session_id: Optional[str] = None,
                             push_notification: Optional[PushNotificationConfig] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> AsyncGenerator[
                                 Union[TaskStatusUpdateEvent, TaskArtifactUpdateEvent], None]:
        """Send a task and subscribe to events via SSE."""
        # Convert string to Message if needed
        if isinstance(message, str):
            message = Message(
                role="user",
                parts=[TextPart(text=message)]
            )
        
        params = TaskSendParams(
            id=str(uuid.uuid4()),
            sessionId=session_id,
            message=message,
            pushNotification=push_notification,
            metadata=metadata
        )
        
        await self._ensure_agent_card()
        
        # Check if streaming is supported
        if not self.agent_card.capabilities.streaming:
            raise A2AClientError("Agent does not support streaming")
        
        request_data = self._build_jsonrpc_request("tasks/sendSubscribe", params.dict(exclude_none=True))
        headers = self._build_headers()
        headers["Accept"] = "text/event-stream"
        
        try:
            async with self.http_client.stream(
                "POST",
                f"{self.agent_url}",
                json=request_data,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                # Parse SSE events
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    while "\n\n" in buffer:
                        event, buffer = buffer.split("\n\n", 1)
                        event_lines = event.strip().split("\n")
                        
                        event_data = None
                        for line in event_lines:
                            if line.startswith("data: "):
                                event_data = line[6:]
                        
                        if event_data:
                            try:
                                event_json = json.loads(event_data)
                                
                                if "status" in event_json:
                                    yield TaskStatusUpdateEvent(**event_json)
                                elif "artifact" in event_json:
                                    yield TaskArtifactUpdateEvent(**event_json)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE event: {event_data}")
        except httpx.HTTPStatusError as e:
            raise A2AClientError(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise A2AClientError(f"Streaming request failed: {str(e)}")
    
    async def resubscribe(self, 
                          task_id: str, 
                          history_length: Optional[int] = None) -> AsyncGenerator[
                              Union[TaskStatusUpdateEvent, TaskArtifactUpdateEvent], None]:
        """Resubscribe to task events after connection interruption."""
        await self._ensure_agent_card()
        
        # Check if streaming is supported
        if not self.agent_card.capabilities.streaming:
            raise A2AClientError("Agent does not support streaming")
        
        params = TaskQueryParams(
            id=task_id,
            historyLength=history_length
        )
        
        request_data = self._build_jsonrpc_request("tasks/resubscribe", params.dict(exclude_none=True))
        headers = self._build_headers()
        headers["Accept"] = "text/event-stream"
        
        try:
            async with self.http_client.stream(
                "POST",
                f"{self.agent_url}",
                json=request_data,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                # Parse SSE events
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    while "\n\n" in buffer:
                        event, buffer = buffer.split("\n\n", 1)
                        event_lines = event.strip().split("\n")
                        
                        event_data = None
                        for line in event_lines:
                            if line.startswith("data: "):
                                event_data = line[6:]
                        
                        if event_data:
                            try:
                                event_json = json.loads(event_data)
                                
                                if "status" in event_json:
                                    yield TaskStatusUpdateEvent(**event_json)
                                elif "artifact" in event_json:
                                    yield TaskArtifactUpdateEvent(**event_json)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE event: {event_data}")
        except httpx.HTTPStatusError as e:
            raise A2AClientError(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise A2AClientError(f"Streaming request failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
        await self.card_resolver.http_client.aclose() 