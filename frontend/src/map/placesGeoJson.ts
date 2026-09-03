import type { PlaceSummary } from '../api/places'

export interface PlaceFeatureCollection {
  type: 'FeatureCollection'
  features: PlaceFeature[]
}

interface PlaceFeature {
  type: 'Feature'
  geometry: {
    type: 'Point'
    coordinates: [longitude: number, latitude: number]
  }
  properties: {
    id: string
    title: string
  }
}

export function placesToGeoJson(
  places: PlaceSummary[],
): PlaceFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: places.map((place) => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [place.longitude, place.latitude],
      },
      properties: {
        id: place.id,
        title: place.title,
      },
    })),
  }
}
