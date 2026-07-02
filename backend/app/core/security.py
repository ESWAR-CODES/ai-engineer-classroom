import os
import logging
from logging.handlers import RotatingFileHandler

# Define base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE = os.path.join(BASE_DIR, "classroom_app.log")

# Setup Logging Guardrails
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("classroom_prod")

# Rotating log handler - max size 2MB with 3 backup logs kept
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

def verify_environment_keys():
    """Validates presence of critical production variable keys, logging status safely."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY is not defined in system environment parameters. "
            "Sandbox/Fallback models will trigger for LLM content generation pipelines."
        )
    else:
        # Avoid print logging sensitive credentials
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
        logger.info(f"API Environment configurations initialized. GEMINI_API_KEY loaded: {masked_key}")
