import json
import logging
from datetime import datetime
from pathlib import Path

AUDIT_LOG_PATH = Path(__file__).parents[2] / "audit.log"

def setup_audit_logger():
    logger = logging.getLogger("audit")
    logger.setLevel(logging.INFO)
    # Avoid adding multiple handlers
    if not logger.handlers:
        handler = logging.FileHandler(AUDIT_LOG_PATH)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

audit_logger = setup_audit_logger()

def log_event(event_type: str, data: dict):
    """Log an audit event with timestamp"""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event_type,
        "data": data
    }
    audit_logger.info(json.dumps(entry))