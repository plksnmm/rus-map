export const PLACE_MARKER_KINDS = [
  'active-protest',
  'ended-protest',
  'working-factory',
  'destroyed-factory',
] as const

export type PlaceMarkerKind = (typeof PLACE_MARKER_KINDS)[number]

const PLACE_MARKER_KIND_BY_ID: Record<string, PlaceMarkerKind> = {
  '0d332342-352e-4056-a682-fba4033756b6': 'destroyed-factory',
  '0b6c3e44-ca0f-55b3-a54b-25756e3dc03e': 'active-protest',
  '26bfa8c5-e320-4c19-8c5a-93f647101bd4': 'destroyed-factory',
  '5fc2e406-ddd7-578f-aa20-186e6bbe8d1d': 'active-protest',
  '65687e47-08a0-5efc-b07c-2af0ded59424': 'active-protest',
  '71cd30a1-b2a7-5c2e-bca6-e9cc3d654d3c': 'destroyed-factory',
  '740f3d9b-ea79-5adc-ab54-84663ad29ed5': 'active-protest',
  '854cc672-1f90-53fe-a9da-9a6d715d73a4': 'destroyed-factory',
  'a4e5d685-2aef-4cf8-b2c6-51bbfe7b2aaf': 'destroyed-factory',
  'b4880ed8-e7bd-5093-9814-370afe4920f6': 'destroyed-factory',
  'ca440df3-adb8-5343-98c4-7683a49bebef': 'destroyed-factory',
  'da9c2fd1-a194-5ad8-bb55-883cf4424640': 'destroyed-factory',
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
