import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchPlace, fetchPlaces } from './places'

const validPayload = {
  items: [
    {
      id: 'db21fe63-a06c-49de-8762-70cbe9c51601',
      title: 'Завод «Красный богатырь»',
      latitude: 55.811,
      longitude: 37.691,
    },
  ],
  total: 1,
}

function responseWith(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(payload),
  } as unknown as Response
}

afterEach(() => vi.unstubAllGlobals())

describe('fetchPlaces', () => {
  it('loads a typed list of places', async () => {
    const fetchMock = vi.fn().mockResolvedValue(responseWith(validPayload))
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchPlaces()).resolves.toEqual(validPayload)
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/places', {
      headers: { Accept: 'application/json' },
      signal: undefined,
    })
  })

  it('reports an unsuccessful HTTP response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseWith({}, 503)))

    await expect(fetchPlaces()).rejects.toThrow(
      'Не удалось загрузить места: HTTP 503',
    )
  })

  it('rejects a response with invalid coordinates', async () => {
    const invalidPayload = {
      ...validPayload,
      items: [{ ...validPayload.items[0], latitude: 100 }],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responseWith(invalidPayload)),
    )

    await expect(fetchPlaces()).rejects.toThrow(
      'API мест вернул данные неожиданного формата',
    )
  })
})

describe('fetchPlace', () => {
  it('loads and validates complete place details', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const place = {
      id: 'e2457cad-b0e2-45b4-8e76-81e09b3d1fed',
      title: 'Сысертский электротехнический завод',
      description: 'Советское предприятие в исторических корпусах.',
      latitude: 56.494711,
      longitude: 60.809612,
      created_at: '2026-09-03T20:22:56.888798Z',
      updated_at: '2026-09-03T20:29:00Z',
    }
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(place), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(fetchPlace(place.id)).resolves.toEqual(place)
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/places/${place.id}`,
      expect.objectContaining({ headers: { Accept: 'application/json' } }),
    )
  })

  it('rejects an incomplete detail response', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'e2457cad-b0e2-45b4-8e76-81e09b3d1fed',
          title: 'Сысертский электротехнический завод',
          latitude: 56.494711,
          longitude: 60.809612,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(fetchPlace('missing-fields')).rejects.toThrow(
      'данные неожиданного формата',
    )
  })
})
