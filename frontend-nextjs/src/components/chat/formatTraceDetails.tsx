import { formatBreakdownKey } from "@/types/claim";

const CURRENCY_KEYS =
  /amount|remaining|deducted|claimed|approved|copay_amount|sub_limit|limit|total/i;
const PERCENT_KEYS = /percent|rate|ratio/i;

export function formatDetailLabel(key: string): string {
  return formatBreakdownKey(key);
}

export function formatScalar(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (PERCENT_KEYS.test(key) && value <= 1) return `${Math.round(value * 100)}%`;
    if (PERCENT_KEYS.test(key)) return `${value}%`;
    if (CURRENCY_KEYS.test(key)) return `₹${value.toLocaleString("en-IN")}`;
    if (key.includes("confidence") && value <= 1) return `${Math.round(value * 100)}%`;
    return value.toLocaleString("en-IN");
  }
  return String(value);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isLineItem(value: unknown): value is {
  description?: string;
  amount?: number;
  approved?: boolean | null;
  rejection_reason?: string | null;
} {
  return isPlainObject(value) && ("description" in value || "amount" in value);
}

export function DetailValue({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined || value === "") return null;

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <div className="py-0.5">
          <span className="font-medium text-text-muted">{formatDetailLabel(label)}: </span>
          <span className="text-text-muted italic">None</span>
        </div>
      );
    }

    if (value.every((item) => typeof item === "string" || typeof item === "number")) {
      return (
        <div className="py-0.5">
          <span className="font-medium text-text-muted">{formatDetailLabel(label)}: </span>
          <span className="text-text">{value.join(", ")}</span>
        </div>
      );
    }

    if (value.every(isLineItem)) {
      return (
        <div className="py-1">
          <p className="mb-1 font-medium text-text-muted">{formatDetailLabel(label)}</p>
          <ul className="space-y-1.5">
            {value.map((item, i) => (
              <li
                key={`${item.description ?? i}-${i}`}
                className="rounded-md border border-black/[0.06] bg-white/60 px-2.5 py-1.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-text">{item.description ?? "Item"}</span>
                  {item.amount != null && (
                    <span className="text-text-muted">
                      ₹{Number(item.amount).toLocaleString("en-IN")}
                    </span>
                  )}
                </div>
                {item.approved != null && (
                  <p className="mt-0.5 text-[11px] text-text-muted">
                    {item.approved ? "Approved" : "Rejected"}
                    {item.rejection_reason ? ` · ${item.rejection_reason}` : ""}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      );
    }

    return (
      <div className="py-0.5">
        <span className="font-medium text-text-muted">{formatDetailLabel(label)}: </span>
        <span className="text-text">{value.map(String).join(", ")}</span>
      </div>
    );
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value).filter(([, v]) => v !== null && v !== undefined);
    if (entries.length === 0) return null;

    return (
      <div className="py-1">
        <p className="mb-1.5 font-medium text-text-muted">{formatDetailLabel(label)}</p>
        <dl className="space-y-1 rounded-md border border-black/[0.06] bg-white/60 px-2.5 py-2">
          {entries.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 text-[11px]">
              <dt className="text-text-muted">{formatDetailLabel(k)}</dt>
              <dd className="text-right font-medium text-text">{formatScalar(k, v)}</dd>
            </div>
          ))}
        </dl>
      </div>
    );
  }

  return (
    <div className="py-0.5">
      <span className="font-medium text-text-muted">{formatDetailLabel(label)}: </span>
      <span className="text-text">{formatScalar(label, value)}</span>
    </div>
  );
}
