"""
Webhook Agent Processor - processes messages with request-time filtering and orchestration
"""

import logging

from app.events.orchestration.publisher import OrchestrationEventPublisher
from app.events.orchestration.task_registry import TaskRegistry
from app.events.orchestration.task_state import TaskState, TaskStatus
from app.events.webhooks.publisher import WebhookEventPublisher


logger = logging.getLogger(__name__)


class WebhookAgentProcessor:
    """Processes webhook messages using request-time agent selection with orchestration support"""

    def __init__(
        self,
        agent_cache,
        event_publisher: WebhookEventPublisher,
        task_registry: TaskRegistry | None = None,
        orchestration_publisher: OrchestrationEventPublisher | None = None,
    ):
        self.agent_cache = agent_cache
        self.event_publisher = event_publisher
        self.task_registry = task_registry or TaskRegistry()
        self.orchestration_publisher = orchestration_publisher

    def is_valid_for_webhook(self, agent_id: str) -> bool:
        """Check if agent is valid for webhook processing"""
        # Find the DB agent to check webhook fields
        db_agents = self.agent_cache.get_loaded_db_agents()

        for db_agent in db_agents:
            if str(db_agent.id) == agent_id:
                return bool(db_agent.is_active)

        return False

    async def process_message(self, agent_id: str, message: str, chat_id: str) -> str | None:
        """
        Process a message with the specified agent

        Args:
            agent_id: Agent UUID as string
            message: User message text
            chat_id: WhatsApp chat ID

        Returns:
            Agent response or None if processing failed
        """
        try:
            # Validate agent is suitable for webhook processing
            if not self.is_valid_for_webhook(agent_id):
                logger.error(f"Agent {agent_id} is not enabled for webhook processing")
                return None

            # Find the agent by ID
            target_agent = self.agent_cache.find_agent_by_id(agent_id)
            if not target_agent:
                logger.error(f"Agent not found: {agent_id}")
                return None

            logger.info(f"Processing message with agent: {target_agent.name}")
            logger.debug(f"Message: {message}")
            logger.debug(f"Chat ID: {chat_id}")

            # Process the message with the agent
            response = await target_agent.arun(message)

            if response and hasattr(response, "content"):
                response_text = str(response.content)
                logger.info(
                    f"Agent {target_agent.name} responded successfully. "
                    f"Response length: {len(response_text)}"
                )
                logger.debug(f"Response: {response_text}")
                return response_text
            logger.warning(f"Agent {target_agent.name} returned empty or invalid response")
            return None

        except Exception as e:
            logger.error(f"Error processing message with agent {agent_id}: {e}")
            return None

    async def create_processing_task(
        self, agent_id: str, message: str, chat_id: str, session_id: str
    ) -> TaskState:
        """Create an orchestrated task for message processing"""
        task_data = {
            "agent_id": agent_id,
            "message": message,
            "chat_id": chat_id,
            "session_id": session_id,
            "task_type": "webhook_message_processing",
        }

        task = self.task_registry.create_task(
            agent_id=agent_id, task_type="webhook_message_processing", data=task_data
        )

        # Publish orchestration event if publisher available
        if self.orchestration_publisher:
            await self.orchestration_publisher.task_created(task.task_id, task_data)

        logger.info(f"Created orchestration task {task.task_id} for agent {agent_id}")
        return task

    async def process_orchestrated_message(self, task_id: str) -> str | None:
        """Process a message using orchestration task coordination"""
        task = self.task_registry.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return None

        if task.status != TaskStatus.READY:
            logger.warning(f"Task {task_id} is not ready (status: {task.status})")
            return None

        # Mark task as in progress
        self.task_registry.update_task_status(task_id, TaskStatus.IN_PROGRESS)

        try:
            # Extract task data
            agent_id = task.data["agent_id"]
            message = task.data["message"]
            chat_id = task.data["chat_id"]

            # Process message using existing logic
            response = await self.process_message(agent_id, message, chat_id)

            if response:
                # Mark task as completed with result
                self.task_registry.update_task_status(
                    task_id, TaskStatus.COMPLETED, result={"response": response}
                )

                # Publish orchestration completion event
                if self.orchestration_publisher:
                    await self.orchestration_publisher.task_completed(
                        task_id, {"response": response, "agent_id": agent_id}
                    )

                logger.info(f"Orchestrated task {task_id} completed successfully")
                return response
            # Mark task as failed
            self.task_registry.update_task_status(
                task_id, TaskStatus.FAILED, error="Agent returned empty response"
            )

            # Publish orchestration failure event
            if self.orchestration_publisher:
                await self.orchestration_publisher.task_failed(
                    task_id, {"error": "Agent returned empty response", "agent_id": agent_id}
                )

            return None

        except Exception as e:
            error_msg = f"Error in orchestrated processing: {e}"
            logger.error(f"Task {task_id} failed: {error_msg}")

            # Mark task as failed
            self.task_registry.update_task_status(task_id, TaskStatus.FAILED, error=error_msg)

            # Publish orchestration failure event
            if self.orchestration_publisher:
                await self.orchestration_publisher.task_failed(
                    task_id, {"error": error_msg, "agent_id": task.data.get("agent_id")}
                )

            return None

    def get_task_status(self, task_id: str) -> TaskStatus | None:
        """Get the status of an orchestration task"""
        task = self.task_registry.get_task(task_id)
        return task.status if task else None

    def get_ready_tasks(self) -> list[TaskState]:
        """Get all ready tasks for processing"""
        return self.task_registry.get_ready_tasks()
