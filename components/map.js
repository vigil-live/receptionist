'use client';

import { useEffect, useRef } from 'react';

const SEV_COLORS = {
  critical: '#dc2626',
  high:     '#ea580c',
  medium:   '#d97706',
  low:      '#16a34a',
};

export default function Map({ calls, selectedId, onSelect }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    const boot = async () => {
      if (typeof window === 'undefined') return;

      const L = (await import('leaflet')).default;
      if (cancelled) return;

      const el = containerRef.current;
      if (!el) return;

      // If Leaflet already initialized this container, destroy it first
      if (el._leaflet_id) {
        el._leaflet_id = null;
      }
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }

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

      // Pulse keyframe (inject once)
      if (!document.getElementById('vigil-pulse-css')) {
        const st = document.createElement('style');
        st.id = 'vigil-pulse-css';
        st.textContent = `
          @keyframes vg-pulse {
            0%   { transform: scale(.85); opacity: .55; }
            100% { transform: scale(2.6); opacity: 0; }
          }`;
        document.head.appendChild(st);
      }

      calls.forEach(c => {
        const color = SEV_COLORS[c.severity];
        const live  = c.status === 'active';
        const num   = c.id.replace('C', '');

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
        L.marker([c.location.lat, c.location.lng], { icon })
          .addTo(map)
          .on('click', () => onSelect(c.id));
      });

      setTimeout(() => { if (mapRef.current) mapRef.current.invalidateSize(); }, 100);
    };

    boot();

    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !selectedId) return;
    const c = calls.find(x => x.id === selectedId);
    if (c) mapRef.current.flyTo([c.location.lat, c.location.lng], 14, { duration: 0.9 });
  }, [selectedId]);

  return (
    <div
      ref={containerRef}
      style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}
    />
  );
}