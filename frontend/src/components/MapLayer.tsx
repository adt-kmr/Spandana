import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useQuery, useQueries } from '@tanstack/react-query';
import { ClearApi } from '../api';
import type { RainRisk } from '../types';


// Corridor coordinates in [lng, lat] — mirror of backend corridor_latlon_json.
const RAIN_CORRIDORS: Record<string, [number, number]> = {
  'Sarjapur Road': [77.6810, 12.9180],
  'ORR East': [77.7010, 12.9560],
  'ORR West': [77.5050, 13.0280],
  'Hosur Road': [77.6390, 12.9100],
  'Old Madras Road': [77.6720, 12.9920],
  'Mysore Road': [77.5260, 12.9447],
  'MG Road': [77.6090, 12.9750],
  'Residency Road': [77.6010, 12.9690],
  'Bellary Road': [77.5970, 13.0358],
  'Kanakapura Road': [77.5600, 12.9120],
  'Brigade Road': [77.6090, 12.9720],
  'Richmond Road': [77.6010, 12.9620],
  'Tumkur Road': [77.5190, 13.0280],
  'Magadi Road': [77.5360, 12.9760],
};

// Shared data-driven colour expression (band => colour).
const BAND_COLOR: any = [
  'match', ['get', 'band'],
  'high', '#ef4444',
  'moderate', '#f59e0b',
  'low', '#22c55e',
  '#94a3b8',
];

interface MapLayerProps {
  scope: 'operator' | 'citizen';
}

export default function MapLayer({ scope }: MapLayerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markerInstances = useRef<maplibregl.Marker[]>([]);

  const { data: hotspots } = useQuery({
    queryKey: ['hotspots'],
    queryFn: () => ClearApi.hotspots(5, 20),
    enabled: scope === 'operator',
  });

  const { data: risks } = useQuery({
    queryKey: ['corridorsRisk', scope],
    queryFn: () => ClearApi.corridorsRisk(scope),
  });

  // Live rain-clog for every known corridor, in parallel.
  const rainResults = useQueries({
    queries: Object.keys(RAIN_CORRIDORS).map((name) => ({
      queryKey: ['rain-risk-map', name, scope],
      queryFn: () => ClearApi.rainRisk(name, scope),
      refetchInterval: 5 * 60 * 1000,
    })),
  });

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [77.5946, 12.9716], // Bengaluru
      zoom: 11,
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.current.on('load', () => map.current?.resize());

    const ro = new ResizeObserver(() => map.current?.resize());
    ro.observe(mapContainer.current);

    return () => {
      ro.disconnect();
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current || !hotspots?.clusters) return;

    markerInstances.current.forEach(m => m.remove());
    markerInstances.current = [];

    hotspots.clusters.forEach(cluster => {
      if (!cluster.centroid_lon || !cluster.centroid_lat) return;
      
      const el = document.createElement('div');
      el.className = 'hotspot-marker w-6 h-6 bg-red-500 rounded-full border-2 border-white shadow-lg opacity-80 flex items-center justify-center text-white text-xs font-bold';
      el.innerText = String(cluster.size);

      const marker = new maplibregl.Marker(el)
        .setLngLat([cluster.centroid_lon, cluster.centroid_lat])
        .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(`
          <div class="p-2">
            <h3 class="font-bold">Hotspot</h3>
            <p>Size: ${cluster.size}</p>
            <p>Corridor: ${cluster.top_corridor || 'Unknown'}</p>
          </div>
        `))
        .addTo(map.current!);
        
      markerInstances.current.push(marker);
    });
  }, [hotspots]);

  // Rain-clog overlay: data-driven coloured circles per corridor.
  const rainSignature = rainResults
    .map((r) => (r.data ? `${r.data.corridor}:${r.data.available ? r.data.rain_clog_score : 'x'}:${r.data.risk_band}` : ''))
    .join('|');

  useEffect(() => {
    const m = map.current;
    if (!m) return;

    const features = rainResults
      .map((r) => r.data)
      .filter((d): d is RainRisk => !!d && d.available && !!RAIN_CORRIDORS[d.corridor])
      .map((d) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: RAIN_CORRIDORS[d.corridor] },
        properties: {
          corridor: d.corridor,
          score: d.rain_clog_score,
          band: d.risk_band,
          multiplier: d.rain_multiplier,
        },
      }));

    const data: any = { type: 'FeatureCollection', features };

    const apply = () => {
      const existing = m.getSource('rain-risk') as maplibregl.GeoJSONSource | undefined;
      if (existing) {
        existing.setData(data);
        return;
      }

      m.addSource('rain-risk', { type: 'geojson', data });

      // Soft glow halo (radius grows with score).
      m.addLayer({
        id: 'rain-risk-glow',
        type: 'circle',
        source: 'rain-risk',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'score'], 0, 16, 100, 46],
          'circle-color': BAND_COLOR,
          'circle-opacity': 0.18,
          'circle-blur': 0.7,
        },
      } as any);

      // Solid core dot.
      m.addLayer({
        id: 'rain-risk-core',
        type: 'circle',
        source: 'rain-risk',
        paint: {
          'circle-radius': 7,
          'circle-color': BAND_COLOR,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        },
      } as any);

      m.on('click', 'rain-risk-core', (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as { corridor: string; score: number; band: string; multiplier: number };
        new maplibregl.Popup({ offset: 14 })
          .setLngLat((f.geometry as any).coordinates as [number, number])
          .setHTML(`
            <div class="p-2 font-sans">
              <h3 class="font-bold">${p.corridor}</h3>
              <p>Rain-clog: ${p.score}/100 (${p.band})</p>
              <p>ETA impact: ×${p.multiplier}</p>
            </div>
          `)
          .addTo(m);
      });
      m.on('mouseenter', 'rain-risk-core', () => { m.getCanvas().style.cursor = 'pointer'; });
      m.on('mouseleave', 'rain-risk-core', () => { m.getCanvas().style.cursor = ''; });
    };

    if (m.isStyleLoaded()) apply();
    else m.once('load', apply);
  }, [rainSignature]);

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100 flex flex-col">
      <div ref={mapContainer} className="flex-1" />
      
      {/* Overlay for risks */}
      <div className="absolute top-4 left-4 bg-white/90 backdrop-blur p-4 rounded-xl shadow-lg border border-slate-200 max-w-sm max-h-[50%] overflow-y-auto">
        <h3 className="text-sm font-bold text-slate-800 mb-2 flex items-center justify-between">
          <span>Corridor Risk (3h Nowcast)</span>
          {risks?.note && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded ml-2">Degraded</span>}
        </h3>
        <div className="space-y-2">
          {!risks?.corridors?.length ? (
            <p className="text-sm text-slate-500">No data available</p>
          ) : (
            risks.corridors.slice(0, 5).map(c => (
              <div key={c.corridor} className="flex items-center justify-between text-sm">
                <span className="truncate w-32 font-medium text-slate-600" title={c.corridor}>{c.corridor}</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${c.risk > 70 ? 'bg-red-500' : c.risk > 40 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${c.risk}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold w-6 text-right">{c.risk}</span>
                </div>
                {c.stale && <span className="text-[10px] text-amber-600 bg-amber-50 px-1 rounded border border-amber-200">STALE</span>}
              </div>
            ))
          )}
        </div>

        {/* Rain-clog overlay legend */}
        <div className="mt-3 pt-2 border-t border-slate-200">
          <div className="text-xs font-bold text-slate-700 mb-1">🌧️ Rain-clog overlay</div>
          <div className="flex items-center gap-3 text-[11px] text-slate-600">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />Low</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />Moderate</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />High</span>
          </div>
        </div>
      </div>
    </div>
  );
}
