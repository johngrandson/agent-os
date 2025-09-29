"""Webhook API schemas - consolidated request/response models"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MessagePayload(BaseModel):
    """WhatsApp message payload from WAHA webhook"""

    model_config = ConfigDict(populate_by_name=True)

    chat_id: str = Field(..., alias="from", title="Chat ID", description="Chat ID of the sender")
    sent_by_bot: bool = Field(
        default=False,
        title="Sent By Bot",
        description="Whether message was sent by bot",
    )
    body: str = Field(..., title="Message Body", description="Message text content")
    type: str = Field(default="chat", title="Message Type", description="Message type")
    timestamp: int | None = Field(None, title="Timestamp", description="Message timestamp")
    id: str | None = Field(None, title="Message ID", description="Message ID")


class SessionStatusPayload(BaseModel):
    """Session status payload from WAHA webhook"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., title="Session Name", description="Session name")
    status: str = Field(..., title="Status", description="Current session status")
    statuses: list[dict[str, Any]] = Field(
        default_factory=list, title="Status History", description="Status change history"
    )


# Union type for different payload types
WebhookPayload = MessagePayload | SessionStatusPayload


class WebhookMetadata(BaseModel):
    """Webhook metadata containing agent configuration"""

    model_config = ConfigDict(populate_by_name=True)

    agent_id: str | None = Field(
        None, alias="agent.id", title="Agent ID", description="Agent ID for processing"
    )


class WebhookData(BaseModel):
    """Complete webhook data structure from WAHA"""

    model_config = ConfigDict(populate_by_name=True)

    event: str = Field(..., title="Event Type", description="Event type (e.g., 'message')")
    payload: WebhookPayload = Field(..., title="Payload", description="Message payload data")
    metadata: WebhookMetadata | None = Field(None, title="Metadata", description="Agent metadata")

    def get_chat_id(self) -> str | None:
        """Get the chat ID from payload if it's a message event"""
        if isinstance(self.payload, MessagePayload):
            return self.payload.chat_id
        return None

    def get_message_body(self) -> str | None:
        """Get the message text content if it's a message event"""
        if isinstance(self.payload, MessagePayload):
            return self.payload.body
        return None

    def get_agent_id(self) -> str | None:
        """Get the agent ID from metadata"""
        return self.metadata.agent_id if self.metadata else None

    def is_from_bot(self) -> bool:
        """Check if message was sent by the bot"""
        if isinstance(self.payload, MessagePayload):
            return self.payload.sent_by_bot
        return False

    def is_message_event(self) -> bool:
        """Check if this is a message event"""
        return self.event == "message" and isinstance(self.payload, MessagePayload)

    def is_session_status_event(self) -> bool:
        """Check if this is a session status event"""
        return self.event == "session.status" and isinstance(self.payload, SessionStatusPayload)
