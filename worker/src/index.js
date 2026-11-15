// Written with AI assistance (Claude, Anthropic) for InfoFlame, NASA Space Apps Challenge 2026, team Spacecrammers. See AI_USE.md.
// InfoFlame AI proxy (Cloudflare Worker) for the Gemini API.
// Keeps the Gemini API key secret, so the public GitHub Pages site can use the model.
// The browser runs the tool loop on its own embedded data; this worker only forwards
// generateContent calls with server-side limits (model, output size, request size, origin, rate).

const API = "https://generativelanguage.googleapis.com/v1beta/models/";
const SYSTEM_PREFIX =
  "You are the assistant inside InfoFlame, a dashboard of NASA PSI microgravity combustion data for spacecraft and habitat fire safety. " +
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
    const model = env.MODEL || "gemini-3.5-flash-lite";

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: h });
    if (url.pathname === "/health") return json(200, { ok: true, provider: "gemini", model, fallback: env.FALLBACK_MODEL || null, keySet: Boolean(env.GEMINI_API_KEY) }, h);
    if (request.method !== "POST" || url.pathname !== "/v1/generate") return json(404, { error: "not found" }, h);
    if (allowed.length && !allowed.includes(origin)) return json(403, { error: "origin not allowed" }, h);
    if (!env.GEMINI_API_KEY) return json(500, { error: "server is missing GEMINI_API_KEY" }, h);

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (limited(ip, Number(env.RATE_PER_MINUTE || 12))) return json(429, { error: "rate limited" }, h);

    const raw = await request.text();
    if (raw.length > 300_000) return json(413, { error: "request too large" }, h);
    let body;
    try { body = JSON.parse(raw); } catch { return json(400, { error: "invalid JSON" }, h); }
    if (!Array.isArray(body.contents) || body.contents.length === 0) return json(400, { error: "contents required" }, h);

    const clientSystem = (body.systemInstruction?.parts || []).map((p) => p.text || "").join("\n").slice(0, 6000);
    const upstreamBody = {
      systemInstruction: { parts: [{ text: SYSTEM_PREFIX + "\n\n" + clientSystem }] },
      contents: body.contents.slice(-30),
      ...(Array.isArray(body.tools) ? { tools: body.tools.slice(0, 2) } : {}),
      generationConfig: {
        maxOutputTokens: Math.min(Number(body.generationConfig?.maxOutputTokens) || 2048, Number(env.MAX_OUTPUT_TOKENS || 2048)),
      },
    };

    const call = (m) => fetch(API + encodeURIComponent(m) + ":generateContent", {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY },
      body: JSON.stringify(upstreamBody),
    });
    let r = await call(model);
    // free-tier quota for the main model used up -> try the fallback model once (separate quota)
    if (r.status === 429 && env.FALLBACK_MODEL && env.FALLBACK_MODEL !== model) r = await call(env.FALLBACK_MODEL);
    const text = await r.text();
    return new Response(text, { status: r.status, headers: { "content-type": "application/json", ...h } });
  },
};
