import type { Map } from 'maplibre-gl'
import { describe, expect, it, vi } from 'vitest'
import {
  emphasizeRegionBoundaries,
  localizeMapLabels,
  recolorBaseMap,
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
      '#223330',
    )
    expect(map.setPaintProperty).toHaveBeenCalledWith(
      'boundary_state',
      'line-opacity',
      0.72,
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

describe('recolorBaseMap', () => {
  it('applies the project palette to available base and label layers', () => {
    const setPaintProperty = vi.fn()
    const map = {
      getStyle: () => ({
        layers: [
          { id: 'background', type: 'background' },
          { id: 'water', type: 'fill' },
          { id: 'highway_major_casing', type: 'line' },
          {
            id: 'label_city',
            type: 'symbol',
            layout: { 'text-field': ['get', 'name'] },
          },
          {
            id: 'water_name_point_label',
            type: 'symbol',
            layout: { 'text-field': ['get', 'name'] },
          },
        ],
      }),
      setPaintProperty,
    } as unknown as Map

    recolorBaseMap(map)

    expect(setPaintProperty).toHaveBeenCalledWith(
      'background',
      'background-color',
      '#e5e4d5',
    )
    expect(setPaintProperty).toHaveBeenCalledWith(
      'water',
      'fill-color',
      '#b5c7c4',
    )
    expect(setPaintProperty).toHaveBeenCalledWith(
      'highway_major_casing',
      'line-color',
      '#4d524b',
    )
    expect(setPaintProperty).toHaveBeenCalledWith(
      'label_city',
      'text-color',
      '#081919',
    )
    expect(setPaintProperty).toHaveBeenCalledWith(
      'water_name_point_label',
      'text-color',
      '#223330',
    )
    expect(setPaintProperty).toHaveBeenCalledWith(
      'label_city',
      'text-halo-color',
      '#f0efed',
    )
  })
})
