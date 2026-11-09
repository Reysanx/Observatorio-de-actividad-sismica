import { writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDirectory = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outputDirectory = resolve(
  frontendDirectory,
  'dist',
  'observatorio-sismico-frontend',
  'browser',
);

function getApiUrl() {
  const configuredUrl = process.env.NGROK_API_URL?.trim();
  if (!configuredUrl) {
    throw new Error('NGROK_API_URL must be set to the HTTPS ngrok API URL.');
  }

  const apiUrl = new URL(configuredUrl);
  if (
    apiUrl.protocol !== 'https:' ||
    apiUrl.username ||
    apiUrl.password ||
    apiUrl.pathname !== '/' ||
    apiUrl.search ||
    apiUrl.hash
  ) {
    throw new Error('NGROK_API_URL must be an HTTPS origin without credentials or a path.');
  }

  return apiUrl.origin;
}

try {
  const apiUrl = getApiUrl();
  await writeFile(
    resolve(outputDirectory, 'config.json'),
    `${JSON.stringify({ apiUrl }, null, 2)}\n`,
    'utf8',
  );
  console.log('Generated Netlify runtime API configuration.');
} catch (error) {
  console.error(
    `Netlify API configuration failed: ${
      error instanceof Error ? error.message : String(error)
    }`,
  );
  process.exitCode = 1;
}
