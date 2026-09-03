import type { Map } from 'maplibre-gl'
import { describe, expect, it, vi } from 'vitest'
import {
  emphasizeRegionBoundaries,
  localizeMapLabels,
} from './localizeStyle'

describe('localizeMapLabels', () => {
  it('uses Russian names for text layers and preserves reference layers', () => {
    const setLayoutProperty = vi.fn()
    const map = {
      getStyle: () => ({
        layers: [
          {
            id: 'place-city',
            type: 'symbol',
            layout: { 'text-field': ['get', 'name'] },
          },
          {
            id: 'motorway-reference',
            type: 'symbol',
            layout: { 'text-field': ['get', 'ref'] },
          },
          { id: 'water', type: 'fill' },
        ],
      }),
      setLayoutProperty,
    } as unknown as Map

    localizeMapLabels(map)

    expect(setLayoutProperty).toHaveBeenCalledOnce()
    expect(setLayoutProperty).toHaveBeenCalledWith(
      'place-city',
      'text-field',
      [
        'coalesce',
        ['get', 'name:ru'],
        ['get', 'name:nonlatin'],
        ['get', 'name'],
      ],
    )
  })
})

describe('emphasizeRegionBoundaries', () => {
  it('makes the OpenFreeMap region boundary layer easier to see', () => {
    const map = {
      getStyle: () => ({
        layers: [{ id: 'boundary_state', type: 'line' }],
      }),
      setPaintProperty: vi.fn(),
    } as unknown as Map

    emphasizeRegionBoundaries(map)

    expect(map.setPaintProperty).toHaveBeenCalledWith(
      'boundary_state',
      'line-color',
      '#8a8d91',
    )
    expect(map.setPaintProperty).toHaveBeenCalledWith(
      'boundary_state',
      'line-opacity',
      0.9,
    )
  })

  it('does nothing when a different map style has no region layer', () => {
    const map = {
      getStyle: () => ({ layers: [] }),
      setPaintProperty: vi.fn(),
    } as unknown as Map

    emphasizeRegionBoundaries(map)

    expect(map.setPaintProperty).not.toHaveBeenCalled()
  })
})
