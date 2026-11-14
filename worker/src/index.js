// FireSight AI proxy (Cloudflare Worker).
// Keeps the Anthropic API key secret, so the public GitHub Pages site can use Claude.
// The browser runs the tool loop on its own embedded data; this worker only forwards
// Messages API calls with server-side limits (model, tokens, size, origin, rate).

const UPSTREAM = "https://api.anthropic.com/v1/messages";
const SYSTEM_PREFIX =
  "You are the assistant inside FireSight, a dashboard of NASA PSI microgravity combustion data for spacecraft and habitat fire safety. " +
  "Only answer questions about that data and fire safety in crewed spacecraft, habitats and related Earth analogs, using the provided tools. " +
  "Politely decline anything unrelated in one sentence.";

const hits = new Map(); // best-effort per-IP limiter (per Worker instance)

function cors(origin, allowed) {
  const ok = allowed.length === 0 || allowed.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin || "*" : "null",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(status, obj, headers) {
  return new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", ...headers } });
}

function limited(ip, perMinute) {
  const now = Date.now();
  const arr = (hits.get(ip) || []).filter((t) => now - t < 60_000);
  arr.push(now);
  hits.set(ip, arr);
  if (hits.size > 5000) hits.clear();
  return arr.length > perMinute;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
    const h = cors(origin, allowed);
    const url = new URL(request.url);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: h });
    if (url.pathname === "/health") return json(200, { ok: true, model: env.MODEL || "claude-haiku-5-5" }, h);
    if (request.method !== "POST" || url.pathname !== "/v1/messages") return json(404, { error: "not found" }, h);
    if (allowed.length && !allowed.includes(origin)) return json(403, { error: "origin not allowed" }, h);
    if (!env.ANTHROPIC_API_KEY) return json(500, { error: "server is missing ANTHROPIC_API_KEY" }, h);

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const perMinute = Number(env.RATE_PER_MINUTE || 12);
    if (env.RATE_LIMITER) {
      try {
        const { success } = await env.RATE_LIMITER.limit({ key: ip });
        if (!success) return json(429, { error: "rate limited" }, h);
      } catch (e) { /* binding not available: fall back below */ }
    }
    if (limited(ip, perMinute)) return json(429, { error: "rate limited" }, h);

    const raw = await request.text();
    if (raw.length > 300_000) return json(413, { error: "request too large" }, h);
    let body;
    try { body = JSON.parse(raw); } catch { return json(400, { error: "invalid JSON" }, h); }
    if (!Array.isArray(body.messages) || body.messages.length === 0) return json(400, { error: "messages required" }, h);

    const upstreamBody = {
      model: env.MODEL || "claude-haiku-5-5",
      max_tokens: Math.min(Number(body.max_tokens) || 900, Number(env.MAX_TOKENS || 1200)),
      system: SYSTEM_PREFIX + "\n\n" + String(body.system || "").slice(0, 6000),
      messages: body.messages.slice(-24),
      ...(Array.isArray(body.tools) ? { tools: body.tools.slice(0, 8) } : {}),
    };

    const r = await fetch(UPSTREAM, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(upstreamBody),
    });
    const text = await r.text();
    return new Response(text, { status: r.status, headers: { "content-type": "application/json", ...h } });
  },
};
