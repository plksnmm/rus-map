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

export interface PlaceDetail extends PlaceSummary {
  description: string | null
  created_at: string
  updated_at: string
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

function isPlaceDetail(value: unknown): value is PlaceDetail {
  return (
    isRecord(value) &&
    isPlaceSummary(value) &&
    (typeof value.description === 'string' || value.description === null) &&
    typeof value.created_at === 'string' &&
    typeof value.updated_at === 'string'
  )
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    throw new Error('API мест вернул некорректный JSON')
  }
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

  const payload = await readJson(response)

  if (!isPlaceListResponse(payload)) {
    throw new Error('API мест вернул данные неожиданного формата')
  }

  return payload
}

export async function fetchPlace(
  placeId: string,
  signal?: AbortSignal,
): Promise<PlaceDetail> {
  const response = await fetch(`${placesApiUrl}/${encodeURIComponent(placeId)}`, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new Error(`Не удалось загрузить место: HTTP ${response.status}`)
  }

  const payload = await readJson(response)

  if (!isPlaceDetail(payload)) {
    throw new Error('API места вернул данные неожиданного формата')
  }

  return payload
}
