import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve, join, relative } from 'node:path';

const distDir = resolve('dist');
const pkg = JSON.parse(readFileSync('package.json', 'utf8'));

function walk(dir, acc = []) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else acc.push(p);
  }
  return acc;
}

const critical = walk(distDir).filter((p) => {
  const rel = relative(distDir, p).replace(/\\/g, '/');
  if (rel === 'sw.js') return false;
  if (rel.startsWith('astro/')) return true;
  if (rel.startsWith('assets/')) return true;
  if (rel.startsWith('dashboard/')) return true;
  if (rel.endsWith('.html')) return true;
  return false;
}).sort();

const h = createHash('sha256');
for (const p of critical) {
  h.update(relative(distDir, p).replace(/\\/g, '/'));
  h.update(readFileSync(p));
}
const buildId = `${pkg.version}-${h.digest('hex').slice(0, 10)}`;

const swPath = join(distDir, 'sw.js');
let sw = readFileSync(swPath, 'utf8');
if (!sw.includes('__SW_BUILD__')) {
  console.warn('[stamp-sw] WARN: __SW_BUILD__ placeholder missing from dist/sw.js');
} else {
  sw = sw.replace(/__SW_BUILD__/g, buildId);
  writeFileSync(swPath, sw);
  console.log(`[stamp-sw] SW cache build id: ${buildId} (${critical.length} files hashed)`);
}
