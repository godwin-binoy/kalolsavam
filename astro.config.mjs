import { defineConfig } from 'astro/config';

function normalizeBase(raw) {
  if (!raw || raw === '/') return '/';
  let b = raw.trim();
  if (!b.startsWith('/')) b = '/' + b;
  if (!b.endsWith('/')) b = b + '/';
  return b;
}

const base = normalizeBase(process.env.BASE_PATH || '/');

export default defineConfig({
  output: 'static',
  build: { assets: 'astro' },
  base,
  site: process.env.SITE_URL || 'https://mala-subdistrict-kalolsavam.pages.dev',
});
