import type { PlaceSummary } from '../api/places'

export type RouteCoordinate = readonly [longitude: number, latitude: number]

export function decodePolyline6(encoded: string): RouteCoordinate[] {
  const coordinates: RouteCoordinate[] = []
  let index = 0
  let latitude = 0
  let longitude = 0

  const decodeValue = () => {
    let result = 0
    let shift = 0
    let byte: number
    do {
      if (index >= encoded.length) {
        throw new Error('Некорректная геометрия маршрута')
      }
      byte = encoded.charCodeAt(index) - 63
      index += 1
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)
    return result & 1 ? ~(result >> 1) : result >> 1
  }

  while (index < encoded.length) {
    latitude += decodeValue()
    longitude += decodeValue()
    coordinates.push([longitude / 1_000_000, latitude / 1_000_000])
  }

  return coordinates
}

export function decodeRoutePath(
  encodedSegments: readonly string[],
): RouteCoordinate[] {
  return encodedSegments.flatMap((segment, index) => {
    const coordinates = decodePolyline6(segment)
    return index === 0 ? coordinates : coordinates.slice(1)
  })
}

export function routeLineToGeoJson(coordinates: readonly RouteCoordinate[]) {
  return {
    type: 'FeatureCollection' as const,
    features:
      coordinates.length >= 2
        ? [
            {
              type: 'Feature' as const,
              properties: {},
              geometry: {
                type: 'LineString' as const,
                coordinates,
              },
            },
          ]
        : [],
  }
}

export function routeStopsToGeoJson(places: PlaceSummary[]) {
  return {
    type: 'FeatureCollection' as const,
    features: places.map((place, index) => ({
      type: 'Feature' as const,
      properties: {
        id: place.id,
        title: place.title,
        order: String(index + 1),
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [place.longitude, place.latitude] as [number, number],
      },
    })),
  }
}
