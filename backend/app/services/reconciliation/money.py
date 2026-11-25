from decimal import ROUND_HALF_UP, Decimal

CURRENCY_PRECISION: dict[str, int] = {
    "INR": 2,
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "JPY": 0,
}

QTY_QUANT = Decimal("0.0001")
ZERO = Decimal("0")


def get_currency_quantum(currency: str) -> Decimal:
    places = CURRENCY_PRECISION.get(currency.upper(), 2)
    if places <= 0:
        return Decimal("1")
    return Decimal("1").scaleb(-places)


def quantize_money(amount: Decimal, currency: str = "INR") -> Decimal:
    quantum = get_currency_quantum(currency)
    return amount.quantize(quantum, rounding=ROUND_HALF_UP)


def quantize_qty(qty: Decimal) -> Decimal:
    return qty.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def compute_line_extension(qty: Decimal, unit_price: Decimal, currency: str = "INR") -> Decimal:
    return quantize_money(qty * unit_price, currency)
