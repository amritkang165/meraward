/**
 * MapLibre map with a draggable pin.
 *
 * The basemap is CARTO Positron: no API key, and its terms permit application
 * use with attribution. We deliberately do *not* point at
 * `tile.openstreetmap.org` — its usage policy prohibits exactly this, and this
 * is a public URL judges will click. Attribution is rendered in-map.
 */
import { useEffect, useRef } from 'react'
import maplibregl, { type Map as MapLibreMap, type Marker } from 'maplibre-gl'

const STYLE_URL =
  import.meta.env.VITE_BASEMAP_STYLE_URL ??
  'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

/** Delhi. The map opens here rather than at null island. */
export const DELHI_CENTRE: [number, number] = [77.2167, 28.6315]

const ATTRIBUTION =
  '© <a href="https://carto.com/attributions">CARTO</a> · © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · Ward boundaries © <a href="https://github.com/datameet/Municipal_Spatial_Data">DataMeet</a> (CC BY-SA 2.5 IN)'

export function MapView({
  pin,
  onPinMove,
  className = '',
}: {
  pin: { lat: number; lng: number }
  onPinMove: (position: { lat: number; lng: number }) => void
  className?: string
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  const marker = useRef<Marker | null>(null)
  // Kept in a ref so re-renders don't tear down and rebuild the map.
  const onMove = useRef(onPinMove)
  onMove.current = onPinMove

  useEffect(() => {
    if (!container.current || map.current) return

    const instance = new maplibregl.Map({
      container: container.current,
      style: STYLE_URL,
      center: [pin.lng, pin.lat],
      zoom: 12,
      attributionControl: false,
    })
    map.current = instance

    instance.addControl(
      new maplibregl.AttributionControl({ compact: true, customAttribution: ATTRIBUTION }),
      'bottom-right',
    )
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    const pinMarker = new maplibregl.Marker({ color: '#0E6E68', draggable: true })
      .setLngLat([pin.lng, pin.lat])
      .addTo(instance)
    marker.current = pinMarker

    // MapLibre labels its marker div with aria-label but gives it no role,
    // which is a prohibited ARIA usage. Naming the role makes the label valid
    // and tells a screen reader what the thing actually is.
    const markerElement = pinMarker.getElement()
    markerElement.setAttribute('role', 'img')
    markerElement.setAttribute('aria-label', 'Selected location. Drag to move.')

    pinMarker.on('dragend', () => {
      const { lat, lng } = pinMarker.getLngLat()
      onMove.current({ lat, lng })
    })

    // Tapping the map is faster than dragging on a phone.
    instance.on('click', (event) => {
      pinMarker.setLngLat(event.lngLat)
      onMove.current({ lat: event.lngLat.lat, lng: event.lngLat.lng })
    })

    return () => {
      instance.remove()
      map.current = null
      marker.current = null
    }
    // Mount once. Pin updates are handled by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Keep the marker in step when the pin changes from outside (e.g. "use my
  // location"), without rebuilding the map.
  useEffect(() => {
    if (!marker.current || !map.current) return
    const current = marker.current.getLngLat()
    if (Math.abs(current.lat - pin.lat) < 1e-7 && Math.abs(current.lng - pin.lng) < 1e-7) return
    marker.current.setLngLat([pin.lng, pin.lat])
    map.current.easeTo({ center: [pin.lng, pin.lat], duration: 600 })
  }, [pin.lat, pin.lng])

  return <div ref={container} className={className} aria-label="Map of Delhi" role="application" />
}
