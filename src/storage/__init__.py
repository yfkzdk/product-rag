# Storage package — lazy imports to avoid hard dependency failures in demo mode
import logging

logger = logging.getLogger(__name__)

try:
    from src.storage.postgres import *
except ImportError as e:
    logger.debug(f"Postgres backend unavailable: {e}")

try:
    from src.storage.milvus import *
except ImportError as e:
    logger.debug(f"Milvus backend unavailable: {e}")

try:
    from src.storage.neo4j import *
except ImportError as e:
    logger.debug(f"Neo4j backend unavailable: {e}")
