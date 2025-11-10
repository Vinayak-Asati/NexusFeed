"""Main entry point for NexusFeed application."""

from config import Config
from helpers.logger import setup_logger


def main():
    """Main application entry point."""
    # Ensure directories exist
    Config.ensure_directories()
    
    # Setup logger
    logger = setup_logger(
        name="nexusfeed",
        log_file=Config.LOG_FILE,
        level=getattr(__import__('logging'), Config.LOG_LEVEL)
    )
    
    logger.info("NexusFeed application starting...")
    logger.info(f"Data directory: {Config.DATA_DIR}")
    logger.info(f"Logs directory: {Config.LOGS_DIR}")
    
    # TODO: Add application logic here
    logger.info("NexusFeed application initialized.")


if __name__ == "__main__":
    main()

