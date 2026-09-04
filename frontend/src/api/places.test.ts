import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  fetchPlace,
  fetchPlaceMaterials,
  fetchPlaces,
  placeImageUrl,
} from './places'

describe('placeImageUrl', () => {
  it('encodes the place and media identifiers', () => {
    expect(placeImageUrl('place/id', 'media id')).toBe(
      '/api/v1/places/place%2Fid/images/media%20id',
    )
  })
})

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

describe('fetchPlaceMaterials', () => {
  it('loads and validates text and linked materials', async () => {
    const payload = {
      items: [
        {
          id: '7e3e79ea-59c6-4a85-acb2-4289e77677ec',
          type: 'text',
          title: 'История завода',
          source: 'Русь пролетарская',
          revision: {
            revision_number: 2,
            content: 'Новая опубликованная редакция.',
            url: null,
            media_id: null,
            created_at: '2026-09-04T09:00:00Z',
          },
          created_at: '2026-09-04T08:00:00Z',
          updated_at: '2026-09-04T09:00:00Z',
        },
        {
          id: 'a1358ae4-5a50-4f2b-bfad-ae652c288409',
          type: 'video',
          title: 'Видеорепортаж',
          source: null,
          revision: {
            revision_number: 1,
            content: null,
            url: 'https://example.com/video',
            media_id: null,
            created_at: '2026-09-04T10:00:00Z',
          },
          created_at: '2026-09-04T10:00:00Z',
          updated_at: '2026-09-04T10:00:00Z',
        },
      ],
      total: 2,
    }
    const fetchMock = vi.fn().mockResolvedValue(responseWith(payload))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      fetchPlaceMaterials('place/id with spaces'),
    ).resolves.toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/places/place%2Fid%20with%20spaces/materials',
      {
        headers: { Accept: 'application/json' },
        signal: undefined,
      },
    )
  })

  it('rejects unsafe material URLs', async () => {
    const payload = {
      items: [
        {
          id: 'a1358ae4-5a50-4f2b-bfad-ae652c288409',
          type: 'external_link',
          title: 'Опасная ссылка',
          source: null,
          revision: {
            revision_number: 1,
            content: null,
            url: 'javascript:alert(1)',
            media_id: null,
            created_at: '2026-09-04T10:00:00Z',
          },
          created_at: '2026-09-04T10:00:00Z',
          updated_at: '2026-09-04T10:00:00Z',
        },
      ],
      total: 1,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseWith(payload)))

    await expect(fetchPlaceMaterials('place-id')).rejects.toThrow(
      'API материалов вернул данные неожиданного формата',
    )
  })

  it('reports an unsuccessful materials response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseWith({}, 502)))

    await expect(fetchPlaceMaterials('place-id')).rejects.toThrow(
      'Не удалось загрузить материалы места: HTTP 502',
    )
  })
})
