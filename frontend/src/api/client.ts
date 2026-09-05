const baseUrl = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '');

export async function checkService(signal: AbortSignal): Promise<void> {
  const response = await fetch(`${baseUrl}/health/ready`, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error('No se pudo conectar con el servicio.');
  const body = await response.json();
  if (body.status !== 'ok' || body.database !== 'ok') throw new Error('El servicio no está disponible.');
}

