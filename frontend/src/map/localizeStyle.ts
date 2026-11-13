import type { Map } from 'maplibre-gl'

const REGION_BOUNDARY_LAYER_ID = 'boundary_state'
const REGION_BOUNDARY_COLOR = '#223330'
const MAP_INK_COLOR = '#081919'
const MAP_DARK_COLOR = '#223330'
const MAP_MID_COLOR = '#4d524b'
const MAP_LIGHT_COLOR = '#837f78'
const MAP_PAPER_COLOR = '#f0efed'
const MAP_LAND_COLOR = '#e5e4d5'
const MAP_WATER_COLOR = '#b5c7c4'
const MAP_PARK_COLOR = '#c5cfb5'
const MAP_WOOD_COLOR = '#aebc9f'
const MAP_SETTLEMENT_COLOR = '#ddd9cf'

const BASE_MAP_PAINT_OVERRIDES: Record<
  string,
  Record<string, string>
> = {
  background: { 'background-color': MAP_LAND_COLOR },
  park: { 'fill-color': MAP_PARK_COLOR },
  water: { 'fill-color': MAP_WATER_COLOR },
  landcover_ice_shelf: { 'fill-color': MAP_PAPER_COLOR },
  landcover_glacier: { 'fill-color': MAP_PAPER_COLOR },
  landuse_residential: { 'fill-color': MAP_SETTLEMENT_COLOR },
  landcover_wood: { 'fill-color': MAP_WOOD_COLOR },
  building: {
    'fill-color': 'rgba(77, 82, 75, 0.2)',
    'fill-outline-color': 'rgba(77, 82, 75, 0.5)',
  },
  aeroway_area: { 'fill-color': 'rgba(131, 127, 120, 0.22)' },
  road_area_pier: { 'fill-color': MAP_PAPER_COLOR },
  waterway: { 'line-color': 'rgba(77, 82, 75, 0.65)' },
  tunnel_motorway_casing: { 'line-color': MAP_LIGHT_COLOR },
  tunnel_motorway_inner: { 'line-color': MAP_PAPER_COLOR },
  'aeroway-taxiway': { 'line-color': 'rgba(77, 82, 75, 0.45)' },
  'aeroway-runway-casing': { 'line-color': MAP_LIGHT_COLOR },
  'aeroway-runway': { 'line-color': MAP_PAPER_COLOR },
  road_pier: { 'line-color': MAP_PAPER_COLOR },
  highway_path: { 'line-color': 'rgba(77, 82, 75, 0.55)' },
  highway_minor: { 'line-color': 'rgba(77, 82, 75, 0.42)' },
  highway_major_casing: { 'line-color': MAP_MID_COLOR },
  highway_major_inner: { 'line-color': MAP_PAPER_COLOR },
  highway_major_subtle: { 'line-color': 'rgba(77, 82, 75, 0.5)' },
  highway_motorway_casing: { 'line-color': MAP_DARK_COLOR },
  highway_motorway_inner: { 'line-color': MAP_PAPER_COLOR },
  highway_motorway_subtle: { 'line-color': 'rgba(34, 51, 48, 0.35)' },
  railway_transit: { 'line-color': MAP_MID_COLOR },
  railway_transit_dashline: { 'line-color': MAP_PAPER_COLOR },
  railway_service: { 'line-color': MAP_MID_COLOR },
  railway_service_dashline: { 'line-color': MAP_PAPER_COLOR },
  railway: { 'line-color': MAP_MID_COLOR },
  railway_dashline: { 'line-color': MAP_PAPER_COLOR },
  highway_motorway_bridge_casing: { 'line-color': MAP_DARK_COLOR },
  highway_motorway_bridge_inner: { 'line-color': MAP_PAPER_COLOR },
  boundary_3: { 'line-color': REGION_BOUNDARY_COLOR },
  boundary_2: { 'line-color': REGION_BOUNDARY_COLOR },
  boundary_disputed: { 'line-color': REGION_BOUNDARY_COLOR },
}

const RUSSIAN_NAME_EXPRESSION: [
  'coalesce',
  ['get', 'name:ru'],
  ['get', 'name:nonlatin'],
  ['get', 'name'],
] = [
  'coalesce',
  ['get', 'name:ru'],
  ['get', 'name:nonlatin'],
  ['get', 'name'],
]

export function localizeMapLabels(map: Map) {
  for (const layer of map.getStyle().layers) {
    if (layer.type !== 'symbol') {
      continue
    }

    const textField = layer.layout?.['text-field']

    if (!textField || !JSON.stringify(textField).includes('name')) {
      continue
    }

    map.setLayoutProperty(layer.id, 'text-field', RUSSIAN_NAME_EXPRESSION)
  }
}

export function recolorBaseMap(map: Map) {
  const layers = map.getStyle().layers
  const availableLayerIds = new Set(layers.map((layer) => layer.id))

  for (const [layerId, properties] of Object.entries(
    BASE_MAP_PAINT_OVERRIDES,
  )) {
    if (!availableLayerIds.has(layerId)) {
      continue
    }

    for (const [property, value] of Object.entries(properties)) {
      map.setPaintProperty(
        layerId,
        property as Parameters<Map['setPaintProperty']>[1],
        value,
      )
    }
  }

  for (const layer of layers) {
    if (layer.type !== 'symbol' || !layer.layout?.['text-field']) {
      continue
    }

    const textColor = layer.id.includes('water')
      ? MAP_DARK_COLOR
      : MAP_INK_COLOR
    map.setPaintProperty(layer.id, 'text-color', textColor)
    map.setPaintProperty(layer.id, 'text-halo-color', MAP_PAPER_COLOR)
    map.setPaintProperty(layer.id, 'text-halo-width', 1.25)
  }
}

export function emphasizeRegionBoundaries(map: Map) {
  const hasRegionBoundaryLayer = map
    .getStyle()
    .layers.some((layer) => layer.id === REGION_BOUNDARY_LAYER_ID)

  if (!hasRegionBoundaryLayer) {
    return
  }

  map.setPaintProperty(
    REGION_BOUNDARY_LAYER_ID,
    'line-color',
    REGION_BOUNDARY_COLOR,
  )
  map.setPaintProperty(REGION_BOUNDARY_LAYER_ID, 'line-opacity', 0.72)
}
