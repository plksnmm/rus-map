export interface PlaceSummary {
  id: string
  title: string
  latitude: number
  longitude: number
}

export interface PlaceListResponse {
  items: PlaceSummary[]
  total: number
}

const placesApiUrl = `${import.meta.env.BASE_URL}api/v1/places`

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isCoordinate(value: unknown, minimum: number, maximum: number) {
  return (
    typeof value === 'number' &&
    Number.isFinite(value) &&
    value >= minimum &&
    value <= maximum
  )
}

function isPlaceSummary(value: unknown): value is PlaceSummary {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.title === 'string' &&
    value.title.length > 0 &&
    isCoordinate(value.latitude, -90, 90) &&
    isCoordinate(value.longitude, -180, 180)
  )
}

function isPlaceListResponse(value: unknown): value is PlaceListResponse {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isPlaceSummary) &&
    typeof value.total === 'number' &&
    Number.isInteger(value.total) &&
    value.total >= 0
  )
}

export async function fetchPlaces(
  signal?: AbortSignal,
): Promise<PlaceListResponse> {
  const response = await fetch(placesApiUrl, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new Error(`Не удалось загрузить места: HTTP ${response.status}`)
  }

  let payload: unknown

  try {
    payload = await response.json()
  } catch {
    throw new Error('API мест вернул некорректный JSON')
  }

  if (!isPlaceListResponse(payload)) {
    throw new Error('API мест вернул данные неожиданного формата')
  }

  return payload
}
