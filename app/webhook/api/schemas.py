"""Webhook API schemas - consolidated request/response models"""

from pydantic import BaseModel, ConfigDict, Field


class WebhookPayload(BaseModel):
    """WhatsApp message payload from WAHA webhook"""

    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(..., alias="from", title="Chat ID", description="Chat ID of the sender")
    from_me: bool = Field(
        default=False,
        alias="fromMe",
        title="From Me",
        description="Whether message was sent by bot",
    )
    body: str = Field(..., title="Message Body", description="Message text content")
    type: str = Field(default="chat", title="Message Type", description="Message type")
    timestamp: int | None = Field(None, title="Timestamp", description="Message timestamp")
    id: str | None = Field(None, title="Message ID", description="Message ID")


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
    metadata: WebhookMetadata | None = Field(
        default_factory=WebhookMetadata, title="Metadata", description="Agent metadata"
    )

    def get_chat_id(self) -> str:
        """Get the chat ID from payload"""
        return self.payload.from_

    def get_message_body(self) -> str:
        """Get the message text content"""
        return self.payload.body

    def get_agent_id(self) -> str | None:
        """Get the agent ID from metadata"""
        return self.metadata.agent_id if self.metadata else None

    def is_from_bot(self) -> bool:
        """Check if message was sent by the bot"""
        return self.payload.from_me

    def is_message_event(self) -> bool:
        """Check if this is a message event"""
        return self.event == "message"
