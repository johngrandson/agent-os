"""WAHA WhatsApp API client for sending messages"""

import httpx
from core.config import Config
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class WahaClient:
    """Simple WAHA client for sending WhatsApp messages"""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_url = config.WAHA_API_URL
        self.session_name = config.WAHA_SESSION_NAME
        self.api_key = config.WAHA_API_KEY

    async def send_text_message(self, chat_id: str, text: str) -> bool:
        """
        Send a text message to WhatsApp chat via WAHA API

        Args:
            chat_id: WhatsApp chat ID (e.g., "558381055060@c.us")
            text: Message text to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/sendText"

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "session": self.session_name,
                "chatId": chat_id,
                "text": text,
            }

            logger.info(f"Sending WhatsApp message to {chat_id}")
            logger.debug(f"Message content: {text}")

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in (200, 201):
                    logger.info(f"Message sent successfully to {chat_id}")
                    return True
                else:
                    logger.error(
                        f"Failed to send message to {chat_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {chat_id}: {e}")
            return False

    async def send_seen_status(self, chat_id: str) -> bool:
        """Mark message as seen to mimic human behavior"""
        try:
            url = f"{self.base_url}/sendSeen"

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "session": self.session_name,
                "chatId": chat_id,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in (200, 201):
                    logger.debug(f"Sent seen status to {chat_id}")
                    return True
                else:
                    logger.warning(
                        f"Failed to send seen status to {chat_id}: {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.warning(f"Error sending seen status to {chat_id}: {e}")
            return False

    async def start_typing(self, chat_id: str) -> bool:
        """Start typing indicator to mimic human behavior"""
        try:
            url = f"{self.base_url}/startTyping"

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "session": self.session_name,
                "chatId": chat_id,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in (200, 201):
                    logger.debug(f"Started typing to {chat_id}")
                    return True
                else:
                    logger.warning(f"Failed to start typing to {chat_id}: {response.status_code}")
                    return False

        except Exception as e:
            logger.warning(f"Error starting typing to {chat_id}: {e}")
            return False

    async def stop_typing(self, chat_id: str) -> bool:
        """Stop typing indicator"""
        try:
            url = f"{self.base_url}/stopTyping"

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "session": self.session_name,
                "chatId": chat_id,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in (200, 201):
                    logger.debug(f"Stopped typing to {chat_id}")
                    return True
                else:
                    logger.warning(f"Failed to stop typing to {chat_id}: {response.status_code}")
                    return False

        except Exception as e:
            logger.warning(f"Error stopping typing to {chat_id}: {e}")
            return False

    async def get_session_status(self) -> dict | None:
        """Get current session status from WAHA"""
        try:
            url = f"{self.base_url}/sessions/{self.session_name}"

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(
                        f"Failed to get session status. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None
