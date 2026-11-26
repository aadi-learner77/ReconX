/**
 * Decimal-safe Indian grouping formatter for monetary strings from the API.
 * NEVER converts amounts to binary float or Number.
 */
export function formatInrString(raw: string | null | undefined, currency = "INR"): string {
  if (raw === null || raw === undefined || raw === "") return "—";
  const cleaned = String(raw).trim();
  const match = cleaned.match(/^(-?)(\d+)(?:\.(\d+))?$/);
  if (!match) return cleaned;

  const sign = match[1];
  const intPart = match[2];
  const fracRaw = (match[3] || "00").slice(0, 2).padEnd(2, "0");

  let grouped = intPart;
  if (intPart.length > 3) {
    const last3 = intPart.slice(-3);
    const rest = intPart.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
    grouped = `${rest},${last3}`;
  }

  const prefix = currency.toUpperCase() === "INR" ? "₹" : `${currency.toUpperCase()} `;
  return `${sign}${prefix}${grouped}.${fracRaw}`;
}
