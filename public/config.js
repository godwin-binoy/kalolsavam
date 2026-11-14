// Kalolsavam API origin.
//
// Production is split: static Astro build on Cloudflare Pages (*.pages.dev)
// talks to the FastAPI backend via a Cloudflare Tunnel at a different host.
// Docker self-host, local preview, and tests serve frontend + API from one
// origin. Detect the split by hostname.
//
// Self-hosting on a custom domain? Override window.KAL_API_BASE before this
// script loads, or edit the tunnel URL below.
(function () {
  var host = (location.hostname || '').toLowerCase();
  var isPages = host === 'pages.dev' || host.endsWith('.pages.dev');
  window.KAL_API_BASE = isPages
    ? 'https://apikalolsavammala.dpdns.org'
    : '';
})();
