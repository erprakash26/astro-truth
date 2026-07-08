const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function searchCities(query) {
  const url = new URL('/api/cities', BASE_URL)
  if (query) url.searchParams.set('q', query)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to search cities: ${res.status}`)
  return res.json()
}

export async function createChart({ calendar, date, time, cityId }) {
  const res = await fetch(new URL('/api/chart', BASE_URL), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ calendar, date, time, city_id: cityId }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? `Chart request failed: ${res.status}`)
  }
  return res.json()
}
