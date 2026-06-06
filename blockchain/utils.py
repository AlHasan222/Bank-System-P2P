"""Utility functions for the blockchain."""
import hashlib
import json
import time
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def setup_logger(name: str, level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def hash_block(block: Dict[str, Any]) -> str:
    block_string = json.dumps(block, sort_keys=True)
    return sha256(block_string)


def get_timestamp() -> float:
    return time.time()


def parse_node_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def generate_transaction_id() -> str:
    return sha256(f"{time.time()}{__import__('random').random()}")[:16]


def validate_amount(amount: Any) -> bool:
    try:
        return float(amount) > 0
    except (ValueError, TypeError):
        return False


def validate_transaction_type(tx_type: str) -> bool:
    return tx_type in ('deposit', 'withdrawal', 'transfer')