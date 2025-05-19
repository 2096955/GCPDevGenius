from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field

# Core JSON-RPC Structures
class JSONRPCMessage(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None

class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class JSONRPCResponse(JSONRPCMessage):
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None

class JSONRPCRequest(JSONRPCMessage):
    method: str
    params: Optional[Union[Dict, List]] = None

# A2A Protocol Enums
class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    UNKNOWN = "unknown"

# A2A Data Objects
class FileContent(BaseModel):
    name: Optional[str] = None
    mimeType: Optional[str] = None
    bytes: Optional[str] = None
    uri: Optional[str] = None

class Part(BaseModel):
    type: str
    metadata: Optional[Dict[str, Any]] = None

class TextPart(Part):
    type: str = "text"
    text: str

class FilePart(Part):
    type: str = "file"
    file: FileContent

class DataPart(Part):
    type: str = "data"
    data: Dict[str, Any]

class Message(BaseModel):
    role: str  # "user" | "agent"
    parts: List[Union[TextPart, FilePart, DataPart]]
    metadata: Optional[Dict[str, Any]] = None

class TaskStatus(BaseModel):
    state: TaskState
    message: Optional[Message] = None
    timestamp: str

class Artifact(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Union[TextPart, FilePart, DataPart]]
    index: int = 0
    append: Optional[bool] = None
    lastChunk: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class Task(BaseModel):
    id: str
    sessionId: Optional[str] = None
    status: TaskStatus
    artifacts: Optional[List[Artifact]] = None
    history: Optional[List[Message]] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = False

class AgentProvider(BaseModel):
    name: str
    url: Optional[str] = None

class AgentAuthentication(BaseModel):
    type: str
    url: Optional[str] = None
    scheme: Optional[str] = None
    aud: Optional[str] = None

class AgentSkill(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    inputModes: Optional[List[str]] = None
    outputModes: Optional[List[str]] = None

class AgentCard(BaseModel):
    name: str
    description: Optional[str] = None
    url: str
    provider: Optional[AgentProvider] = None
    version: str
    documentationUrl: Optional[str] = None
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    authentication: Optional[AgentAuthentication] = None
    defaultInputModes: List[str] = ["text"]
    defaultOutputModes: List[str] = ["text"]
    skills: List[AgentSkill] = []

class PushNotificationConfig(BaseModel):
    url: str
    token: Optional[str] = None
    authentication: Optional[Any] = None

class TaskPushNotificationConfig(BaseModel):
    id: str
    pushNotification: PushNotificationConfig

# Event Types for Streaming
class TaskStatusUpdateEvent(BaseModel):
    id: str
    status: TaskStatus
    final: bool = False
    metadata: Optional[Dict[str, Any]] = None

class TaskArtifactUpdateEvent(BaseModel):
    id: str
    artifact: Artifact
    final: bool = False
    metadata: Optional[Dict[str, Any]] = None

# Request Parameters
class TaskIdParams(BaseModel):
    id: str

class TaskQueryParams(TaskIdParams):
    historyLength: Optional[int] = None

class TaskSendParams(TaskQueryParams):
    sessionId: Optional[str] = None
    message: Message
    pushNotification: Optional[PushNotificationConfig] = None
    metadata: Optional[Dict[str, Any]] = None 