import { provideHttpClient } from '@angular/common/http';
import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app';
import { API_BASE_URL } from './app/api/earthquake-api.service';

const defaultApiUrl = 'http://127.0.0.1:8000';

async function loadApiUrl(): Promise<string> {
  try {
    const response = await fetch('/config.json', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`config.json returned HTTP ${response.status}`);
    }

    const config: unknown = await response.json();
    if (
      typeof config !== 'object' ||
      config === null ||
      !('apiUrl' in config) ||
      typeof config.apiUrl !== 'string' ||
      config.apiUrl.trim() === ''
    ) {
      throw new Error('config.json must contain a non-empty apiUrl string');
    }

    return config.apiUrl.trim().replace(/\/+$/, '');
  } catch (error) {
    console.warn('No se pudo cargar config.json; se usará la API local.', error);
    return defaultApiUrl;
  }
}

void loadApiUrl().then((apiUrl) =>
  bootstrapApplication(App, {
    providers: [
      provideHttpClient(),
      { provide: API_BASE_URL, useValue: apiUrl },
    ],
  }).catch((error: unknown) => console.error('No se pudo iniciar Angular.', error)),
);
