import { describe, expect, it } from 'vitest'
import { placesToGeoJson } from './placesGeoJson'

describe('placesToGeoJson', () => {
  it('uses the GeoJSON longitude, latitude coordinate order', () => {
    const result = placesToGeoJson([
      {
        id: 'db21fe63-a06c-49de-8762-70cbe9c51601',
        title: 'Завод «Красный богатырь»',
        latitude: 55.811,
        longitude: 37.691,
      },
    ])

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [37.691, 55.811],
          },
          properties: {
            id: 'db21fe63-a06c-49de-8762-70cbe9c51601',
            title: 'Завод «Красный богатырь»',
          },
        },
      ],
    })
  })

  it('creates an empty feature collection for an empty list', () => {
    expect(placesToGeoJson([])).toEqual({
      type: 'FeatureCollection',
      features: [],
    })
  })
})
