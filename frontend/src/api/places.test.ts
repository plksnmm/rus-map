import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchPlaces } from './places'

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
