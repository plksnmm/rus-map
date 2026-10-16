import { useEffect, useRef } from 'react'
import {
  GeoJSONSource,
  Map,
  NavigationControl,
  Popup,
  ScaleControl,
  setWorkerUrl,
} from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import type { GeocodingResult } from '../api/geocoding'
import type { PlaceSummary } from '../api/places'
import type { MapLocation } from './PlaceSubmissionForm'
import {
  emphasizeRegionBoundaries,
  localizeMapLabels,
} from '../map/localizeStyle'
import { placesToGeoJson } from '../map/placesGeoJson'
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
const DRAFT_SOURCE_ID = 'submission-location'
const DRAFT_LAYER_ID = 'submission-location-marker'

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
    mapRef.current
      ?.getSource<GeoJSONSource>(PLACES_SOURCE_ID)
      ?.setData(placesData)
  }, [places])

  useEffect(() => {
    routePlacesRef.current = routePlaces
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
          'line-color': '#a82626',
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
        paint: {
          'circle-color': '#a82626',
          'circle-radius': 8,
          'circle-stroke-color': '#ffffff',
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
          'circle-color': '#a82626',
          'circle-radius': 12,
          'circle-stroke-color': '#ffffff',
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
          'text-color': '#ffffff',
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
          'circle-color': '#a82626',
          'circle-radius': 10,
          'circle-stroke-color': '#f7f1e7',
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

      map.on('click', PLACES_LAYER_ID, (event) => {
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

      map.on('mouseenter', PLACES_LAYER_ID, () => {
        if (!selectingRef.current) {
          map.getCanvas().style.cursor = 'pointer'
        }
      })
      map.on('mouseleave', PLACES_LAYER_ID, () => {
        map.getCanvas().style.cursor = selectingRef.current ? 'crosshair' : ''
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
