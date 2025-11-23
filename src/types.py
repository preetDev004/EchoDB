"""Type definitions for EchoDB application."""

from typing import TypedDict, Literal, Any


class UserMessage(TypedDict):
    """User message in chat history."""
    role: Literal["user"]
    content: str


class AssistantMessage(TypedDict):
    """Assistant message in chat history."""
    role: Literal["assistant"]
    content: str


class ToolLog(TypedDict):
    """Tool execution log."""
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: str


class ContentEvent(TypedDict):
    """Streaming content event from agent."""
    type: Literal["content"]
    content: str


class ToolStartEvent(TypedDict):
    """Tool execution start event."""
    type: Literal["tool_start"]
    tool_name: str
    tool_input: dict[str, Any]


class ToolEndEvent(TypedDict):
    """Tool execution end event."""
    type: Literal["tool_end"]
    tool_name: str
    tool_output: str


# Union type for all possible events
AgentEvent = ContentEvent | ToolStartEvent | ToolEndEvent

# Union type for chat messages
ChatMessage = UserMessage | AssistantMessage
