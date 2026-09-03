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
import type { PlaceSummary } from '../api/places'
import {
  emphasizeRegionBoundaries,
  localizeMapLabels,
} from '../map/localizeStyle'
import { placesToGeoJson } from '../map/placesGeoJson'

const INITIAL_CENTER: [number, number] = [94, 64]
const INITIAL_ZOOM = 2.1
const MIN_ZOOM = 2
const MAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/dark'
const PLACES_SOURCE_ID = 'places'
const PLACES_LAYER_ID = 'places-markers'

setWorkerUrl(maplibreWorkerUrl)

interface MapViewProps {
  places: PlaceSummary[]
  onSelectPlace: (placeId: string) => void
}

export default function MapView({ places, onSelectPlace }: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map>(null)
  const placesDataRef = useRef(placesToGeoJson(places))

  useEffect(() => {
    const placesData = placesToGeoJson(places)
    placesDataRef.current = placesData
    mapRef.current
      ?.getSource<GeoJSONSource>(PLACES_SOURCE_ID)
      ?.setData(placesData)
  }, [places])

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

    map.addControl(new NavigationControl(), 'top-right')
    map.addControl(new ScaleControl(), 'bottom-right')

    map.on('load', () => {
      localizeMapLabels(map)
      emphasizeRegionBoundaries(map)
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

      map.on('click', PLACES_LAYER_ID, (event) => {
        const title = event.features?.[0]?.properties.title
        const placeId = event.features?.[0]?.properties.id

        if (typeof title !== 'string' || typeof placeId !== 'string') {
          return
        }

        onSelectPlace(placeId)

        new Popup({ offset: 12 })
          .setLngLat(event.lngLat)
          .setText(title)
          .addTo(map)
      })

      map.on('mouseenter', PLACES_LAYER_ID, () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', PLACES_LAYER_ID, () => {
        map.getCanvas().style.cursor = ''
      })
    })

    return () => {
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
