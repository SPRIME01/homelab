import sys
from pathlib import Path

# Add the tools/logging/python directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "tools" / "logging" / "python"))

from logger import logger


def main():
    # Create a logger with service name for better identification
    app_logger = logger.bind(service="homelab-main")

    # Log the greeting message with context
    app_logger.info(
        "Hello from homelab!",
        component="main",
        action="startup",
        message_type="greeting"
    )


if __name__ == "__main__":
    main()
