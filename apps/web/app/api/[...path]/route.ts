import { NextRequest, NextResponse } from "next/server";

/**
 * BFF proxy: the browser only talks to Next.js (same origin), Next.js forwards /api/* to FastAPI.
 * BACKEND_URL is server-side only (never exposed to the browser).
 */
const BACKEND_URL = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const UPSTREAM_TIMEOUT_MS = 180_000; // AI mentor tool loops can take several model round-trips

const FORWARD_REQUEST_HEADERS = ["accept", "accept-language", "content-type", "range", "if-none-match", "if-modified-since", "authorization", "cookie"];
const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

type RouteParams = { params: Promise<{ path: string[] }> };

function buildTarget(req: NextRequest, segments: string[]): URL | null {
  // Reject traversal so the proxy can only reach /api/* on the backend.
  if (segments.some((segment) => !segment || segment === "." || segment === ".." || /[\\/]/.test(segment))) {
    return null;
  }
  const target = new URL(`${BACKEND_URL}/api/${segments.map(encodeURIComponent).join("/")}`);
  target.search = req.nextUrl.search; // keeps repeated keys and original encoding
  return target;
}

async function proxy(req: NextRequest, { params }: RouteParams): Promise<Response> {
  const { path } = await params;
  const target = buildTarget(req, path ?? []);
  if (!target) {
    return NextResponse.json({ error: "Invalid API path" }, { status: 400 });
  }

  const headers = new Headers();
  for (const name of FORWARD_REQUEST_HEADERS) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }

  const hasBody = !["GET", "HEAD"].includes(req.method);
  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.any([req.signal, AbortSignal.timeout(UPSTREAM_TIMEOUT_MS)]),
    });

    const responseHeaders = new Headers();
    // fetch() transparently decodes compressed bodies, so encoding/length headers would no longer match.
    const decoded = upstream.headers.has("content-encoding");
    upstream.headers.forEach((value, key) => {
      const name = key.toLowerCase();
      if (HOP_BY_HOP.has(name) || name === "content-encoding" || (decoded && name === "content-length")) return;
      responseHeaders.set(key, value);
    });

    return new Response(req.method === "HEAD" ? null : upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    const timedOut = error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError");
    const detail = error instanceof Error ? error.message : String(error);
    console.error(`[BFF] ${req.method} ${target.pathname} failed: ${detail}`);
    return NextResponse.json(
      {
        error: timedOut
          ? "Backend phản hồi quá lâu (timeout)."
          : "Không kết nối được FastAPI backend. Kiểm tra server đã chạy ở BACKEND_URL chưa.",
      },
      { status: timedOut ? 504 : 502 },
    );
  }
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
