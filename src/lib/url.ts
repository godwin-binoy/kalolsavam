// Astro normalises import.meta.env.BASE_URL to always include a trailing slash.
// Fallback to '/' for safety if the env var is missing.
const RAW = import.meta.env.BASE_URL || "/";
export const BASE = RAW.endsWith("/") ? RAW : RAW + "/";

const RAW_API = (import.meta.env.PUBLIC_API_URL ?? "https://apikalolsavammala.dpdns.org").trim();
export const API_BASE = RAW_API.replace(/\/+$/, "");

export function url(path: string): string {
  if (!path) return BASE;
  // External, protocol-relative, mailto/tel, anchors, data URLs: leave alone.
  if (/^(?:https?:|mailto:|tel:|data:|#|\/\/)/.test(path)) return path;
  // Idempotent: if path already starts with BASE, don't double-prefix.
  if (BASE !== "/" && path.startsWith(BASE)) return path;
  return BASE + path.replace(/^\/+/, "");
}
