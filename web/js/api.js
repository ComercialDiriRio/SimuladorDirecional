/**
 * Cliente HTTP da API (cookies + JSON).
 */
const API_BASE = "";

export async function apiGet(path) {
  const r = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  const text = await r.text();
  if (!r.ok) throw new Error(`${r.status} ${text}`);
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiPost(path, body, contentType = "application/json") {
  const opts = {
    method: "POST",
    credentials: "include",
    headers: {},
  };
  if (body !== undefined && body !== null) {
    if (contentType === "application/json") {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    } else {
      opts.body = body;
    }
  }
  const r = await fetch(`${API_BASE}${path}`, opts);
  const ct = r.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = await r.json();
    if (!r.ok) throw new Error(JSON.stringify(data));
    return data;
  }
  const buf = await r.arrayBuffer();
  if (!r.ok) throw new Error(`${r.status}`);
  return buf;
}

export async function apiPatch(path, body) {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`${r.status} ${text}`);
  return JSON.parse(text);
}

export async function apiPut(path, body) {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`${r.status} ${text}`);
  return JSON.parse(text);
}

export async function apiDelete(path) {
  const r = await fetch(`${API_BASE}${path}`, { method: "DELETE", credentials: "include" });
  const text = await r.text();
  if (!r.ok) throw new Error(`${r.status} ${text}`);
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
