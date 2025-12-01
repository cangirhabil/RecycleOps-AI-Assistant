"""
RecycleOps AI Assistant - Slack Middleware

Custom middleware for logging, authentication, and request processing.
"""
from typing import Callable
from slack_bolt import App, BoltContext
from slack_bolt.request import BoltRequest
from slack_bolt.response import BoltResponse
import structlog


logger = structlog.get_logger(__name__)


def log_request_middleware(
    req: BoltRequest,
    resp: BoltResponse,
    next: Callable,
):
    """
    Middleware to log all incoming Slack requests.
    """
    # Extract relevant info for logging - use body instead of payload
    body = req.body or {}
    event_type = body.get("type", "unknown")
    user_id = None
    channel_id = None
    
    if "event" in body:
        event = body["event"]
        event_type = event.get("type", event_type)
        user_id = event.get("user")
        channel_id = event.get("channel")
    elif "command" in body:
        event_type = f"command:{body.get('command', 'unknown')}"
        user_id = body.get("user_id")
        channel_id = body.get("channel_id")
    
    logger.info(
        "Incoming Slack request",
        event_type=event_type,
        user_id=user_id,
        channel_id=channel_id,
    )
    
    # Continue to next middleware/handler
    return next()


def error_handler_middleware(
    error: Exception,
    body: dict,
    logger: structlog.stdlib.BoundLogger,
):
    """
    Global error handler for the Slack app.
    """
    logger.exception(
        "Error processing Slack request",
        error=str(error),
        error_type=type(error).__name__,
    )


def register_middleware(app: App) -> None:
    """
    Register all middleware with the Slack app.
    
    Args:
        app: The Slack App instance
    """
    # Add logging middleware
    app.middleware(log_request_middleware)
    
    # Register global error handler
    app.error(error_handler_middleware)
    
    logger.info("Slack middleware registered")
