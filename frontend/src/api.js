const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function searchCities(query) {
  const url = new URL('/api/cities', BASE_URL)
  if (query) url.searchParams.set('q', query)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to search cities: ${res.status}`)
  return res.json()
}

export async function searchLanguages(query) {
  const url = new URL('/api/languages', BASE_URL)
  if (query) url.searchParams.set('q', query)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to search languages: ${res.status}`)
  return res.json()
}

export async function translateUI(language) {
  const res = await fetch(new URL('/api/translate-ui', BASE_URL), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ language }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? `UI translation request failed: ${res.status}`)
  }
  return res.json()
}

export async function createChart({ calendar, date, time, cityId, name }) {
  const res = await fetch(new URL('/api/chart', BASE_URL), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ calendar, date, time, city_id: cityId, name: name || null }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? `Chart request failed: ${res.status}`)
  }
  return res.json()
}

export async function getConfig() {
  const res = await fetch(new URL('/api/config', BASE_URL))
  if (!res.ok) throw new Error(`Failed to load config: ${res.status}`)
  return res.json()
}

export async function chatWithChart({ shareId, message, history }) {
  const res = await fetch(new URL(`/api/chart/${shareId}/chat`, BASE_URL), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? `Chat request failed: ${res.status}`)
  }
  return res.json()
}

export async function downloadChartPdf({ shareId, language }) {
  const url = new URL(`/api/chart/${shareId}/pdf`, BASE_URL)
  url.searchParams.set('language', language)
  const res = await fetch(url)
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? `PDF request failed: ${res.status}`)
  }
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = `astrotruth-${shareId}.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

// Consumes the /api/interpret SSE stream. Server sends either bare
// `data: {...}` chunks (event type defaults to "message") or a named
// `event: error` / `event: done` block. Buffers partial reads across the
// `\n\n` event delimiter since fetch chunks don't align with SSE events.
export async function streamInterpretation({ shareId, language, onChunk, onDone, onError, signal }) {
  let res
  try {
    res = await fetch(new URL('/api/interpret', BASE_URL), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ share_id: shareId, language }),
      signal,
    })
  } catch (err) {
    onError(err)
    return
  }

  if (!res.ok || !res.body) {
    onError(new Error(`Interpretation request failed: ${res.status}`))
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let sepIndex
      while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex)
        buffer = buffer.slice(sepIndex + 2)

        let eventType = 'message'
        let dataLine = ''
        for (const line of rawEvent.split('\n')) {
          if (line.startsWith('event:')) eventType = line.slice(6).trim()
          else if (line.startsWith('data:')) dataLine = line.slice(5).trim()
        }
        if (!dataLine) continue
        const payload = JSON.parse(dataLine)

        if (eventType === 'error') {
          onError(new Error(payload.message || 'Interpretation failed'))
          return
        }
        if (eventType === 'done') {
          onDone()
          return
        }
        onChunk(payload.text ?? '')
      }
    }
  } catch (err) {
    onError(err)
    return
  }

  onDone()
}
