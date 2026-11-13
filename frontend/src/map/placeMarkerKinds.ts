export const PLACE_MARKER_KINDS = [
  'active-protest',
  'ended-protest',
  'working-factory',
  'destroyed-factory',
] as const

export type PlaceMarkerKind = (typeof PLACE_MARKER_KINDS)[number]

const PLACE_MARKER_KIND_BY_ID: Record<string, PlaceMarkerKind> = {
  'e2457cad-b0e2-45b4-8e76-81e09b3d1fed': 'working-factory',
  'bbe880f1-4bf5-4b49-889a-7ccab143a6dd': 'destroyed-factory',
  'c237ed0b-9c49-4afe-b455-df792a7d2d13': 'destroyed-factory',
  '2524a00d-61d2-4657-a5f9-a018130f8a7c': 'working-factory',
  '1ee1a2eb-b60f-4b31-bc7d-81afe5664724': 'ended-protest',
  '38ed1b06-8e68-4ca1-96d5-2c47baf66d78': 'working-factory',
}

export function getPlaceMarkerKind(placeId: string): PlaceMarkerKind | null {
  return PLACE_MARKER_KIND_BY_ID[placeId] ?? null
}
