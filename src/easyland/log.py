from loguru import logger

logger.remove()  # Remove default handler
logger.add(
    "easyland.log",
    level="INFO",
    rotation="10 MB",
    retention="10 days",
    compression="zip",
)
logger.add(lambda msg: print(msg, end=""), level="INFO")
