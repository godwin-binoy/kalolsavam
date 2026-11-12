import { cpSync, existsSync, rmSync } from 'node:fs';
import { resolve } from 'node:path';

// Copy private server-side UI assets into the Astro build output.
// Add more [source, destination] pairs here as you build more private pages.
const targets = [
  ['server/dashboard', 'dist/dashboard'],
];

for (const [srcRel, destRel] of targets) {
  const src = resolve(srcRel);
  const dest = resolve(destRel);

  if (existsSync(src)) {
    if (existsSync(dest)) {
      rmSync(dest, { recursive: true, force: true });
    }
    cpSync(src, dest, { recursive: true });
    console.log(`[copy-private] Copied ${srcRel} to ${destRel}`);
  } else {
    console.warn(`[copy-private] Warning: Source directory ${srcRel} not found.`);
  }
}
