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

export type MaterialType =
  | 'text'
  | 'external_link'
  | 'image'
  | 'video'
  | 'audio'

export interface MaterialRevision {
  revision_number: number
  content: string | null
  url: string | null
  created_at: string
}

export interface PlaceMaterial {
  id: string
  type: MaterialType
  title: string
  source: string | null
  revision: MaterialRevision
  created_at: string
  updated_at: string
}

export interface MaterialListResponse {
  items: PlaceMaterial[]
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

function isPlaceDetail(value: unknown): value is PlaceDetail {
  return (
    isRecord(value) &&
    isPlaceSummary(value) &&
    (typeof value.description === 'string' || value.description === null) &&
    typeof value.created_at === 'string' &&
    typeof value.updated_at === 'string'
  )
}

const materialTypes: ReadonlySet<string> = new Set([
  'text',
  'external_link',
  'image',
  'video',
  'audio',
])

export function isSafeHttpUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

function isMaterialRevision(
  value: unknown,
  materialType: MaterialType,
): value is MaterialRevision {
  if (!isRecord(value)) {
    return false
  }

  const hasContent = typeof value.content === 'string' && value.content.length > 0
  const hasSafeUrl = typeof value.url === 'string' && isSafeHttpUrl(value.url)

  return (
    Number.isInteger(value.revision_number) &&
    (value.revision_number as number) > 0 &&
    typeof value.created_at === 'string' &&
    ((materialType === 'text' && hasContent && value.url === null) ||
      (materialType !== 'text' && value.content === null && hasSafeUrl))
  )
}

function isPlaceMaterial(value: unknown): value is PlaceMaterial {
  if (
    !isRecord(value) ||
    typeof value.type !== 'string' ||
    !materialTypes.has(value.type)
  ) {
    return false
  }

  const materialType = value.type as MaterialType

  return (
    typeof value.id === 'string' &&
    typeof value.title === 'string' &&
    value.title.length > 0 &&
    (typeof value.source === 'string' || value.source === null) &&
    isMaterialRevision(value.revision, materialType) &&
    typeof value.created_at === 'string' &&
    typeof value.updated_at === 'string'
  )
}

function isMaterialListResponse(value: unknown): value is MaterialListResponse {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isPlaceMaterial) &&
    typeof value.total === 'number' &&
    Number.isInteger(value.total) &&
    value.total >= 0
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

export async function fetchPlaceMaterials(
  placeId: string,
  signal?: AbortSignal,
): Promise<MaterialListResponse> {
  const response = await fetch(
    `${placesApiUrl}/${encodeURIComponent(placeId)}/materials`,
    {
      headers: { Accept: 'application/json' },
      signal,
    },
  )

  if (!response.ok) {
    throw new Error(
      `Не удалось загрузить материалы места: HTTP ${response.status}`,
    )
  }

  const payload = await readJson(response)

  if (!isMaterialListResponse(payload)) {
    throw new Error('API материалов вернул данные неожиданного формата')
  }

  return payload
}
