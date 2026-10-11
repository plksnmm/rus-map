import { describe, expect, it } from 'vitest'
import { curatedRoutes } from '../data/curatedRoutes'
import {
  decodePolyline6,
  decodeRoutePath,
  routeLineToGeoJson,
  routeStopsToGeoJson,
} from './routeGeoJson'

const places = [
  { id: 'first', title: 'Первая', latitude: 57.6, longitude: 39.84 },
  { id: 'second', title: 'Вторая', latitude: 57.61, longitude: 39.83 },
]

describe('route GeoJSON', () => {
  it('draws the supplied pedestrian path instead of straight stop connections', () => {
    expect(
      routeLineToGeoJson([
        [39.84, 57.6],
        [39.835, 57.605],
        [39.83, 57.61],
      ]).features[0]?.geometry.coordinates,
    ).toEqual([
      [39.84, 57.6],
      [39.835, 57.605],
      [39.83, 57.61],
    ])
  })

  it('decodes and joins the reviewed Yaroslavl pedestrian segments', () => {
    const path = decodeRoutePath(curatedRoutes[0].pathSegments)

    expect(path.length).toBeGreaterThan(50)
    expect(path[0][0]).toBeCloseTo(39.843852, 5)
    expect(path[0][1]).toBeCloseTo(57.602413, 5)
    expect(path.at(-1)?.[0]).toBeCloseTo(39.830369, 5)
    expect(path.at(-1)?.[1]).toBeCloseTo(57.611738, 5)
    expect(Math.min(...path.map(([longitude]) => longitude))).toBeLessThan(39.83)
  })

  it('rejects a truncated encoded path', () => {
    expect(() => decodePolyline6('_')).toThrow('Некорректная геометрия')
  })

  it('numbers route stops from one', () => {
    expect(routeStopsToGeoJson(places).features.map((feature) => feature.properties)).toEqual([
      { id: 'first', title: 'Первая', order: '1' },
      { id: 'second', title: 'Вторая', order: '2' },
    ])
  })

  it('does not draw a misleading line for fewer than two stops', () => {
    expect(routeLineToGeoJson([[39.84, 57.6]]).features).toEqual([])
  })
})
