import { useEffect, useRef } from 'react'
import {
  Map,
  NavigationControl,
  ScaleControl,
  setWorkerUrl,
} from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

const INITIAL_CENTER: [number, number] = [37.6173, 55.7558]

setWorkerUrl(maplibreWorkerUrl)

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!mapContainer.current) {
      return
    }

    const map = new Map({
      container: mapContainer.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: INITIAL_CENTER,
      zoom: 4,
    })

    map.addControl(new NavigationControl(), 'top-right')
    map.addControl(new ScaleControl(), 'bottom-right')

    return () => map.remove()
  }, [])

  return (
    <div
      ref={mapContainer}
      className="map-container"
      role="application"
      aria-label="Интерактивная карта"
    />
  )
}
