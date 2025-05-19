import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
import traceback
from typing import Dict, List, Optional, Union, Any, AsyncGenerator, Callable, Awaitable

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from .types import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCError,
    Task, TaskStatus, TaskState, Message, Artifact,
    TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
    TaskIdParams, TaskQueryParams, TaskSendParams,
    PushNotificationConfig, TaskPushNotificationConfig,
    AgentCard, TextPart
)

logger = logging.getLogger(__name__)

# JSON-RPC error codes
class ErrorCode:
    # Standard JSON-RPC errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # A2A specific errors
    TASK_NOT_FOUND = -32001
    TASK_NOT_CANCELABLE = -32002
    PUSH_NOTIFICATION_NOT_SUPPORTED = -32003
    UNSUPPORTED_OPERATION = -32004
    CONTENT_TYPE_NOT_SUPPORTED = -32005

class TaskManager:
    """Base class for managing task state in an A2A server."""
    
    async def create_task(self, params: TaskSendParams) -> Task:
        """Create a new task."""
        raise NotImplementedError()
    
    async def get_task(self, task_id: str, history_length: Optional[int] = None) -> Task:
        """Get task details by ID."""
        raise NotImplementedError()
    
    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a running task."""
        raise NotImplementedError()
    
    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> TaskPushNotificationConfig:
        """Set push notification configuration for a task."""
        raise NotImplementedError()
    
    async def get_push_notification(self, task_id: str) -> TaskPushNotificationConfig:
        """Get push notification configuration for a task."""
        raise NotImplementedError()
    
    async def get_task_stream(self, 
                             task_id: str, 
                             history_length: Optional[int] = None) -> AsyncGenerator[
                                 Union[TaskStatusUpdateEvent, TaskArtifactUpdateEvent], None]:
        """Get a stream of task updates."""
        raise NotImplementedError()

class InMemoryTaskManager(TaskManager):
    """In-memory implementation of TaskManager."""
    
    def __init__(self, 
                 task_processor: Optional[Callable[[TaskSendParams], Awaitable[Task]]] = None,
                 supports_streaming: bool = True,
                 supports_push_notifications: bool = False):
        """Initialize in-memory task manager."""
        self.tasks: Dict[str, Task] = {}
        self.push_notifications: Dict[str, PushNotificationConfig] = {}
        self.task_processor = task_processor
        self.supports_streaming = supports_streaming
        self.supports_push_notifications = supports_push_notifications
        self.task_streams: Dict[str, List[asyncio.Queue]] = {}
    
    def _get_iso_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
    
    async def create_task(self, params: TaskSendParams) -> Task:
        """Create a new task and process it."""
        task_id = params.id
        
        # Create initial task with SUBMITTED state
        task = Task(
            id=task_id,
            sessionId=params.sessionId,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                message=params.message,
                timestamp=self._get_iso_timestamp()
            ),
            artifacts=[],
            metadata=params.metadata or {}
        )
        
        self.tasks[task_id] = task
        
        # Set up streaming if supported
        if self.supports_streaming:
            self.task_streams[task_id] = []
        
        # Set up push notification if provided
        if params.pushNotification and self.supports_push_notifications:
            self.push_notifications[task_id] = params.pushNotification
        
        # Process the task if processor is provided
        if self.task_processor:
            # Update task to WORKING state
            task.status = TaskStatus(
                state=TaskState.WORKING,
                message=None,
                timestamp=self._get_iso_timestamp()
            )
            self._send_status_update(task)
            
            try:
                # Process the task
                updated_task = await self.task_processor(params)
                self.tasks[task_id] = updated_task
                self._send_status_update(updated_task)
            except Exception as e:
                # Update task to FAILED state
                error_message = Message(
                    role="agent",
                    parts=[TextPart(text=f"Task processing failed: {str(e)}")]
                )
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message=error_message,
                    timestamp=self._get_iso_timestamp()
                )
                self._send_status_update(task)
                logger.error(f"Task processing failed: {e}")
                logger.debug(traceback.format_exc())
        
        return self.tasks[task_id]
    
    async def get_task(self, task_id: str, history_length: Optional[int] = None) -> Task:
        """Get task details by ID."""
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # TODO: Implement history length filtering
        
        return task
    
    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a running task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # Check if task is in a final state
        if task.status.state in [TaskState.COMPLETED, TaskState.CANCELED, TaskState.FAILED]:
            raise ValueError("Task is already in a final state and cannot be canceled")
        
        # Update task to CANCELED state
        task.status = TaskStatus(
            state=TaskState.CANCELED,
            message=Message(
                role="agent",
                parts=[TextPart(text="Task was canceled")]
            ),
            timestamp=self._get_iso_timestamp()
        )
        
        self._send_status_update(task)
        
        return task
    
    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> TaskPushNotificationConfig:
        """Set push notification configuration for a task."""
        if not self.supports_push_notifications:
            raise ValueError("Push notifications are not supported")
        
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        self.push_notifications[task_id] = config
        
        return TaskPushNotificationConfig(
            id=task_id,
            pushNotification=config
        )
    
    async def get_push_notification(self, task_id: str) -> TaskPushNotificationConfig:
        """Get push notification configuration for a task."""
        if not self.supports_push_notifications:
            raise ValueError("Push notifications are not supported")
        
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        if task_id not in self.push_notifications:
            raise ValueError(f"No push notification configuration for task: {task_id}")
        
        return TaskPushNotificationConfig(
            id=task_id,
            pushNotification=self.push_notifications[task_id]
        )
    
    def _send_status_update(self, task: Task) -> None:
        """Send status update to all subscribers."""
        if not self.supports_streaming or task.id not in self.task_streams:
            return
        
        update = TaskStatusUpdateEvent(
            id=task.id,
            status=task.status,
            final=task.status.state in [TaskState.COMPLETED, TaskState.CANCELED, TaskState.FAILED]
        )
        
        for queue in self.task_streams[task.id]:
            queue.put_nowait(update)
    
    def send_artifact_update(self, task_id: str, artifact: Artifact, final: bool = False) -> None:
        """Send artifact update to all subscribers."""
        if not self.supports_streaming or task_id not in self.task_streams:
            return
        
        if task_id not in self.tasks:
            logger.warning(f"Attempting to send artifact update for unknown task: {task_id}")
            return
        
        task = self.tasks[task_id]
        
        # Add/update artifact in task
        existing_artifacts = task.artifacts or []
        
        # Check if we need to update an existing artifact or add a new one
        updated = False
        for i, existing in enumerate(existing_artifacts):
            if existing.index == artifact.index:
                if artifact.append:
                    # Append to existing parts
                    existing.parts.extend(artifact.parts)
                else:
                    # Replace existing artifact
                    existing_artifacts[i] = artifact
                updated = True
                break
        
        if not updated:
            existing_artifacts.append(artifact)
        
        task.artifacts = existing_artifacts
        
        # Send update to subscribers
        update = TaskArtifactUpdateEvent(
            id=task_id,
            artifact=artifact,
            final=final
        )
        
        for queue in self.task_streams[task_id]:
            queue.put_nowait(update)
    
    async def get_task_stream(self, 
                             task_id: str, 
                             history_length: Optional[int] = None) -> AsyncGenerator[
                                 Union[TaskStatusUpdateEvent, TaskArtifactUpdateEvent], None]:
        """Get a stream of task updates."""
        if not self.supports_streaming:
            raise ValueError("Streaming is not supported")
        
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        # Create a queue for this subscription
        queue = asyncio.Queue()
        
        if task_id not in self.task_streams:
            self.task_streams[task_id] = []
        
        self.task_streams[task_id].append(queue)
        
        try:
            # Send initial status update
            task = self.tasks[task_id]
            initial_update = TaskStatusUpdateEvent(
                id=task.id,
                status=task.status,
                final=task.status.state in [TaskState.COMPLETED, TaskState.CANCELED, TaskState.FAILED]
            )
            
            yield initial_update
            
            # Handle artifacts
            if task.artifacts:
                for artifact in task.artifacts:
                    yield TaskArtifactUpdateEvent(
                        id=task.id,
                        artifact=artifact,
                        final=False
                    )
            
            # If task is already in final state, we're done
            if initial_update.final:
                return
            
            # Otherwise, continue listening for updates
            while True:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=300)  # 5-minute timeout
                    yield update
                    
                    if update.final:
                        break
                except asyncio.TimeoutError:
                    # Timeout, send a heartbeat or break
                    break
        finally:
            # Clean up when subscription ends
            if task_id in self.task_streams:
                self.task_streams[task_id].remove(queue)

class A2AServer:
    """Starlette-based A2A protocol server."""
    
    def __init__(self, 
                 task_manager: TaskManager,
                 agent_card: AgentCard,
                 middleware: Optional[List[Middleware]] = None):
        """Initialize A2A server."""
        self.task_manager = task_manager
        self.agent_card = agent_card
        
        # Define routes
        routes = [
            Route("/.well-known/agent.json", self.get_agent_card),
            Route("/", self.handle_jsonrpc, methods=["POST"]),
        ]
        
        # Set up middleware
        if middleware is None:
            middleware = [
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["GET", "POST"],
                    allow_headers=["*"]
                )
            ]
        
        # Create Starlette application
        self.app = Starlette(
            routes=routes,
            middleware=middleware
        )
    
    async def get_agent_card(self, request: Request) -> JSONResponse:
        """Handle GET request for agent card."""
        return JSONResponse(self.agent_card.dict(exclude_none=True))
    
    async def handle_jsonrpc(self, request: Request) -> Union[JSONResponse, StreamingResponse]:
        """Handle JSON-RPC requests."""
        try:
            # Parse request JSON
            try:
                data = await request.json()
            except json.JSONDecodeError:
                return self._error_response(
                    None, ErrorCode.PARSE_ERROR, "Invalid JSON"
                )
            
            # Validate JSON-RPC request
            if not isinstance(data, dict) or data.get("jsonrpc") != "2.0" or "method" not in data:
                return self._error_response(
                    data.get("id"), ErrorCode.INVALID_REQUEST, "Invalid JSON-RPC request"
                )
            
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            # Check if this is a streaming request
            is_streaming = method == "tasks/sendSubscribe" or method == "tasks/resubscribe"
            
            # For streaming requests, check Accept header
            if is_streaming and request.headers.get("accept") != "text/event-stream":
                return self._error_response(
                    request_id, ErrorCode.CONTENT_TYPE_NOT_SUPPORTED,
                    "Streaming requests require Accept: text/event-stream header"
                )
            
            # Dispatch to appropriate handler based on method
            try:
                if method == "tasks/send":
                    result = await self._handle_send_task(params)
                    return self._success_response(request_id, result)
                elif method == "tasks/get":
                    result = await self._handle_get_task(params)
                    return self._success_response(request_id, result)
                elif method == "tasks/cancel":
                    result = await self._handle_cancel_task(params)
                    return self._success_response(request_id, result)
                elif method == "tasks/pushNotification/set":
                    result = await self._handle_set_push_notification(params)
                    return self._success_response(request_id, result)
                elif method == "tasks/pushNotification/get":
                    result = await self._handle_get_push_notification(params)
                    return self._success_response(request_id, result)
                elif method == "tasks/sendSubscribe":
                    return self._handle_send_subscribe(request_id, params)
                elif method == "tasks/resubscribe":
                    return self._handle_resubscribe(request_id, params)
                else:
                    return self._error_response(
                        request_id, ErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}"
                    )
            except ValueError as e:
                # Map specific error messages to specific error codes
                error_message = str(e)
                if "Task not found" in error_message:
                    return self._error_response(
                        request_id, ErrorCode.TASK_NOT_FOUND, error_message
                    )
                elif "Task is already in a final state" in error_message:
                    return self._error_response(
                        request_id, ErrorCode.TASK_NOT_CANCELABLE, error_message
                    )
                elif "Push notifications are not supported" in error_message:
                    return self._error_response(
                        request_id, ErrorCode.PUSH_NOTIFICATION_NOT_SUPPORTED, error_message
                    )
                elif "Streaming is not supported" in error_message:
                    return self._error_response(
                        request_id, ErrorCode.UNSUPPORTED_OPERATION, error_message
                    )
                else:
                    return self._error_response(
                        request_id, ErrorCode.INVALID_PARAMS, error_message
                    )
        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            logger.debug(traceback.format_exc())
            return self._error_response(
                getattr(request, "id", None), ErrorCode.INTERNAL_ERROR, f"Internal error: {str(e)}"
            )
    
    def _success_response(self, request_id: Optional[Union[str, int]], result: Any) -> JSONResponse:
        """Create a successful JSON-RPC response."""
        if isinstance(result, BaseModel):
            result = result.dict(exclude_none=True)
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        })
    
    def _error_response(self, 
                        request_id: Optional[Union[str, int]], 
                        code: int, 
                        message: str, 
                        data: Optional[Any] = None) -> JSONResponse:
        """Create an error JSON-RPC response."""
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message,
                "data": data
            },
            "id": request_id
        })
    
    async def _handle_send_task(self, params: Dict[str, Any]) -> Task:
        """Handle tasks/send method."""
        try:
            send_params = TaskSendParams(**params)
            return await self.task_manager.create_task(send_params)
        except Exception as e:
            raise ValueError(f"Invalid params: {str(e)}")
    
    async def _handle_get_task(self, params: Dict[str, Any]) -> Task:
        """Handle tasks/get method."""
        try:
            query_params = TaskQueryParams(**params)
            return await self.task_manager.get_task(query_params.id, query_params.historyLength)
        except Exception as e:
            raise ValueError(f"Invalid params: {str(e)}")
    
    async def _handle_cancel_task(self, params: Dict[str, Any]) -> Task:
        """Handle tasks/cancel method."""
        try:
            id_params = TaskIdParams(**params)
            return await self.task_manager.cancel_task(id_params.id)
        except Exception as e:
            raise ValueError(f"Invalid params: {str(e)}")
    
    async def _handle_set_push_notification(self, params: Dict[str, Any]) -> TaskPushNotificationConfig:
        """Handle tasks/pushNotification/set method."""
        try:
            config_params = TaskPushNotificationConfig(**params)
            return await self.task_manager.set_push_notification(
                config_params.id, config_params.pushNotification
            )
        except Exception as e:
            raise ValueError(f"Invalid params: {str(e)}")
    
    async def _handle_get_push_notification(self, params: Dict[str, Any]) -> TaskPushNotificationConfig:
        """Handle tasks/pushNotification/get method."""
        try:
            id_params = TaskIdParams(**params)
            return await self.task_manager.get_push_notification(id_params.id)
        except Exception as e:
            raise ValueError(f"Invalid params: {str(e)}")
    
    def _handle_send_subscribe(self, request_id: Optional[Union[str, int]], params: Dict[str, Any]) -> StreamingResponse:
        """Handle tasks/sendSubscribe method."""
        try:
            send_params = TaskSendParams(**params)
            
            async def sse_stream():
                try:
                    # First, create the task
                    await self.task_manager.create_task(send_params)
                    
                    # Then subscribe to updates
                    async for event in self.task_manager.get_task_stream(send_params.id, send_params.historyLength):
                        event_data = event.dict(exclude_none=True)
                        yield f"data: {json.dumps(event_data)}\n\n"
                except Exception as e:
                    logger.error(f"Error in streaming task updates: {e}")
                    error_event = {
                        "error": {
                            "code": ErrorCode.INTERNAL_ERROR,
                            "message": f"Streaming error: {str(e)}"
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
            
            return StreamingResponse(
                sse_stream(),
                media_type="text/event-stream"
            )
        except Exception as e:
            raise ValueError(f"Invalid params: {str(e)}")
    
    def _handle_resubscribe(self, request_id: Optional[Union[str, int]], params: Dict[str, Any]) -> StreamingResponse:
        """Handle tasks/resubscribe method."""
        try:
            query_params = TaskQueryParams(**params)
            
            async def sse_stream():
                try:
                    async for event in self.task_manager.get_task_stream(query_params.id, query_params.historyLength):
                        event_data = event.dict(exclude_none=True)
                        yield f"data: {json.dumps(event_data)}\n\n"
                except Exception as e:
                    logger.error(f"Error in streaming task updates: {e}")
                    error_event = {
                        "error": {
                            "code": ErrorCode.INTERNAL_ERROR,
                            "message": f"Streaming error: {str(e)}"
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
            
            return StreamingResponse(
                sse_stream(),
                media_type="text/event-stream"
            )
        except Exception as e:
            raise ValueError(f"Invalid params: {str(e)}") 