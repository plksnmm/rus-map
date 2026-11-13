import type { PlaceSummary } from '../api/places'
import { getPlaceMarkerKind, type PlaceMarkerKind } from './placeMarkerKinds'

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
    markerKind: PlaceMarkerKind | null
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
        markerKind: getPlaceMarkerKind(place.id),
      },
    })),
  }
}
