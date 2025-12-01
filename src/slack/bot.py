"""
RecycleOps AI Assistant - Slack Bot

Main Slack Bolt application setup and configuration.
"""
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import structlog

from src.config import settings
from src.slack.events import register_event_handlers
from src.slack.commands import register_commands
from src.slack.middleware import register_middleware


logger = structlog.get_logger(__name__)


def create_slack_app() -> App:
    """
    Create and configure the Slack Bolt application.
    
    Returns:
        Configured Slack App instance
    """
    logger.info("Creating Slack application...")
    
    # Create the Slack Bolt app
    app = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )
    
    # Register middleware
    register_middleware(app)
    
    # Register event handlers
    register_event_handlers(app)
    
    # Register slash commands
    register_commands(app)
    
    # Log successful setup
    logger.info("Slack application created successfully")
    
    return app


def start_slack_app(app: App) -> None:
    """
    Start the Slack app using Socket Mode.
    
    Socket Mode allows the app to receive events without exposing a public URL.
    This is ideal for development and internal deployments.
    
    Args:
        app: The configured Slack App instance
    """
    logger.info("Starting Slack app in Socket Mode...")
    
    handler = SocketModeHandler(
        app=app,
        app_token=settings.slack_app_token,
    )
    
    # This blocks and runs the app
    handler.start()
