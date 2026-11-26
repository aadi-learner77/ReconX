from threading import Lock
from typing import Any

from neo4j import Driver, GraphDatabase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("reconx.neo4j")


class Neo4jManager:
    """Application-scoped Neo4j driver manager with safe lazy init & graceful degradation."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._driver: Driver | None = None
        self._schema_initialized = False

    def is_enabled(self) -> bool:
        return get_settings().graph_backend.lower().strip() == "neo4j"

    def get_driver(self) -> Driver | None:
        if not self.is_enabled():
            return None
        with self._lock:
            if self._driver is not None:
                return self._driver
            settings = get_settings()
            if not settings.neo4j_uri or not settings.neo4j_password:
                return None
            try:
                self._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_username, settings.neo4j_password),
                    connection_timeout=float(settings.graph_query_timeout_seconds),
                    max_connection_lifetime=1800,
                    max_connection_pool_size=25,
                )
                return self._driver
            except Exception as exc:
                logger.warning(
                    "neo4j_driver_init_failed",
                    extra={"extra_fields": {"error": type(exc).__name__}},
                )
                self._driver = None
                return None

    def verify_connectivity(self) -> tuple[bool, str]:
        if not self.is_enabled():
            return False, "GRAPH_BACKEND is not neo4j"
        driver = self.get_driver()
        if driver is None:
            return False, "Neo4j driver not configured or unavailable"
        try:
            driver.verify_connectivity()
            return True, "Connected"
        except Exception as exc:
            return False, f"Unavailable ({type(exc).__name__})"

    def close(self) -> None:
        with self._lock:
            if self._driver is not None:
                try:
                    self._driver.close()
                except Exception:
                    pass
                self._driver = None
            self._schema_initialized = False

    @property
    def schema_initialized(self) -> bool:
        return self._schema_initialized

    def mark_schema_initialized(self) -> None:
        self._schema_initialized = True

    def status_snapshot(self) -> dict[str, Any]:
        settings = get_settings()
        ok, detail = self.verify_connectivity()
        return {
            "enabled": self.is_enabled(),
            "graph_backend": settings.graph_backend,
            "connected": ok,
            "database": settings.neo4j_database,
            "detail": detail,
            "schema_initialized": self._schema_initialized,
        }


neo4j_manager = Neo4jManager()
