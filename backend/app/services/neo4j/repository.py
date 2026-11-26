from typing import Any

from neo4j import Query

from app.core.config import get_settings
from app.services.neo4j.driver import neo4j_manager


class Neo4jUnavailableError(RuntimeError):
    """Raised when Neo4j cannot be reached or queried."""


def run_read(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    driver = neo4j_manager.get_driver()
    if driver is None:
        raise Neo4jUnavailableError("Neo4j driver is unavailable.")
    settings = get_settings()
    try:
        with driver.session(database=settings.neo4j_database) as session:
            result = session.run(
                Query(cypher, timeout=float(settings.graph_query_timeout_seconds)),
                params or {},
            )
            return [dict(record) for record in result]
    except Exception as exc:
        raise Neo4jUnavailableError(f"Neo4j read failed: {type(exc).__name__}") from exc


def run_write(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    driver = neo4j_manager.get_driver()
    if driver is None:
        raise Neo4jUnavailableError("Neo4j driver is unavailable.")
    settings = get_settings()
    try:
        with driver.session(database=settings.neo4j_database) as session:
            result = session.run(
                Query(cypher, timeout=float(settings.graph_query_timeout_seconds)),
                params or {},
            )
            return [dict(record) for record in result]
    except Exception as exc:
        raise Neo4jUnavailableError(f"Neo4j write failed: {type(exc).__name__}") from exc
