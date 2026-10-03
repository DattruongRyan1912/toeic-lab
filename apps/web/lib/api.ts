/** Browser-side client for the FastAPI backend, always called through the Next.js BFF proxy (/api/*). */

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiInit = Omit<RequestInit, "body"> & { json?: unknown; body?: BodyInit | null };

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    const detail = record.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // FastAPI validation errors: [{loc: [...], msg: "..."}]
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const loc = Array.isArray((item as { loc?: unknown[] }).loc) ? (item as { loc: unknown[] }).loc.slice(-1)[0] : "";
            return `${loc ? `${String(loc)}: ` : ""}${String((item as { msg: unknown }).msg)}`;
          }
          return String(item);
        })
        .join("; ");
    }
    if (typeof record.error === "string") return record.error; // BFF proxy error
  }
  if (typeof body === "string" && body.trim()) return body.slice(0, 300);
  return fallback;
}

const TOKEN_KEY = "toeic_access_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Ignore quota or private mode errors
  }
}

export async function api<T>(path: string, init: ApiInit = {}): Promise<T> {
  const { json, headers, body, ...rest } = init;
  const token = getAuthToken();
  const response = await fetch(`/api${path.startsWith("/") ? path : `/${path}`}`, {
    cache: "no-store",
    ...rest,
    headers: {
      Accept: "application/json",
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : body,
  });
  const text = await response.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }
  if (!response.ok) {
    throw new ApiError(response.status, detailMessage(parsed, `Lỗi HTTP ${response.status}`));
  }
  return parsed as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "Không kết nối được máy chủ. Kiểm tra FastAPI (cổng 8000) đã chạy chưa.";
  if (error instanceof Error) return error.message;
  return "Đã có lỗi xảy ra";
}

export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
