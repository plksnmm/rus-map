import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import MapView from './MapView'

type MapEventHandler = (event?: unknown) => void

const mapLibreMock = vi.hoisted(() => {
  const handlers = new globalThis.Map<string, MapEventHandler>()
  const mapOptions: { current?: Record<string, unknown> } = {}
  const source = { setData: vi.fn() }
  const popup = {
    setLngLat: vi.fn(),
    setText: vi.fn(),
    addTo: vi.fn(),
  }
  popup.setLngLat.mockReturnValue(popup)
  popup.setText.mockReturnValue(popup)
  popup.addTo.mockReturnValue(popup)

  const map = {
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    getSource: vi.fn().mockReturnValue(source),
    getStyle: vi.fn().mockReturnValue({ layers: [] }),
    setLayoutProperty: vi.fn(),
    getCanvas: vi.fn().mockReturnValue({ style: { cursor: '' } }),
    remove: vi.fn(),
    on: vi.fn(
      (
        eventName: string,
        layerOrHandler: string | MapEventHandler,
        layerHandler?: MapEventHandler,
      ) => {
        const key =
          typeof layerOrHandler === 'string'
            ? `${eventName}:${layerOrHandler}`
            : eventName
        const handler =
          typeof layerOrHandler === 'string' ? layerHandler : layerOrHandler

        if (handler) {
          handlers.set(key, handler)
        }

        if (eventName === 'load' && handler) {
          handler()
        }
      },
    ),
  }

  return { handlers, map, mapOptions, popup, source }
})

vi.mock('maplibre-gl', () => ({
  GeoJSONSource: vi.fn(),
  Map: class {
    constructor(options: Record<string, unknown>) {
      mapLibreMock.mapOptions.current = options
      return mapLibreMock.map
    }
  },
  NavigationControl: vi.fn(),
  Popup: class {
    constructor() {
      return mapLibreMock.popup
    }
  },
  ScaleControl: vi.fn(),
  setWorkerUrl: vi.fn(),
}))

describe('MapView', () => {
  it('adds a places layer and opens a titled popup on marker click', () => {
    const place = {
      id: 'db21fe63-a06c-49de-8762-70cbe9c51601',
      title: 'Завод «Красный богатырь»',
      latitude: 55.811,
      longitude: 37.691,
    }

    const { unmount } = render(<MapView places={[place]} />)

    expect(mapLibreMock.mapOptions.current).toEqual(
      expect.objectContaining({
        center: [94, 64],
        minZoom: 2,
        renderWorldCopies: false,
        zoom: 2.1,
      }),
    )

    expect(mapLibreMock.map.addSource).toHaveBeenCalledWith('places', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [
          expect.objectContaining({
            geometry: {
              type: 'Point',
              coordinates: [37.691, 55.811],
            },
          }),
        ],
      },
    })
    expect(mapLibreMock.map.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'places-markers',
        source: 'places',
        type: 'circle',
      }),
    )

    mapLibreMock.handlers.get('click:places-markers')?.({
      features: [{ properties: { title: place.title } }],
      lngLat: { lng: place.longitude, lat: place.latitude },
    })

    expect(mapLibreMock.popup.setText).toHaveBeenCalledWith(place.title)
    expect(mapLibreMock.popup.addTo).toHaveBeenCalledWith(mapLibreMock.map)

    unmount()
    expect(mapLibreMock.map.remove).toHaveBeenCalledOnce()
  })
})
