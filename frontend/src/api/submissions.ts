export interface PlaceSubmissionPayload {
  title: string
  description: string | null
  latitude: number
  longitude: number
  address: string | null
  source_urls: string[]
  website: string
}

export interface PlaceSubmissionReceipt {
  id: string
  status: 'pending'
  created_at: string
}

export class SubmissionApiError extends Error {
  status: number

  constructor(status: number) {
    super(`Не удалось отправить заявку: HTTP ${status}`)
    this.name = 'SubmissionApiError'
    this.status = status
  }
}

const submissionsApiUrl = `${import.meta.env.BASE_URL}api/v1/submissions`

function isReceipt(value: unknown): value is PlaceSubmissionReceipt {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as Record<string, unknown>).id === 'string' &&
    (value as Record<string, unknown>).status === 'pending' &&
    typeof (value as Record<string, unknown>).created_at === 'string'
  )
}

export async function submitPlace(
  payload: PlaceSubmissionPayload,
): Promise<PlaceSubmissionReceipt> {
  const response = await fetch(submissionsApiUrl, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new SubmissionApiError(response.status)
  }

  const data: unknown = await response.json()
  if (!isReceipt(data)) {
    throw new Error('Сервер вернул неожиданный ответ')
  }
  return data
}
