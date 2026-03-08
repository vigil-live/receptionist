'use client';
import { useEffect, useRef, useState } from 'react';

const SEV_COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#d97706',
  low: '#16a34a',
};

function markerKey(calls) {
  return calls
    .map(c => `${c.id}:${c.location?.lat}:${c.location?.lng}:${c.severity}:${c.status}:${c.call_number}`)
    .join('|');
}

export default function Map({ calls, selectedId, onSelect, dark }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const LRef = useRef(null);
  const prevMarkerKey = useRef('');
  const callsRef = useRef(calls);
  const flownToId = useRef(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => { callsRef.current = calls; }, [calls]);

  useEffect(() => {
    let cancelled = false;

    const boot = async () => {
      if (typeof window === 'undefined') return;
      const L = (await import('leaflet')).default;
      if (cancelled) return;

      LRef.current = L;

      const el = containerRef.current;
      if (!el) return;

      if (el._leaflet_id) el._leaflet_id = null;
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }

      const map = L.map(el, {
        center: [34.052235, -118.243683],
        zoom: 11,
        zoomControl: false,
        attributionControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(map);

      mapRef.current = map;

      if (!document.getElementById('vigil-pulse-css')) {
        const st = document.createElement('style');
        st.id = 'vigil-pulse-css';
        st.textContent = `
          @keyframes vg-pulse {
            0% { transform: scale(.85); opacity: .55; }
            100% { transform: scale(2.6); opacity: 0; }
          }`;
        document.head.appendChild(st);
      }

      setTimeout(() => { if (mapRef.current) mapRef.current.invalidateSize(); }, 100);
      if (!cancelled) setMapReady(true);
    };

    boot();
    return () => {
      cancelled = true;
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const L = LRef.current;
    if (!map || !L) return;

    const key = markerKey(calls);
    if (key === prevMarkerKey.current) return;
    prevMarkerKey.current = key;

    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    const locatedCalls = calls.filter(
      c => c.location?.lat != null && c.location?.lng != null
    );

    locatedCalls.forEach(c => {
      const color = SEV_COLORS[c.severity] ?? SEV_COLORS.medium;
      const live = c.status === 'active';
      const num = String(c.call_number ?? c.id.slice(-3));

      const html = `
        <div style="position:relative;width:40px;height:40px;display:flex;align-items:center;justify-content:center;">
          ${live ? `
            <div style="position:absolute;inset:0;border-radius:50%;background:${color};opacity:.12;animation:vg-pulse 2s ease-out infinite;"></div>
            <div style="position:absolute;width:28px;height:28px;border-radius:50%;border:1.5px solid ${color};opacity:.4;animation:vg-pulse 2s ease-out .6s infinite;"></div>
          ` : ''}
          <div style="
            position:relative;z-index:2;
            width:24px;height:24px;border-radius:50%;
            background:${color};
            border:2.5px solid white;
            box-shadow:0 2px 8px ${color}88;
            display:flex;align-items:center;justify-content:center;
            font:700 10px/1 'Inter',sans-serif;
            color:#fff;
          ">${num}</div>
        </div>`;

      const icon = L.divIcon({ html, className: '', iconSize: [40, 40], iconAnchor: [20, 20] });
      const marker = L.marker([c.location.lat, c.location.lng], { icon })
        .addTo(map)
        .on('click', () => onSelect(c.id));

      markersRef.current.push(marker);
    });
  }, [calls, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedId) return;
    if (flownToId.current === selectedId) return;
    const c = callsRef.current.find(x => x.id === selectedId);
    if (c?.location?.lat != null && c?.location?.lng != null) {
      map.panTo([c.location.lat, c.location.lng]);
      flownToId.current = selectedId;
    }
  }, [selectedId, mapReady]);
}