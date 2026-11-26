from app.core.logging import get_logger
from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.repository import Neo4jUnavailableError, run_write

logger = get_logger("reconx.neo4j.schema")

NODE_LABELS = [
    "Organization",
    "Vendor",
    "PurchaseOrder",
    "POLine",
    "GoodsReceipt",
    "GRNLine",
    "Invoice",
    "InvoiceLine",
    "Document",
    "ReconciliationRun",
    "Exception",
    "RiskSignal",
    "Policy",
    "PolicyVersion",
    "PolicyEvaluation",
    "Investigation",
    "Approval",
    "AuditEvent",
    "AgentRun",
    "AgentStageExecution",
    "AgentDefinition",
    "ToolCall",
    "EvidenceReference",
]


def ensure_neo4j_schema() -> bool:
    """Idempotently initialize uniqueness constraints and organization indexes in Neo4j."""
    if not neo4j_manager.is_enabled():
        return False
    ok, _ = neo4j_manager.verify_connectivity()
    if not ok:
        return False

    try:
        for label in NODE_LABELS:
            c_name = f"uniq_{label.lower()}_graph_key"
            run_write(
                f"CREATE CONSTRAINT {c_name} IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.graph_key IS UNIQUE"
            )
            idx_name = f"idx_{label.lower()}_org"
            run_write(
                f"CREATE INDEX {idx_name} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.organization_id)"
            )
        neo4j_manager.mark_schema_initialized()
        return True
    except Neo4jUnavailableError as exc:
        logger.warning(
            "neo4j_schema_init_deferred",
            extra={"extra_fields": {"error": str(exc)}},
        )
        return False
