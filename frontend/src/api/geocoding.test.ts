import { afterEach, describe, expect, it, vi } from 'vitest'
import { GeocodingApiError, searchAddress } from './geocoding'

describe('geocoding API', () => {
  afterEach(() => vi.restoreAllMocks())

  it('searches an encoded address and validates results', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              display_name: 'Перовская улица, 66, Москва, Россия',
              latitude: 55.7433,
              longitude: 37.803,
              bounding_box: [55.742, 55.744, 37.802, 37.804],
            },
          ],
          attribution: '© OpenStreetMap contributors',
          attribution_url: 'https://www.openstreetmap.org/copyright',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(searchAddress(' Москва, Перовская улица, 66 ')).resolves.toEqual(
      expect.objectContaining({ items: [expect.objectContaining({ latitude: 55.7433 })] }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/geocoding/search?q=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C+%D0%9F%D0%B5%D1%80%D0%BE%D0%B2%D1%81%D0%BA%D0%B0%D1%8F+%D1%83%D0%BB%D0%B8%D1%86%D0%B0%2C+66',
      expect.objectContaining({ headers: { Accept: 'application/json' } }),
    )
  })

  it('exposes provider throttling', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 429 }))

    await expect(searchAddress('Москва')).rejects.toEqual(
      expect.objectContaining<Partial<GeocodingApiError>>({ status: 429 }),
    )
  })
})
