import pytest
from loguru import logger
import sys

@pytest.fixture(autouse=True)
def setup_logging():
    logger.remove()  # Remove default handlers
    logger.add(
        sys.stderr,
        format="{time} | {level} | {name}:{function}:{line} | {message}",
        level="DEBUG" # Default level for tests, can be overridden
    )
    logger.add(
        "tests/logs/test_run_{time}.log",
        format="{time} | {level} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="1 MB", # Keep log files small for test runs
        compression="zip"
    )
    logger.info("Loguru setup complete for test run.")

# Optional: If you want to make logger available as a fixture
@pytest.fixture
def log():
    return logger
