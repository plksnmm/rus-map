import { useEffect, useRef } from 'react'
import {
  GeoJSONSource,
  Map,
  type MapLayerMouseEvent,
  Marker,
  NavigationControl,
  Popup,
  ScaleControl,
  setWorkerUrl,
} from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import activeProtestMarkerUrl from '../assets/map-markers/active-protest.svg?no-inline'
import destroyedFactoryMarkerUrl from '../assets/map-markers/destroyed-factory.svg?no-inline'
import endedProtestMarkerUrl from '../assets/map-markers/ended-protest.svg?no-inline'
import workingFactoryMarkerUrl from '../assets/map-markers/working-factory.svg?no-inline'
import type { GeocodingResult } from '../api/geocoding'
import type { PlaceSummary } from '../api/places'
import type { MapLocation } from './PlaceSubmissionForm'
import {
  emphasizeRegionBoundaries,
  localizeMapLabels,
  recolorBaseMap,
} from '../map/localizeStyle'
import { placesToGeoJson } from '../map/placesGeoJson'
import {
  getPlaceMarkerKind,
  type PlaceMarkerKind,
} from '../map/placeMarkerKinds'
import {
  type RouteCoordinate,
  routeLineToGeoJson,
  routeStopsToGeoJson,
} from '../map/routeGeoJson'

const INITIAL_CENTER: [number, number] = [94, 64]
const INITIAL_ZOOM = 2.1
const MIN_ZOOM = 2
const MAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'
const PLACES_SOURCE_ID = 'places'
const PLACES_LAYER_ID = 'places-markers'
const ROUTE_LINE_SOURCE_ID = 'curated-route-line'
const ROUTE_LINE_LAYER_ID = 'curated-route-line'
const ROUTE_STOPS_SOURCE_ID = 'curated-route-stops'
const ROUTE_STOPS_LAYER_ID = 'curated-route-stops'
const ROUTE_STOP_LABELS_LAYER_ID = 'curated-route-stop-labels'
const MAP_ACCENT_COLOR = '#ce1a1e'
const MAP_INK_COLOR = '#081919'
const MAP_DARK_COLOR = '#223330'
const MAP_LIGHT_COLOR = '#837f78'
const DRAFT_SOURCE_ID = 'submission-location'
const DRAFT_LAYER_ID = 'submission-location-marker'

const PLACE_MARKER_URLS: Record<PlaceMarkerKind, string> = {
  'active-protest': activeProtestMarkerUrl,
  'ended-protest': endedProtestMarkerUrl,
  'working-factory': workingFactoryMarkerUrl,
  'destroyed-factory': destroyedFactoryMarkerUrl,
}

const ACTIVE_PLACE_MARKER_KINDS: ReadonlySet<PlaceMarkerKind> = new Set([
  'active-protest',
  'working-factory',
])

const PLACE_MARKER_SIZE_STOPS = [
  [2, 24],
  [6, 34],
  [10, 50],
  [14, 69],
  [18, 88],
] as const

interface SemanticPlaceMarker {
  marker: Marker
  element: HTMLButtonElement
}

setWorkerUrl(maplibreWorkerUrl)

interface MapViewProps {
  places: PlaceSummary[]
  routePlaces?: PlaceSummary[]
  routePath?: readonly RouteCoordinate[]
  routePanelState?: 'compact' | 'half' | 'expanded'
  onSelectPlace: (placeId: string) => void
  isSelectingLocation?: boolean
  selectedLocation?: MapLocation | null
  focusLocation?: GeocodingResult | null
  onSelectLocation?: (location: MapLocation) => void
}

function routeFramePadding(
  panelState: 'compact' | 'half' | 'expanded',
): number | { top: number; right: number; bottom: number; left: number } {
  if (window.innerWidth > 575.98) {
    return 88
  }

  const panelHeight =
    panelState === 'half'
      ? Math.min(window.innerHeight * 0.52, 430)
      : 176

  return {
    top: 76,
    right: 28,
    bottom: Math.round(panelHeight + 24),
    left: 28,
  }
}

function frameRoute(
  map: Map,
  coordinates: readonly RouteCoordinate[],
  panelState: 'compact' | 'half' | 'expanded',
) {
  if (coordinates.length === 0) {
    return
  }
  if (coordinates.length === 1) {
    map.flyTo({
      center: [coordinates[0][0], coordinates[0][1]],
      zoom: 15,
      duration: 700,
    })
    return
  }

  const longitudes = coordinates.map(([longitude]) => longitude)
  const latitudes = coordinates.map(([, latitude]) => latitude)
  map.fitBounds(
    [
      [Math.min(...longitudes), Math.min(...latitudes)],
      [Math.max(...longitudes), Math.max(...latitudes)],
    ],
    {
      padding: routeFramePadding(panelState),
      maxZoom: 15,
      duration: 700,
    },
  )
}

function locationGeoJson(location: MapLocation | null | undefined) {
  return {
    type: 'FeatureCollection' as const,
    features: location
      ? [
          {
            type: 'Feature' as const,
            properties: {},
            geometry: {
              type: 'Point' as const,
              coordinates: [location.longitude, location.latitude],
            },
          },
        ]
      : [],
  }
}

function focusMap(map: Map, focusLocation: GeocodingResult | null | undefined) {
  if (!focusLocation) {
    return
  }
  if (focusLocation.bounding_box) {
    const [south, north, west, east] = focusLocation.bounding_box
    map.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 72, maxZoom: 16, duration: 700 },
    )
    return
  }
  map.flyTo({
    center: [focusLocation.longitude, focusLocation.latitude],
    zoom: 15,
    duration: 700,
  })
}

function placeMarkerSize(zoom: number): number {
  const first = PLACE_MARKER_SIZE_STOPS[0]
  if (zoom <= first[0]) {
    return first[1]
  }

  for (let index = 1; index < PLACE_MARKER_SIZE_STOPS.length; index += 1) {
    const previous = PLACE_MARKER_SIZE_STOPS[index - 1]
    const current = PLACE_MARKER_SIZE_STOPS[index]
    if (zoom <= current[0]) {
      const progress = (zoom - previous[0]) / (current[0] - previous[0])
      return previous[1] + progress * (current[1] - previous[1])
    }
  }

  return PLACE_MARKER_SIZE_STOPS.at(-1)?.[1] ?? first[1]
}

function updateSemanticMarkerSizes(
  markers: globalThis.Map<string, SemanticPlaceMarker>,
  zoom: number,
) {
  const size = `${Math.round(placeMarkerSize(zoom))}px`
  for (const { element } of markers.values()) {
    element.style.width = size
    element.style.height = size
  }
}

function updateSemanticMarkerRouteState(
  markers: globalThis.Map<string, SemanticPlaceMarker>,
  routePlaces: readonly PlaceSummary[],
) {
  const routePlaceIds = new Set(routePlaces.map((place) => place.id))
  for (const [placeId, { element }] of markers) {
    element.hidden = routePlaceIds.has(placeId)
  }
}

function updateSemanticMarkerSelectionState(
  markers: globalThis.Map<string, SemanticPlaceMarker>,
  isSelectingLocation: boolean,
) {
  for (const { element } of markers.values()) {
    element.style.pointerEvents = isSelectingLocation ? 'none' : ''
  }
}

function syncSemanticPlaceMarkers(
  map: Map,
  places: readonly PlaceSummary[],
  markers: globalThis.Map<string, SemanticPlaceMarker>,
  onSelectPlace: (placeId: string) => void,
  routePlaces: readonly PlaceSummary[],
  isSelectingLocation: boolean,
) {
  for (const { marker } of markers.values()) {
    marker.remove()
  }
  markers.clear()

  for (const place of places) {
    const markerKind = getPlaceMarkerKind(place.id)
    if (!markerKind) {
      continue
    }

    const element = document.createElement('button')
    element.type = 'button'
    element.className = `place-svg-marker place-svg-marker--${
      ACTIVE_PLACE_MARKER_KINDS.has(markerKind) ? 'active' : 'inactive'
    }${markerKind.endsWith('factory') ? ' place-svg-marker--factory' : ''}`
    element.setAttribute('aria-label', place.title)

    const shape = document.createElement('span')
    shape.className = 'place-svg-marker__shape'
    shape.setAttribute('aria-hidden', 'true')
    const maskUrl = `url("${PLACE_MARKER_URLS[markerKind]}")`
    shape.style.maskImage = maskUrl
    shape.style.setProperty('-webkit-mask-image', maskUrl)
    element.append(shape)

    element.addEventListener('click', (event) => {
      event.stopPropagation()
      onSelectPlace(place.id)
      new Popup({ offset: 12 })
        .setLngLat([place.longitude, place.latitude])
        .setText(place.title)
        .addTo(map)
    })

    const marker = new Marker({ element, anchor: 'center' })
      .setLngLat([place.longitude, place.latitude])
      .addTo(map)
    markers.set(place.id, { marker, element })
  }

  updateSemanticMarkerSizes(markers, map.getZoom())
  updateSemanticMarkerRouteState(markers, routePlaces)
  updateSemanticMarkerSelectionState(markers, isSelectingLocation)
}

export default function MapView({
  places,
  routePlaces = [],
  routePath = [],
  routePanelState = 'compact',
  onSelectPlace,
  isSelectingLocation = false,
  selectedLocation = null,
  focusLocation = null,
  onSelectLocation,
}: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map>(null)
  const semanticMarkersRef = useRef(
    new globalThis.Map<string, SemanticPlaceMarker>(),
  )
  const placesDataRef = useRef(placesToGeoJson(places))
  const routePlacesRef = useRef(routePlaces)
  const routePathRef = useRef(routePath)
  const routePanelStateRef = useRef(routePanelState)
  const selectingRef = useRef(isSelectingLocation)
  const focusLocationRef = useRef(focusLocation)
  const onSelectLocationRef = useRef(onSelectLocation)

  useEffect(() => {
    const placesData = placesToGeoJson(places)
    placesDataRef.current = placesData
    const map = mapRef.current
    const source = map?.getSource<GeoJSONSource>(PLACES_SOURCE_ID)
    source?.setData(placesData)
    if (map && source) {
      syncSemanticPlaceMarkers(
        map,
        places,
        semanticMarkersRef.current,
        onSelectPlace,
        routePlacesRef.current,
        selectingRef.current,
      )
    }
  }, [onSelectPlace, places])

  useEffect(() => {
    routePlacesRef.current = routePlaces
    updateSemanticMarkerRouteState(
      semanticMarkersRef.current,
      routePlaces,
    )
    mapRef.current
      ?.getSource<GeoJSONSource>(ROUTE_STOPS_SOURCE_ID)
      ?.setData(routeStopsToGeoJson(routePlaces))
  }, [routePlaces])

  useEffect(() => {
    routePathRef.current = routePath
    routePanelStateRef.current = routePanelState
    mapRef.current
      ?.getSource<GeoJSONSource>(ROUTE_LINE_SOURCE_ID)
      ?.setData(routeLineToGeoJson(routePath))
    if (mapRef.current) {
      frameRoute(mapRef.current, routePath, routePanelState)
    }
  }, [routePanelState, routePath])

  useEffect(() => {
    selectingRef.current = isSelectingLocation
    onSelectLocationRef.current = onSelectLocation
    if (mapRef.current) {
      mapRef.current.getCanvas().style.cursor = isSelectingLocation
        ? 'crosshair'
        : ''
    }
    updateSemanticMarkerSelectionState(
      semanticMarkersRef.current,
      isSelectingLocation,
    )
  }, [isSelectingLocation, onSelectLocation])

  useEffect(() => {
    mapRef.current
      ?.getSource<GeoJSONSource>(DRAFT_SOURCE_ID)
      ?.setData(locationGeoJson(selectedLocation))
  }, [selectedLocation])

  useEffect(() => {
    focusLocationRef.current = focusLocation
    if (mapRef.current) {
      focusMap(mapRef.current, focusLocation)
    }
  }, [focusLocation])

  useEffect(() => {
    if (!mapContainer.current) {
      return
    }
    const semanticMarkers = semanticMarkersRef.current

    const map = new Map({
      container: mapContainer.current,
      style: MAP_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      minZoom: MIN_ZOOM,
      renderWorldCopies: false,
    })
    mapRef.current = map
    map.getCanvas().style.cursor = selectingRef.current ? 'crosshair' : ''

    map.addControl(new NavigationControl(), 'top-right')
    map.addControl(new ScaleControl(), 'bottom-right')

    map.on('load', () => {
      localizeMapLabels(map)
      recolorBaseMap(map)
      emphasizeRegionBoundaries(map)
      map.addSource(ROUTE_LINE_SOURCE_ID, {
        type: 'geojson',
        data: routeLineToGeoJson(routePathRef.current),
      })
      map.addLayer({
        id: ROUTE_LINE_LAYER_ID,
        type: 'line',
        source: ROUTE_LINE_SOURCE_ID,
        paint: {
          'line-color': MAP_DARK_COLOR,
          'line-width': 5,
          'line-opacity': 0.82,
        },
      })
      map.addSource(PLACES_SOURCE_ID, {
        type: 'geojson',
        data: placesDataRef.current,
      })
      map.addLayer({
        id: PLACES_LAYER_ID,
        type: 'circle',
        source: PLACES_SOURCE_ID,
        filter: ['==', ['get', 'markerKind'], null],
        paint: {
          'circle-color': MAP_DARK_COLOR,
          'circle-radius': 7,
          'circle-stroke-color': MAP_INK_COLOR,
          'circle-stroke-width': 2,
        },
      })
      map.addSource(ROUTE_STOPS_SOURCE_ID, {
        type: 'geojson',
        data: routeStopsToGeoJson(routePlacesRef.current),
      })
      map.addLayer({
        id: ROUTE_STOPS_LAYER_ID,
        type: 'circle',
        source: ROUTE_STOPS_SOURCE_ID,
        paint: {
          'circle-color': MAP_INK_COLOR,
          'circle-radius': 12,
          'circle-stroke-color': MAP_LIGHT_COLOR,
          'circle-stroke-width': 3,
        },
      })
      map.addLayer({
        id: ROUTE_STOP_LABELS_LAYER_ID,
        type: 'symbol',
        source: ROUTE_STOPS_SOURCE_ID,
        layout: {
          'text-field': ['get', 'order'],
          'text-size': 12,
        },
        paint: {
          'text-color': MAP_LIGHT_COLOR,
        },
      })
      map.addSource(DRAFT_SOURCE_ID, {
        type: 'geojson',
        data: locationGeoJson(null),
      })
      map.addLayer({
        id: DRAFT_LAYER_ID,
        type: 'circle',
        source: DRAFT_SOURCE_ID,
        paint: {
          'circle-color': MAP_ACCENT_COLOR,
          'circle-radius': 10,
          'circle-stroke-color': MAP_LIGHT_COLOR,
          'circle-stroke-width': 4,
        },
      })
      focusMap(map, focusLocationRef.current)
      frameRoute(map, routePathRef.current, routePanelStateRef.current)

      map.on('click', (event) => {
        if (!selectingRef.current || !onSelectLocationRef.current) {
          return
        }
        onSelectLocationRef.current({
          latitude: event.lngLat.lat,
          longitude: event.lngLat.lng,
        })
      })

      const handlePlaceClick = (event: MapLayerMouseEvent) => {
        if (selectingRef.current) {
          return
        }
        const title = event.features?.[0]?.properties.title
        const placeId = event.features?.[0]?.properties.id

        if (typeof title !== 'string' || typeof placeId !== 'string') {
          return
        }

        if (routePlacesRef.current.some((place) => place.id === placeId)) {
          return
        }

        onSelectPlace(placeId)

        new Popup({ offset: 12 })
          .setLngLat(event.lngLat)
          .setText(title)
          .addTo(map)
      }

      const addPlaceLayerInteractions = (layerId: string) => {
        map.on('click', layerId, handlePlaceClick)
        map.on('mouseenter', layerId, () => {
          if (!selectingRef.current) {
            map.getCanvas().style.cursor = 'pointer'
          }
        })
        map.on('mouseleave', layerId, () => {
          map.getCanvas().style.cursor = selectingRef.current
            ? 'crosshair'
            : ''
        })
      }

      addPlaceLayerInteractions(PLACES_LAYER_ID)

      syncSemanticPlaceMarkers(
        map,
        placesDataRef.current.features.map((feature) => ({
          id: feature.properties.id,
          title: feature.properties.title,
          longitude: feature.geometry.coordinates[0],
          latitude: feature.geometry.coordinates[1],
        })),
        semanticMarkers,
        onSelectPlace,
        routePlacesRef.current,
        selectingRef.current,
      )
      map.on('zoom', () => {
        updateSemanticMarkerSizes(
          semanticMarkers,
          map.getZoom(),
        )
      })

      map.on('click', ROUTE_STOPS_LAYER_ID, (event) => {
        const title = event.features?.[0]?.properties.title
        const placeId = event.features?.[0]?.properties.id

        if (typeof title !== 'string' || typeof placeId !== 'string') {
          return
        }

        onSelectPlace(placeId)
        new Popup({ offset: 16 })
          .setLngLat(event.lngLat)
          .setText(title)
          .addTo(map)
      })

      map.on('mouseenter', ROUTE_STOPS_LAYER_ID, () => {
        if (!selectingRef.current) {
          map.getCanvas().style.cursor = 'pointer'
        }
      })
      map.on('mouseleave', ROUTE_STOPS_LAYER_ID, () => {
        map.getCanvas().style.cursor = selectingRef.current ? 'crosshair' : ''
      })

    })

    const handleResize = () => {
      map.resize()
      frameRoute(map, routePathRef.current, routePanelStateRef.current)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      for (const { marker } of semanticMarkers.values()) {
        marker.remove()
      }
      semanticMarkers.clear()
      mapRef.current = null
      map.remove()
    }
  }, [onSelectPlace])

  return (
    <div
      ref={mapContainer}
      className="map-container"
      role="application"
      aria-label="Интерактивная карта"
    />
  )
}
