import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';


interface MapLayerProps {
  scope: 'operator' | 'citizen';
}

export default function MapLayer({ scope }: MapLayerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  const { data: hotspots } = useQuery({
    queryKey: ['hotspots'],
    queryFn: () => ClearApi.hotspots(5, 20),
    enabled: scope === 'operator',
  });

  const { data: risks } = useQuery({
    queryKey: ['corridorsRisk', scope],
    queryFn: () => ClearApi.corridorsRisk(scope),
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

    map.current.on('load', () => {
      // We would ideally add sources and layers here. 
      // For a production app, we need geojson. Since we only have centroids and corridor names,
      // we will just plot markers for hotspots.
    });

  }, []);

  useEffect(() => {
    if (!map.current || !hotspots?.clusters) return;

    // Remove existing markers (simplified for this demo, usually we'd track marker instances)
    const markers = document.querySelectorAll('.hotspot-marker');
    markers.forEach(m => m.remove());

    hotspots.clusters.forEach(cluster => {
      if (!cluster.centroid_lon || !cluster.centroid_lat) return;
      
      const el = document.createElement('div');
      el.className = 'hotspot-marker w-6 h-6 bg-red-500 rounded-full border-2 border-white shadow-lg opacity-80 flex items-center justify-center text-white text-xs font-bold';
      el.innerText = String(cluster.size);

      new maplibregl.Marker(el)
        .setLngLat([cluster.centroid_lon, cluster.centroid_lat])
        .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(`
          <div class="p-2">
            <h3 class="font-bold">Hotspot</h3>
            <p>Size: ${cluster.size}</p>
            <p>Corridor: ${cluster.top_corridor || 'Unknown'}</p>
          </div>
        `))
        .addTo(map.current!);
    });
  }, [hotspots]);

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
      </div>
    </div>
  );
}
