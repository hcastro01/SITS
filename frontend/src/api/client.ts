const baseUrl = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '');
export const SESSION_EXPIRED_EVENT = 'sits:session-expired';

export interface ApiErrorBody {
  ok: false;
  code: string;
  message: string;
  correlationId: string;
}

/** Error tipado del backend: {ok, code, message, correlationId} (ver app/core/errors.py). */
export class HttpError extends Error {
  status: number;
  code: string;
  correlationId: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.correlationId = body.correlationId;
  }
}

function notifySessionExpired(status: number): void {
  if (status === 401) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    credentials: 'include', // la sesión viaja en una cookie HttpOnly.
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    notifySessionExpired(response.status);
    let body: ApiErrorBody;
    try {
      body = await response.json();
    } catch {
      body = { ok: false, code: `HTTP_${response.status}`, message: response.statusText, correlationId: '' };
    }
    throw new HttpError(response.status, body);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' });
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined });
}

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined });
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined });
}

/** Multipart: no fija Content-Type, el navegador agrega el boundary. */
export async function postForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { method: 'POST', credentials: 'include', body: formData });
  if (!response.ok) {
    notifySessionExpired(response.status);
    let body: ApiErrorBody;
    try {
      body = await response.json();
    } catch {
      body = { ok: false, code: `HTTP_${response.status}`, message: response.statusText, correlationId: '' };
    }
    throw new HttpError(response.status, body);
  }
  return (await response.json()) as T;
}

/** URL absoluta para enlaces de descarga (la cookie de sesión viaja con la navegación normal). */
export function fileUrl(path: string): string {
  return `${baseUrl}${path}`;
}

/** Para respuestas que no son JSON (p. ej. CSV de exportación). */
export async function postForBlob(path: string, body?: unknown): Promise<Blob> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    notifySessionExpired(response.status);
    let apiError: ApiErrorBody;
    try {
      apiError = await response.json();
    } catch {
      apiError = { ok: false, code: `HTTP_${response.status}`, message: response.statusText, correlationId: '' };
    }
    throw new HttpError(response.status, apiError);
  }
  return response.blob();
}

export async function checkService(signal: AbortSignal): Promise<void> {
  const response = await fetch(`${baseUrl}/health/ready`, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error('No se pudo conectar con el servicio.');
  const body = await response.json();
  if (body.status !== 'ok' || body.database !== 'ok') throw new Error('El servicio no está disponible.');
}
