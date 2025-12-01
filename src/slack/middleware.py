"""
RecycleOps AI Assistant - Slack Middleware

Custom middleware for logging, authentication, and request processing.
"""
from slack_bolt import App, BoltContext, BoltRequest
from slack_bolt.response import BoltResponse
import structlog


logger = structlog.get_logger(__name__)


def log_request_middleware(
    req: BoltRequest,
    resp: BoltResponse,
    next_fn,
):
    """
    Middleware to log all incoming Slack requests.
    """
    # Extract relevant info for logging
    event_type = req.payload.get("type", "unknown")
    user_id = None
    channel_id = None
    
    if "event" in req.payload:
        event = req.payload["event"]
        event_type = event.get("type", event_type)
        user_id = event.get("user")
        channel_id = event.get("channel")
    elif "command" in req.payload:
        event_type = f"command:{req.payload.get('command', 'unknown')}"
        user_id = req.payload.get("user_id")
        channel_id = req.payload.get("channel_id")
    
    logger.info(
        "Incoming Slack request",
        event_type=event_type,
        user_id=user_id,
        channel_id=channel_id,
    )
    
    # Continue to next middleware/handler
    return next_fn()


def error_handler_middleware(
    error: Exception,
    req: BoltRequest,
    resp: BoltResponse,
    context: BoltContext,
    next_fn,
):
    """
    Global error handler for the Slack app.
    """
    logger.exception(
        "Error processing Slack request",
        error=str(error),
        error_type=type(error).__name__,
    )
    
    # Try to notify the user if possible
    try:
        if context.client and context.channel_id:
            context.client.chat_postEphemeral(
                channel=context.channel_id,
                user=context.user_id,
                text="⚠️ Bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            )
    except Exception:
        pass  # Silently fail if we can't notify
    
    return BoltResponse(status=200)


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
