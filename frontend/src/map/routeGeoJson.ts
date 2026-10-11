import type { PlaceSummary } from '../api/places'

export function routeLineToGeoJson(places: PlaceSummary[]) {
  return {
    type: 'FeatureCollection' as const,
    features:
      places.length >= 2
        ? [
            {
              type: 'Feature' as const,
              properties: {},
              geometry: {
                type: 'LineString' as const,
                coordinates: places.map(
                  (place) => [place.longitude, place.latitude] as [number, number],
                ),
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
