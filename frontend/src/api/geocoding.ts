export interface GeocodingResult {
  display_name: string
  latitude: number
  longitude: number
  bounding_box: [number, number, number, number] | null
}

export interface GeocodingSearchResponse {
  items: GeocodingResult[]
  attribution: string
  attribution_url: string
}

export class GeocodingApiError extends Error {
  status: number

  constructor(status: number) {
    super(`Не удалось найти адрес: HTTP ${status}`)
    this.name = 'GeocodingApiError'
    this.status = status
  }
}

const geocodingApiUrl = `${import.meta.env.BASE_URL}api/v1/geocoding/search`

function isResult(value: unknown): value is GeocodingResult {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const result = value as Record<string, unknown>
  return (
    typeof result.display_name === 'string' &&
    typeof result.latitude === 'number' &&
    typeof result.longitude === 'number' &&
    (result.bounding_box === null ||
      (Array.isArray(result.bounding_box) &&
        result.bounding_box.length === 4 &&
        result.bounding_box.every((part) => typeof part === 'number')))
  )
}

export async function searchAddress(
  query: string,
  signal?: AbortSignal,
): Promise<GeocodingSearchResponse> {
  const search = new URLSearchParams({ q: query.trim() })
  const response = await fetch(`${geocodingApiUrl}?${search.toString()}`, {
    headers: { Accept: 'application/json' },
    signal,
  })
  if (!response.ok) {
    throw new GeocodingApiError(response.status)
  }

  const payload: unknown = await response.json()
  if (typeof payload !== 'object' || payload === null) {
    throw new Error('Сервер вернул неожиданный ответ')
  }
  const record = payload as Record<string, unknown>
  if (
    !Array.isArray(record.items) ||
    !record.items.every(isResult) ||
    typeof record.attribution !== 'string' ||
    typeof record.attribution_url !== 'string'
  ) {
    throw new Error('Сервер вернул неожиданный ответ')
  }
  return payload as GeocodingSearchResponse
}
