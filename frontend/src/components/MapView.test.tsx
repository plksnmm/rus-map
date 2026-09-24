import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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
    fitBounds: vi.fn(),
    flyTo: vi.fn(),
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
  beforeEach(() => {
    vi.clearAllMocks()
    mapLibreMock.handlers.clear()
  })

  it('adds a places layer and opens a titled popup on marker click', () => {
    const onSelectPlace = vi.fn()
    const place = {
      id: 'db21fe63-a06c-49de-8762-70cbe9c51601',
      title: 'Завод «Красный богатырь»',
      latitude: 55.811,
      longitude: 37.691,
    }

    const { unmount } = render(
      <MapView places={[place]} onSelectPlace={onSelectPlace} />,
    )

    expect(mapLibreMock.mapOptions.current).toEqual(
      expect.objectContaining({
        center: [94, 64],
        minZoom: 2,
        renderWorldCopies: false,
        style: 'https://tiles.openfreemap.org/styles/positron',
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
    expect(mapLibreMock.map.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'submission-location-marker',
        source: 'submission-location',
        type: 'circle',
      }),
    )

    mapLibreMock.handlers.get('click:places-markers')?.({
      features: [{ properties: { id: place.id, title: place.title } }],
      lngLat: { lng: place.longitude, lat: place.latitude },
    })

    expect(onSelectPlace).toHaveBeenCalledWith(place.id)
    expect(mapLibreMock.popup.setText).toHaveBeenCalledWith(place.title)
    expect(mapLibreMock.popup.addTo).toHaveBeenCalledWith(mapLibreMock.map)

    unmount()
    expect(mapLibreMock.map.remove).toHaveBeenCalledOnce()
  })

  it('returns clicked coordinates while selecting a proposed place', () => {
    const onSelectLocation = vi.fn()
    const { unmount } = render(
      <MapView
        places={[]}
        onSelectPlace={vi.fn()}
        isSelectingLocation
        onSelectLocation={onSelectLocation}
      />,
    )

    mapLibreMock.handlers.get('click')?.({
      lngLat: { lng: 60.809612, lat: 56.494711 },
    })

    expect(onSelectLocation).toHaveBeenCalledWith({
      latitude: 56.494711,
      longitude: 60.809612,
    })
    expect(mapLibreMock.map.getCanvas().style.cursor).toBe('crosshair')
    unmount()
  })

  it('frames a location found by address search', () => {
    const { unmount } = render(
      <MapView
        places={[]}
        onSelectPlace={vi.fn()}
        isSelectingLocation
        selectedLocation={{ latitude: 55.7433, longitude: 37.803 }}
        focusLocation={{
          display_name: 'Перовская улица, 66, Москва, Россия',
          latitude: 55.7433,
          longitude: 37.803,
          bounding_box: [55.742, 55.744, 37.802, 37.804],
        }}
        onSelectLocation={vi.fn()}
      />,
    )

    expect(mapLibreMock.map.fitBounds).toHaveBeenCalledWith(
      [
        [37.802, 55.742],
        [37.804, 55.744],
      ],
      { padding: 72, maxZoom: 16, duration: 700 },
    )
    unmount()
  })
})
