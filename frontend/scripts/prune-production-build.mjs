import { rm, readdir, readFile, stat } from 'node:fs/promises';
import { basename, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const build = join(root, 'build');

async function removePath(path) {
  await rm(path, { recursive: true, force: true });
}

async function collectReferencedAudio() {
  const manifestPath = join(build, 'assets', 'audio', 'manifest.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const referenced = new Set(['manifest.json']);
  for (const group of [manifest.music, manifest.sfx]) {
    for (const item of Object.values(group ?? {})) {
      if (item?.src) referenced.add(basename(item.src));
    }
  }
  return referenced;
}

async function pruneUnusedAudio() {
  const audioDir = join(build, 'assets', 'audio');
  const referenced = await collectReferencedAudio();
  for (const file of await readdir(audioDir)) {
    const path = join(audioDir, file);
    const info = await stat(path);
    if (info.isFile() && !referenced.has(file)) await removePath(path);
  }
}

await removePath(join(build, 'books'));
await removePath(join(build, 'assets', 'source_sheets'));
await removePath(join(build, 'assets', 'screenshots'));
await pruneUnusedAudio();

