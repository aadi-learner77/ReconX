from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models.auth import Organization, Permission, Role, User
from app.models.config import AppConfig

DEFAULT_APP_CONFIG = {
    "currency": "INR",
    "tax_policy": {"default_gst_rate": "0.18", "tax_tolerance_abs": "1.00"},
    "duplicate_policy": {"normalize_case": True, "strip_separators": True},
    "approval_limits": {
        "finance_operator": "0",
        "approver": "500000.00",
        "admin": "10000000.00",
    },
    "maker_checker_threshold": "100000.00",
    "confidence_threshold": "0.80",
    "partial_billing_allowed": True,
    "llm_provider": "mock",
}


def ensure_roles_and_permissions(db: Session) -> dict[str, Role]:
    perm_map: dict[str, Permission] = {}
    for code in sorted(ALL_PERMISSIONS):
        perm = db.scalar(select(Permission).where(Permission.code == code))
        if not perm:
            perm = Permission(code=code, description=code)
            db.add(perm)
        perm_map[code] = perm
    db.flush()

    role_map: dict[str, Role] = {}
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            role = Role(name=role_name, description=f"{role_name} role")
            db.add(role)
        role.permissions = [perm_map[c] for c in sorted(perm_codes)]
        role_map[role_name] = role
    db.flush()
    return role_map


def seed_foundation_users(db: Session) -> Organization:
    settings = get_settings()
    role_map = ensure_roles_and_permissions(db)

    org = db.scalar(select(Organization).where(Organization.name == settings.seed_org_name))
    if not org:
        org = Organization(
            name=settings.seed_org_name,
            base_currency="INR",
            timezone="Asia/Kolkata",
            settings_json={"demo": True},
        )
        db.add(org)
        db.flush()

    cfg = db.scalar(
        select(AppConfig).where(AppConfig.organization_id == org.id, AppConfig.is_active.is_(True))
    )
    if not cfg:
        db.add(
            AppConfig(
                organization_id=org.id,
                version=1,
                is_active=True,
                config_json=DEFAULT_APP_CONFIG,
                updated_by="system_seed",
            )
        )

    demo_users = [
        ("operator@reconx-demo.com", "Asha Operator", ["finance_operator"]),
        ("approver@reconx-demo.com", "Vikram Approver", ["approver"]),
        ("procurement@reconx-demo.com", "Neha Procurement", ["procurement"]),
        ("receiving@reconx-demo.com", "Rohan Receiving", ["receiving"]),
        ("auditor@reconx-demo.com", "Meera Auditor", ["auditor"]),
        ("admin@reconx-demo.com", "Karan Admin", ["admin"]),
    ]
    for email, full_name, role_names in demo_users:
        user = db.scalar(
            select(User).where(User.organization_id == org.id, User.email == email)
        )
        if not user:
            user = User(
                organization_id=org.id,
                email=email,
                full_name=full_name,
                password_hash=hash_password(settings.seed_default_password),
                status="ACTIVE",
                roles=[role_map[r] for r in role_names],
            )
            db.add(user)
    db.commit()
    return org
