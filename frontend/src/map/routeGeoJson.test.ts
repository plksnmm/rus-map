import { describe, expect, it } from 'vitest'
import { routeLineToGeoJson, routeStopsToGeoJson } from './routeGeoJson'

const places = [
  { id: 'first', title: 'Первая', latitude: 57.6, longitude: 39.84 },
  { id: 'second', title: 'Вторая', latitude: 57.61, longitude: 39.83 },
]

describe('route GeoJSON', () => {
  it('keeps the curated stop order in the route line', () => {
    expect(routeLineToGeoJson(places).features[0]?.geometry.coordinates).toEqual([
      [39.84, 57.6],
      [39.83, 57.61],
    ])
  })

  it('numbers route stops from one', () => {
    expect(routeStopsToGeoJson(places).features.map((feature) => feature.properties)).toEqual([
      { id: 'first', title: 'Первая', order: '1' },
      { id: 'second', title: 'Вторая', order: '2' },
    ])
  })

  it('does not draw a misleading line for fewer than two stops', () => {
    expect(routeLineToGeoJson(places.slice(0, 1)).features).toEqual([])
  })
})
