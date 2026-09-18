/**
 * The dashboard map: every complaint in Delhi at once.
 *
 * Markers are a single GeoJSON source with two layers — a heatmap at low zoom
 * and circles at high zoom — rather than one DOM marker per complaint. Several
 * hundred absolutely-positioned DOM nodes that reposition on every frame of a
 * pan is the difference between a map that glides and one that stutters on a
 * mid-range Android; the GPU draws these instead.
 */
import { useEffect, useRef } from 'react'
import maplibregl, { type Map as MapLibreMap } from 'maplibre-gl'
import type { MapMarker } from '../api/types'

const STYLE_URL =
  import.meta.env.VITE_BASEMAP_STYLE_URL ??
  'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

const ATTRIBUTION =
  '© <a href="https://carto.com/attributions">CARTO</a> · © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · Ward boundaries © <a href="https://github.com/datameet/Municipal_Spatial_Data">DataMeet</a> (CC BY-SA 2.5 IN)'

const SOURCE = 'complaints'

/** Status drives colour: open is the thing that needs attention. */
const STATUS_COLOUR: maplibregl.ExpressionSpecification = [
  'match',
  ['get', 'status'],
  'RESOLVED',
  '#15803d',
  'ACKNOWLEDGED',
  '#b45309',
  '#b91c1c',
]

function toGeoJson(markers: MapMarker[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: markers.map((m) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [Number(m.lng), Number(m.lat)] },
      properties: {
        complaint_id: m.complaint_id,
        status: m.status,
        issue_type: m.issue_type,
      },
    })),
  }
}

export function ComplaintsMap({
  markers,
  heatmap,
  onSelect,
  className = '',
}: {
  markers: MapMarker[]
  heatmap: boolean
  onSelect?: (complaintId: string) => void
  className?: string
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  const ready = useRef(false)

  // Latest props, readable from the mount effect and from MapLibre's own
  // callbacks without making either depend on them and tear the map down.
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect
  const markersRef = useRef(markers)
  markersRef.current = markers
  const heatmapRef = useRef(heatmap)
  heatmapRef.current = heatmap

  useEffect(() => {
    if (!container.current || map.current) return

    const instance = new maplibregl.Map({
      container: container.current,
      style: STYLE_URL,
      center: [77.2167, 28.6315],
      zoom: 10,
      attributionControl: false,
    })
    map.current = instance

    instance.addControl(
      new maplibregl.AttributionControl({ compact: true, customAttribution: ATTRIBUTION }),
      'bottom-right',
    )
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    instance.on('load', () => {
      instance.addSource(SOURCE, { type: 'geojson', data: toGeoJson([]) })

      instance.addLayer({
        id: 'complaints-heat',
        type: 'heatmap',
        source: SOURCE,
        paint: {
          'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 9, 12, 14, 34],
          'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 9, 0.85, 14, 0.4],
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0,
            'rgba(0,0,0,0)',
            0.3,
            '#d6ebe8',
            0.6,
            '#f0b429',
            1,
            '#b91c1c',
          ],
        },
      })

      instance.addLayer({
        id: 'complaints-points',
        type: 'circle',
        source: SOURCE,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 3, 15, 8],
          'circle-color': STATUS_COLOUR,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
          'circle-opacity': 0.9,
        },
      })

      instance.on('click', 'complaints-points', (event) => {
        const id = event.features?.[0]?.properties?.complaint_id
        if (typeof id === 'string') onSelectRef.current?.(id)
      })
      instance.on('mouseenter', 'complaints-points', () => {
        instance.getCanvas().style.cursor = 'pointer'
      })
      instance.on('mouseleave', 'complaints-points', () => {
        instance.getCanvas().style.cursor = ''
      })

      ready.current = true
      const source = instance.getSource(SOURCE) as maplibregl.GeoJSONSource | undefined
      source?.setData(toGeoJson(markersRef.current))
      applyVisibility(instance, heatmapRef.current)
    })

    return () => {
      instance.remove()
      map.current = null
      ready.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Swap the data on the existing source rather than rebuilding the map.
  useEffect(() => {
    if (!map.current || !ready.current) return
    const source = map.current.getSource(SOURCE) as maplibregl.GeoJSONSource | undefined
    source?.setData(toGeoJson(markers))
  }, [markers])

  useEffect(() => {
    if (!map.current || !ready.current) return
    applyVisibility(map.current, heatmap)
  }, [heatmap])

  return <div ref={container} className={className} role="application" aria-label="Complaints across Delhi" />
}

function applyVisibility(instance: MapLibreMap, heatmap: boolean) {
  if (instance.getLayer('complaints-heat')) {
    instance.setLayoutProperty('complaints-heat', 'visibility', heatmap ? 'visible' : 'none')
  }
  if (instance.getLayer('complaints-points')) {
    instance.setLayoutProperty('complaints-points', 'visibility', heatmap ? 'none' : 'visible')
  }
}
