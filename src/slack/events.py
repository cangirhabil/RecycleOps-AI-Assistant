"""
RecycleOps AI Assistant - Slack Event Handlers

Handlers for Slack events like messages, reactions, etc.
"""
import asyncio
import re
from datetime import datetime
from typing import Optional

from slack_bolt import App
from slack_sdk import WebClient
import structlog

from src.config import settings
from src.services.proactive_service import ProactiveService
from src.services.conversation_service import ConversationService


logger = structlog.get_logger(__name__)

# Patterns that indicate an error message
ERROR_PATTERNS = [
    r"\[DESTEK\]",
    r"\[HATA\]",
    r"\[ERROR\]",
    r"\[ARIZA\]",
    r"hata\s+alıyoruz",
    r"çalışmıyor",
    r"arıza",
    r"sıkışma",
    r"durdu",
    r"problem",
]


def is_error_message(text: str) -> bool:
    """Check if a message appears to be an error report."""
    if not text:
        return False
    
    text_lower = text.lower()
    for pattern in ERROR_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def extract_error_info(text: str) -> dict:
    """Extract error information from message text."""
    info = {
        "machine_type": None,
        "error_type": None,
        "location": None,
    }
    
    # Try to extract machine type (e.g., A1100, B2200, etc.)
    machine_match = re.search(r"\b([A-Z]\d{3,4})\b", text)
    if machine_match:
        info["machine_type"] = machine_match.group(1)
    
    # Try to extract location
    location_patterns = [
        r"(\w+)\s+şubesi",
        r"(\w+)\s+fabrikası",
        r"(\w+)\s+tesisi",
        r"lokasyon[:\s]+(\w+)",
    ]
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info["location"] = match.group(1)
            break
    
    return info


def handle_message(
    event: dict,
    client: WebClient,
    logger: structlog.BoundLogger,
) -> None:
    """
    Handle incoming message events.
    
    This handler:
    1. Tracks conversations for the 12-hour learning rule
    2. Detects error messages and triggers proactive support
    3. Updates expert activity metrics
    """
    # Ignore bot messages
    if event.get("bot_id"):
        return
    
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text", "")
    ts = event.get("ts")
    thread_ts = event.get("thread_ts")  # None if not in a thread
    
    # Skip if not in a monitored channel
    if settings.monitor_channel_ids and channel_id not in settings.monitor_channel_ids:
        return
    
    logger.info(
        "Processing message",
        channel=channel_id,
        user=user_id,
        is_thread=thread_ts is not None,
    )
    
    # Track conversation
    try:
        conversation_service = ConversationService()
        asyncio.run(conversation_service.track_message(
            channel_id=channel_id,
            thread_ts=thread_ts or ts,  # Use message ts as thread_ts for parent messages
            message_ts=ts,
            user_id=user_id,
            text=text,
        ))
    except Exception as e:
        logger.error("Failed to track conversation", error=str(e))
    
    # Check for error patterns (only for parent messages, not thread replies)
    if not thread_ts and is_error_message(text):
        logger.info("Detected potential error message", channel=channel_id, ts=ts)
        
        # Extract error info
        error_info = extract_error_info(text)
        
        # Trigger proactive support
        if settings.proactive_support_enabled:
            try:
                proactive_service = ProactiveService(client)
                asyncio.run(proactive_service.suggest_solution(
                    channel_id=channel_id,
                    thread_ts=ts,
                    error_text=text,
                    error_info=error_info,
                ))
            except Exception as e:
                logger.error("Failed to provide proactive support", error=str(e))


def handle_app_mention(
    event: dict,
    client: WebClient,
    say,
    logger: structlog.BoundLogger,
) -> None:
    """
    Handle @mention events for the bot.
    
    Users can mention the bot to ask questions directly.
    """
    user_id = event.get("user")
    text = event.get("text", "")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")
    
    # Remove the bot mention from the text
    # The mention format is <@BOTID>
    clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    
    if not clean_text:
        say(
            text="Merhaba! Size nasıl yardımcı olabilirim? Bir hata açıklaması yazın, "
                 "geçmiş çözümlerimden öneriler sunayım. 🔧",
            thread_ts=thread_ts,
        )
        return
    
    logger.info(
        "App mention received",
        user=user_id,
        channel=channel_id,
        query=clean_text[:100],
    )
    
    # Search for solutions
    try:
        proactive_service = ProactiveService(client)
        asyncio.run(proactive_service.respond_to_mention(
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
            query=clean_text,
        ))
    except Exception as e:
        logger.error("Failed to handle app mention", error=str(e))
        say(
            text="⚠️ Üzgünüm, bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            thread_ts=thread_ts,
        )


def handle_reaction_added(
    event: dict,
    client: WebClient,
    logger: structlog.BoundLogger,
) -> None:
    """
    Handle reaction added events.
    
    Used to collect feedback on solutions (👍 = helpful, 👎 = not helpful)
    """
    reaction = event.get("reaction")
    user_id = event.get("user")
    item = event.get("item", {})
    
    # Only process reactions on messages
    if item.get("type") != "message":
        return
    
    channel_id = item.get("channel")
    message_ts = item.get("ts")
    
    # Check if this is a feedback reaction
    if reaction in ["thumbsup", "+1", "white_check_mark"]:
        is_helpful = True
    elif reaction in ["thumbsdown", "-1", "x"]:
        is_helpful = False
    else:
        return  # Not a feedback reaction
    
    logger.info(
        "Feedback reaction received",
        reaction=reaction,
        is_helpful=is_helpful,
        channel=channel_id,
        message_ts=message_ts,
    )
    
    # TODO: Record feedback in database
    # This requires tracking which messages contain solution suggestions


def register_event_handlers(app: App) -> None:
    """
    Register all event handlers with the Slack app.
    
    Args:
        app: The Slack App instance
    """
    
    @app.event("message")
    def message_handler(event, client, logger):
        handle_message(event, client, logger)
    
    @app.event("app_mention")
    def app_mention_handler(event, client, say, logger):
        handle_app_mention(event, client, say, logger)
    
    @app.event("reaction_added")
    def reaction_added_handler(event, client, logger):
        handle_reaction_added(event, client, logger)
    
    # Log unhandled events for debugging
    @app.event({"type": re.compile(".*")})
    def catch_all_handler(event, logger):
        event_type = event.get("type", "unknown")
        if event_type not in ["message", "app_mention", "reaction_added"]:
            logger.debug("Unhandled event type", event_type=event_type)
    
    logger.info("Slack event handlers registered")
