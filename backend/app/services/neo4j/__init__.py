"""Managed Neo4j driver lifecycle, health checks, and schema initialization."""
from typing import Any

from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.health import get_graph_health, get_sync_status
from app.services.neo4j.schema import ensure_neo4j_schema

__all__ = [
    "ensure_neo4j_schema",
    "get_graph_health",
    "get_sync_status",
    "neo4j_manager",
]
