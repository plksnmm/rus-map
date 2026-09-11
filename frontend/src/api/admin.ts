export type SubmissionStatus = 'pending' | 'approved' | 'rejected'

export interface AdminUser {
  id: string
  username: string
}

export interface AdminLoginResponse {
  admin: AdminUser
  expires_at: string
}

export interface PlaceSubmission {
  id: string
  status: SubmissionStatus
  title: string
  description: string | null
  latitude: number
  longitude: number
  source_urls: string[]
  review_notes: string | null
  approved_place_id: string | null
  moderated_by_admin_id: string | null
  moderated_at: string | null
  created_at: string
  updated_at: string
}

export interface SubmissionListResponse {
  items: PlaceSubmission[]
  total: number
  limit: number
  offset: number
}

export class AdminApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'AdminApiError'
    this.status = status
  }
}

const adminApiUrl = `${import.meta.env.BASE_URL}api/v1/admin`
const csrfCookieName = 'rus_map_admin_csrf'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isNullableString(value: unknown): value is string | null {
  return typeof value === 'string' || value === null
}

function isAdminUser(value: unknown): value is AdminUser {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.username === 'string'
  )
}

function isSubmissionStatus(value: unknown): value is SubmissionStatus {
  return value === 'pending' || value === 'approved' || value === 'rejected'
}

function isPlaceSubmission(value: unknown): value is PlaceSubmission {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    isSubmissionStatus(value.status) &&
    typeof value.title === 'string' &&
    isNullableString(value.description) &&
    typeof value.latitude === 'number' &&
    typeof value.longitude === 'number' &&
    Array.isArray(value.source_urls) &&
    value.source_urls.every((url) => typeof url === 'string') &&
    isNullableString(value.review_notes) &&
    isNullableString(value.approved_place_id) &&
    isNullableString(value.moderated_by_admin_id) &&
    isNullableString(value.moderated_at) &&
    typeof value.created_at === 'string' &&
    typeof value.updated_at === 'string'
  )
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    throw new AdminApiError(response.status, 'Сервер вернул некорректный ответ')
  }
}

async function request(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const response = await fetch(`${adminApiUrl}${path}`, {
    ...options,
    credentials: 'same-origin',
    headers: { Accept: 'application/json', ...options.headers },
  })

  if (!response.ok) {
    throw new AdminApiError(response.status, `HTTP ${response.status}`)
  }

  return response
}

export function readCsrfToken(cookie = document.cookie): string | null {
  for (const part of cookie.split(';')) {
    const [rawName, ...rawValue] = part.trim().split('=')
    if (rawName === csrfCookieName) {
      try {
        return decodeURIComponent(rawValue.join('='))
      } catch {
        return null
      }
    }
  }
  return null
}

function csrfHeaders(): Record<string, string> {
  const token = readCsrfToken()
  if (!token) {
    throw new AdminApiError(403, 'CSRF-токен отсутствует')
  }
  return { 'X-CSRF-Token': token }
}

export async function fetchCurrentAdmin(
  signal?: AbortSignal,
): Promise<AdminUser> {
  const payload = await readJson(await request('/auth/me', { signal }))
  if (!isAdminUser(payload)) {
    throw new AdminApiError(500, 'Неожиданный формат данных администратора')
  }
  return payload
}

export async function loginAdmin(
  username: string,
  password: string,
): Promise<AdminLoginResponse> {
  const payload = await readJson(
    await request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),
  )
  if (
    !isRecord(payload) ||
    !isAdminUser(payload.admin) ||
    typeof payload.expires_at !== 'string'
  ) {
    throw new AdminApiError(500, 'Неожиданный формат ответа входа')
  }
  return payload as unknown as AdminLoginResponse
}

export async function logoutAdmin(): Promise<void> {
  await request('/auth/logout', { method: 'POST', headers: csrfHeaders() })
}

export async function fetchSubmissions(
  status: SubmissionStatus | null,
  signal?: AbortSignal,
): Promise<SubmissionListResponse> {
  const query = new URLSearchParams({ limit: '100', offset: '0' })
  if (status) {
    query.set('status', status)
  }
  const payload = await readJson(
    await request(`/submissions?${query.toString()}`, { signal }),
  )
  if (
    !isRecord(payload) ||
    !Array.isArray(payload.items) ||
    !payload.items.every(isPlaceSubmission) ||
    typeof payload.total !== 'number' ||
    typeof payload.limit !== 'number' ||
    typeof payload.offset !== 'number'
  ) {
    throw new AdminApiError(500, 'Неожиданный формат очереди заявок')
  }
  return payload as unknown as SubmissionListResponse
}

export async function moderateSubmission(
  submissionId: string,
  decision: 'approve' | 'reject',
  reviewNotes: string,
): Promise<PlaceSubmission> {
  const payload = await readJson(
    await request(
      `/submissions/${encodeURIComponent(submissionId)}/${decision}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...csrfHeaders(),
        },
        body: JSON.stringify({ review_notes: reviewNotes.trim() || null }),
      },
    ),
  )
  if (!isPlaceSubmission(payload)) {
    throw new AdminApiError(500, 'Неожиданный формат результата модерации')
  }
  return payload
}
