// In-flight deduplication only. Never cache forecast data across refreshes.
const pending = new Map()

export function fetchPublicText(name) {
  if (!/^[a-z0-9_-]+\.(?:csv|json)$/i.test(name)) {
    return Promise.reject(new Error('Invalid public-data filename'))
  }
  const existing = pending.get(name)
  if (existing) return existing
  const request = fetch(`${import.meta.env.BASE_URL}data/${name}`, {cache:'no-store'})
    .then(response => {
      if (!response.ok) throw new Error(`Public data unavailable: ${name} (${response.status})`)
      return response.text()
    })
    .finally(() => pending.delete(name))
  pending.set(name, request)
  return request
}
