# core/logger.py
import logging
from core.config import LOG_LEVEL

# Setup format log
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger("JasebBot")