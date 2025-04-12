# Utils package initialization
import logging
import os


def setup_logging() -> None:
    """Configure logging for the application."""
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(f"{log_dir}/app.log"), logging.StreamHandler()],
    )

    # Set third-party loggers to WARNING level
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)


# Initialize logging when module is imported
setup_logging()
