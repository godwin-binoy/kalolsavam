import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

const base = process.env.BASE_PATH || '/';

export default defineConfig({
  output: 'static',
  base,
  site: process.env.SITE_URL || 'https://kalolsavam.example.com',
  vite: { plugins: [tailwindcss()] },
});
