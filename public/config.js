// Kalolsavam API origin.
//
// Architecture:
//   - Static frontend (Astro build) is deployed to Cloudflare Pages.
//   - FastAPI backend runs on a self-hosted server, exposed via Cloudflare
//     Tunnel at the hostname below. It is never directly reachable.
//   - Static staff portals (/admin/, /dashboard/, /stagemaster/) are also
//     served from Pages and call this origin.
//
// Astro pages get <body data-api="..."> baked from PUBLIC_API_URL at build
// time, and common.js / api.js check data-api first — so a local Docker
// dev build with PUBLIC_API_URL=same-origin still calls the same origin
// without editing this file. This value is the fallback for the static
// HTML portals, which have no data-api attribute.
window.KAL_API_BASE = "https://apikalolsavammala.dpdns.org";
