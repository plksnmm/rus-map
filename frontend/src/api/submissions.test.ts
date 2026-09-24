import { afterEach, describe, expect, it, vi } from 'vitest'
import { SubmissionApiError, submitPlace } from './submissions'

const payload = {
  title: 'Завод Красный богатырь',
  description: 'Историческое предприятие',
  latitude: 55.8031,
  longitude: 37.6917,
  address: 'Москва, Краснобогатырская улица',
  source_urls: ['https://example.com/factory'],
  website: '',
}

describe('submission API', () => {
  afterEach(() => vi.restoreAllMocks())

  it('posts a pending proposal to the dedicated public endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'ea261f5b-5420-4500-879d-400d6ea82a79',
          status: 'pending',
          created_at: '2026-09-13T10:00:00Z',
        }),
        { status: 202, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(submitPlace(payload)).resolves.toMatchObject({
      status: 'pending',
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/submissions',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    )
  })

  it('exposes the response status when the request is rejected', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 429 }))

    await expect(submitPlace(payload)).rejects.toEqual(
      expect.objectContaining<Partial<SubmissionApiError>>({ status: 429 }),
    )
  })
})
