import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

// The Windows layout is tried first so an existing checkout resolves exactly the
// interpreter it always did; the POSIX layouts are only reached when it is absent.
const PYTHON_CANDIDATES = [
  path.join(repoRoot, '.venv313', 'Scripts', 'python.exe'),
  path.join(repoRoot, '.venv', 'Scripts', 'python.exe'),
  path.join(repoRoot, '.venv', 'bin', 'python'),
];

function resolvePython() {
  if (process.env.SHIFTWORK_PYTHON) return process.env.SHIFTWORK_PYTHON;
  const found = PYTHON_CANDIDATES.find(candidate => existsSync(candidate));
  if (found) return found;
  throw new Error(`no project interpreter found; set SHIFTWORK_PYTHON (tried ${PYTHON_CANDIDATES.join(', ')})`);
}

export const pythonPath = resolvePython();

export const chromePath = process.env.CHROME_PATH
  ?? (process.platform === 'darwin'
    ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    : 'C:/Program Files/Google/Chrome/Application/chrome.exe');
