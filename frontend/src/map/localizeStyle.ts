import type { Map } from 'maplibre-gl'

const REGION_BOUNDARY_LAYER_ID = 'boundary_state'
const REGION_BOUNDARY_COLOR = '#8a8d91'

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
  map.setPaintProperty(REGION_BOUNDARY_LAYER_ID, 'line-opacity', 0.9)
}
