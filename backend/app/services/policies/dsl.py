import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ALLOWED_FIELDS: dict[str, str] = {
    "purchase_order.total_amount": "decimal",
    "purchase_order.subtotal_amount": "decimal",
    "purchase_order.tax_amount": "decimal",
    "purchase_order.ordered_qty": "decimal",
    "purchase_order.currency": "string",
    "purchase_order.status": "string",
    "goods_receipt.accepted_qty": "decimal",
    "goods_receipt.rejected_qty": "decimal",
    "goods_receipt.received_qty": "decimal",
    "goods_receipt.grn_count": "decimal",
    "invoice.total_amount": "decimal",
    "invoice.subtotal_amount": "decimal",
    "invoice.tax_amount": "decimal",
    "invoice.invoiced_qty": "decimal",
    "invoice.unit_price_max": "decimal",
    "invoice.currency": "string",
    "invoice.is_duplicate": "bool",
    "invoice.invoice_count": "decimal",
    "variance.qty_diff": "decimal",
    "variance.amount_diff": "decimal",
    "variance.price_diff_pct": "decimal",
    "vendor.status": "string",
    "vendor.has_pending_bank_change": "bool",
    "vendor.dispute_count": "decimal",
}

ALLOWED_OPERATORS = {
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "contains",
    "exists",
    "between",
}

MAX_NESTING_DEPTH = 3
MAX_CONDITIONS = 15


class FieldRefValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=3, max_length=80)
    multiplier: str = Field(default="1", max_length=24)

    @model_validator(mode="after")
    def _validate_ref(self) -> "FieldRefValue":
        if self.field not in ALLOWED_FIELDS:
            raise ValueError(f"Unsupported field reference '{self.field}'.")
        try:
            Decimal(self.multiplier)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid Decimal multiplier '{self.multiplier}'.") from exc
        return self


class LeafCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=3, max_length=80)
    operator: str = Field(min_length=2, max_length=16)
    value: str | int | float | bool | list[Any] | FieldRefValue | None = None

    @model_validator(mode="after")
    def _validate_leaf(self) -> "LeafCondition":
        if self.field not in ALLOWED_FIELDS:
            raise ValueError(f"Field '{self.field}' is not in the allowlisted policy fields.")
        if self.operator not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator '{self.operator}' is not supported.")
        ftype = ALLOWED_FIELDS[self.field]
        if self.operator in {"gt", "gte", "lt", "lte", "between"} and ftype != "decimal":
            raise ValueError(
                f"Numeric operator '{self.operator}' requires a decimal field, got '{self.field}'."
            )
        if self.operator == "between":
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError("Operator 'between' requires a 2-element list [low, high].")
            for v in self.value:
                _to_decimal(v)
        elif (
            self.operator in {"gt", "gte", "lt", "lte"}
            and not isinstance(self.value, FieldRefValue)
            and self.value is not None
        ):
            _to_decimal(self.value)
        return self


class ConditionGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    logical_operator: Literal["AND", "OR"] = "AND"
    conditions: list["ConditionGroup | LeafCondition"] = Field(min_length=1, max_length=15)


class PolicyScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_types: list[str] = Field(default_factory=lambda: ["PURCHASE_ORDER", "INVOICE"])


class PolicyAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["CREATE_EXCEPTION"] = "CREATE_EXCEPTION"
    exception_type: str = Field(default="POLICY_VIOLATION", min_length=3, max_length=64)
    instructions: str = Field(default="", max_length=500)


class PolicyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: PolicyScope = Field(default_factory=PolicyScope)
    condition: ConditionGroup | LeafCondition
    action: PolicyAction = Field(default_factory=PolicyAction)

    @model_validator(mode="after")
    def _validate_tree(self) -> "PolicyDefinition":
        count = _count_and_check_depth(self.condition, 1)
        if count > MAX_CONDITIONS:
            raise ValueError(f"Policy exceeds maximum condition count ({MAX_CONDITIONS}).")
        return self


def _count_and_check_depth(node: ConditionGroup | LeafCondition, depth: int) -> int:
    if depth > MAX_NESTING_DEPTH:
        raise ValueError(f"Condition nesting exceeds max depth ({MAX_NESTING_DEPTH}).")
    if isinstance(node, LeafCondition):
        return 1
    return sum(_count_and_check_depth(child, depth + 1) for child in node.conditions)


def _to_decimal(val: Any) -> Decimal:
    if isinstance(val, Decimal):
        return val
    if isinstance(val, bool):
        raise ValueError("Boolean cannot be converted to Decimal.")
    try:
        return Decimal(str(val))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid Decimal value '{val}'.") from exc


def compute_definition_hash(definition: dict[str, Any]) -> str:
    canonical = json.dumps(definition, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_target_value(raw_val: Any, facts: dict[str, Any]) -> Any:
    if isinstance(raw_val, FieldRefValue):
        base = facts.get(raw_val.field)
        if base is None:
            return None
        return _to_decimal(base) * Decimal(raw_val.multiplier)
    return raw_val


def _eval_leaf(leaf: LeafCondition, facts: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = facts.get(leaf.field)
    op = leaf.operator
    target = _resolve_target_value(leaf.value, facts)
    ftype = ALLOWED_FIELDS[leaf.field]

    if op == "exists":
        matched = actual is not None and actual != ""
        return matched, {"field": leaf.field, "operator": op, "actual": str(actual)}

    if actual is None:
        return False, {"field": leaf.field, "operator": op, "actual": None, "reason": "missing"}

    if ftype == "decimal":
        a_dec = _to_decimal(actual)
        if op == "between" and isinstance(target, list) and len(target) == 2:
            low, high = _to_decimal(target[0]), _to_decimal(target[1])
            matched = low <= a_dec <= high
        elif target is None:
            matched = False
        else:
            t_dec = _to_decimal(target)
            if op == "eq":
                matched = a_dec == t_dec
            elif op == "ne":
                matched = a_dec != t_dec
            elif op == "gt":
                matched = a_dec > t_dec
            elif op == "gte":
                matched = a_dec >= t_dec
            elif op == "lt":
                matched = a_dec < t_dec
            elif op == "lte":
                matched = a_dec <= t_dec
            elif op == "in" and isinstance(target, list):
                matched = a_dec in [_to_decimal(x) for x in target]
            elif op == "not_in" and isinstance(target, list):
                matched = a_dec not in [_to_decimal(x) for x in target]
            else:
                matched = False
        return matched, {
            "field": leaf.field,
            "operator": op,
            "actual": str(a_dec),
            "threshold": str(target),
            "matched": matched,
        }

    # String / Boolean evaluation
    if op == "eq":
        matched = str(actual).lower() == str(target).lower()
    elif op == "ne":
        matched = str(actual).lower() != str(target).lower()
    elif op == "contains":
        matched = str(target).lower() in str(actual).lower()
    elif op == "in" and isinstance(target, list):
        matched = str(actual).lower() in [str(x).lower() for x in target]
    elif op == "not_in" and isinstance(target, list):
        matched = str(actual).lower() not in [str(x).lower() for x in target]
    else:
        matched = False

    return matched, {
        "field": leaf.field,
        "operator": op,
        "actual": str(actual),
        "threshold": str(target),
        "matched": matched,
    }


def evaluate_condition_tree(
    node: ConditionGroup | LeafCondition, facts: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    if isinstance(node, LeafCondition):
        matched, trace = _eval_leaf(node, facts)
        return matched, [trace]

    traces: list[dict[str, Any]] = []
    results: list[bool] = []
    for child in node.conditions:
        c_matched, c_traces = evaluate_condition_tree(child, facts)
        results.append(c_matched)
        traces.extend(c_traces)

    overall = all(results) if node.logical_operator == "AND" else any(results)
    return overall, traces
