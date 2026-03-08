'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import {
  Sun, Moon, SlidersHorizontal,
  ShieldCheck, Flame, Ambulance,
  MapPin, Clock, Phone, User, ChevronDown, Send, Check, X, PhoneForwarded, FileText, Radio, Pencil
} from 'lucide-react';

const Map = dynamic(() => import('../components/map.js'), {
  ssr: false,
  loading: () => (
    <div style={{ width: '100%', height: '100%', background: 'var(--surface2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ font: '12px var(--font)', color: 'var(--text3)' }}>Loading map…</span>
    </div>
  ),
});

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const POLL_INTERVAL_MS = 3000;

const SEV = {
  critical: { color: '#dc2626', bg: 'rgba(220,38,38,.1)',  label: 'Critical' },
  high:     { color: '#ea580c', bg: 'rgba(234,88,12,.1)',  label: 'High' },
  medium:   { color: '#d97706', bg: 'rgba(217,119,6,.1)',  label: 'Medium' },
  low:      { color: '#16a34a', bg: 'rgba(22,163,74,.1)',  label: 'Low' },
};

const STAT = {
  active:      { color: '#16a34a', label: 'Live' },
  pending:     { color: '#d97706', label: 'Pending' },
  dispatched:  { color: '#2563eb', label: 'Dispatched' },
  resolved:    { color: '#94a3b8', label: 'Resolved' },
  transferred: { color: '#7c3aed', label: 'Transferred' },
};

const DISPATCH_OPTS = [
  { type: 'police',    label: 'Police',    color: '#2563eb', icon: ShieldCheck },
  { type: 'fire',      label: 'Fire Dept', color: '#ea580c', icon: Flame },
  { type: 'ambulance', label: 'Ambulance', color: '#dc2626', icon: Ambulance },
];

function fmt(s) {
  const secs = Math.max(0, Math.floor(s));
  return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
}

function Topbar({ dark, toggle, time, liveCount }) {
  return (
    <div style={{
      height: 54, flexShrink: 0,
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      padding: '0 20px', gap: 12,
      boxShadow: 'var(--shadow)',
      zIndex: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <img src="/logo.png" alt="Vigil" style={{ width: 30, height: 30, borderRadius: 8, objectFit: 'cover' }} />
        <div>
          <div style={{ font: '700 15px var(--font)', color: 'var(--text)', lineHeight: 1 }}>Vigil</div>
          <div style={{ font: '500 9px var(--font)', color: 'var(--text3)', letterSpacing: '.07em', textTransform: 'uppercase' }}>Dispatch Intelligence</div>
        </div>
      </div>

      {liveCount > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px', background: 'rgba(220,38,38,.1)', border: '1px solid rgba(220,38,38,.3)', borderRadius: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#dc2626', animation: 'pulse 1.5s infinite' }} />
          <span style={{ font: '600 11px var(--font)', color: '#dc2626' }}>{liveCount} Live</span>
        </div>
      )}

      <div style={{ flex: 1 }} />
      <span style={{ font: '600 14px var(--font)', color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{time}</span>
      <div style={{ width: 1, height: 28, background: 'var(--border)' }} />
      <button onClick={toggle} style={{
        width: 32, height: 32, borderRadius: 8,
        background: 'var(--surface2)', border: '1px solid var(--border)',
        cursor: 'pointer', color: 'var(--text2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {dark ? <Sun size={14} /> : <Moon size={14} />}
      </button>
    </div>
  );
}

function CallCard({ call, selected, onSelect }) {
  const sev  = SEV[call.severity]  || SEV.medium;
  const stat = STAT[call.status]   || STAT.pending;

  return (
    <div
      onClick={() => onSelect(call.id)}
      className="fadeup"
      style={{
        padding: '12px 14px',
        background: selected ? 'var(--surface2)' : 'transparent',
        borderLeft: `3px solid ${selected ? sev.color : 'transparent'}`,
        borderBottom: '1px solid var(--border)',
        cursor: 'pointer',
        transition: 'background .15s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ font: '600 10px var(--font)', color: sev.color, background: sev.bg, padding: '2px 6px', borderRadius: 4 }}>
            {sev.label}
          </span>
          <span style={{ font: '400 10px var(--font)', color: 'var(--text3)' }}>#{call.call_number ?? '—'}</span>
        </div>
        <span style={{ font: '500 10px var(--font)', color: stat.color }}>{stat.label}</span>
      </div>
      <div style={{ font: '600 12px/1.35 var(--font)', color: 'var(--text)', marginBottom: 5 }}>{call.incident}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 3, marginBottom: 5 }}>
        <MapPin size={9} color="var(--text3)" />
        <span style={{ font: '400 10px var(--font)', color: 'var(--text3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {call.location?.address || 'Unspecified Location'}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        <Clock size={9} color="var(--text3)" />
        <span style={{ font: '400 10px var(--font)', color: 'var(--text3)' }}>{fmt(call.callDuration)}</span>
      </div>
    </div>
  );
}

function Detail({ call, onDispatch, onTransfer, onClose, onUpdate }) {
  const [confirm, setConfirm]             = useState(null);
  const [showTx, setShowTx]               = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError]     = useState(null);
  const [editing, setEditing]             = useState(false);
  const [editFields, setEditFields]       = useState({});

  useEffect(() => {
    setEditing(false);
  }, [call?.id]);

  const startEditing = () => {
    setEditFields({
      incident: call.incident || '',
      name:     call.name     || '',
      phone:    call.phone    || '',
      address:  call.location?.address || '',
      summary:  call.summary  || '',
    });
    setEditing(true);
  };

  const saveEdits = () => {
    onUpdate(call.id, {
      incident: editFields.incident,
      name:     editFields.name,
      phone:    editFields.phone,
      summary:  editFields.summary,
      location: { ...call.location, address: editFields.address },
    });
    setEditing(false);
  };

  if (!call) return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 24 }}>
      <div style={{ width: 44, height: 44, borderRadius: 10, background: 'var(--surface2)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Radio size={20} color="var(--text3)" />
      </div>
      <span style={{ font: '500 12px var(--font)', color: 'var(--text3)' }}>Awaiting incoming calls…</span>
    </div>
  );

  const sev = SEV[call.severity] || SEV.medium;
  const addressDisplay = call.location?.address && call.location.address !== 'Unspecified Location'
    ? (call.location.address.split(',')[0] || '—')
    : 'Unspecified';

  const inputStyle = {
    width: '100%', boxSizing: 'border-box',
    padding: '6px 9px', borderRadius: 6,
    background: 'var(--surface)', border: '1px solid var(--blue)',
    font: '500 12px var(--font)', color: 'var(--text)',
    outline: 'none',
  };

  return (
    <div className="slidein" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ height: 3, background: sev.color, flexShrink: 0 }} />

      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: sev.color }} />
              <span style={{ font: '700 14px var(--font)', color: 'var(--text)' }}>Call #{call.call_number ?? '—'}</span>
            </div>
            <div style={{ font: '500 11px/1.4 var(--font)', color: 'var(--text2)', paddingLeft: 15 }}>{call.incident}</div>
          </div>
          <button onClick={onClose} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, padding: 5, cursor: 'pointer', color: 'var(--text3)', display: 'flex' }}>
            <X size={13} />
          </button>
        </div>
      </div>

      {call.summary && !editing && (
        <div style={{ margin: '10px 16px 0', padding: '9px 12px', background: 'rgba(37,99,235,.06)', border: '1px solid rgba(37,99,235,.2)', borderRadius: 8, font: '400 11px/1.55 var(--font)', color: 'var(--text2)', flexShrink: 0 }}>
          {call.summary}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {editing ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ font: '700 10px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 2 }}>Edit Details</div>

            {[
              { key: 'incident', label: 'Incident',  icon: <Radio size={11} color="var(--text3)" /> },
              { key: 'name',     label: 'Caller',    icon: <User  size={11} color="var(--text3)" /> },
              { key: 'phone',    label: 'Phone',     icon: <Phone size={11} color="var(--text3)" /> },
              { key: 'address',  label: 'Address',   icon: <MapPin size={11} color="var(--text3)" /> },
            ].map(f => (
              <div key={f.key} style={{ padding: '8px 10px', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 5 }}>
                  {f.icon}
                  <span style={{ font: '500 9px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.05em' }}>{f.label}</span>
                </div>
                <input
                  style={inputStyle}
                  value={editFields[f.key]}
                  onChange={e => setEditFields(p => ({ ...p, [f.key]: e.target.value }))}
                />
              </div>
            ))}

            <div style={{ padding: '8px 10px', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 5 }}>
                <FileText size={11} color="var(--text3)" />
                <span style={{ font: '500 9px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.05em' }}>Summary</span>
              </div>
              <textarea
                style={{ ...inputStyle, resize: 'vertical', minHeight: 72, lineHeight: 1.55 }}
                value={editFields.summary}
                onChange={e => setEditFields(p => ({ ...p, summary: e.target.value }))}
              />
            </div>

            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={saveEdits} style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '9px 14px', background: 'var(--blue)', border: 'none', borderRadius: 7,
                cursor: 'pointer', font: '600 13px var(--font)', color: '#fff',
              }}>
                <Check size={14} color="#fff" /> Save
              </button>
              <button onClick={() => setEditing(false)} style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '9px 14px', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 7,
                cursor: 'pointer', font: '600 13px var(--font)', color: 'var(--text2)',
              }}>
                <X size={14} /> Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {[
                { icon: <Phone size={11} color="var(--text3)" />,  label: 'Phone',    value: call.phone },
                { icon: <Clock size={11} color="var(--text3)" />,  label: 'Duration', value: fmt(call.callDuration) },
                { icon: <User size={11} color="var(--text3)" />,   label: 'Caller',   value: call.name || 'Unknown' },
                { icon: <MapPin size={11} color="var(--text3)" />, label: 'Address',  value: addressDisplay },
              ].map(r => (
                <div key={r.label} style={{ padding: '8px 10px', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 3 }}>
                    {r.icon}
                    <span style={{ font: '500 9px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.05em' }}>{r.label}</span>
                  </div>
                  <div style={{ font: '600 11px var(--font)', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.value}</div>
                </div>
              ))}
            </div>

            {call.status !== 'resolved' && call.status !== 'transferred' && (
              <button onClick={() => onTransfer(call.id)} style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                padding: '9px 14px', background: '#7c3aed', border: 'none', borderRadius: 7,
                cursor: 'pointer', font: '600 13px var(--font)', color: '#fff',
              }}>
                <PhoneForwarded size={14} color="#fff" />
                Transfer Call
              </button>
            )}

            {call.status === 'transferred' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ padding: '11px 13px', background: 'rgba(124,58,237,.08)', border: '1px solid rgba(124,58,237,.3)', borderRadius: 9, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <PhoneForwarded size={15} color="#7c3aed" />
                  <div>
                    <div style={{ font: '600 12px var(--font)', color: '#7c3aed' }}>Call Transferred</div>
                    <div style={{ font: '400 10px var(--font)', color: 'var(--text3)', marginTop: 2 }}>Now handled by live operator</div>
                  </div>
                </div>
                <button onClick={startEditing} style={{
                  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  padding: '9px 14px', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 7,
                  cursor: 'pointer', font: '600 13px var(--font)', color: 'var(--text)',
                }}>
                  <Pencil size={14} color="var(--text2)" />
                  Edit Incident Details
                </button>
              </div>
            )}
          </>
        )}

        <div>
          <div style={{ font: '700 10px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 8 }}>Dispatch Units</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {DISPATCH_OPTS.map(opt => {
              const Icon        = opt.icon;
              const sent        = call.dispatched?.includes(opt.type);
              const confirming  = confirm === opt.type;
              const recommended = call.recommended_dispatch?.includes(opt.type);

              if (confirming) return (
                <div key={opt.type} style={{ padding: '9px 12px', background: `${opt.color}12`, border: `1px solid ${opt.color}45`, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ font: '500 12px var(--font)', color: opt.color, flex: 1 }}>Dispatch {opt.label}?</span>
                  <button onClick={() => { onDispatch(call.id, opt.type); setConfirm(null); }} style={{ padding: '4px 12px', background: opt.color, border: 'none', borderRadius: 5, cursor: 'pointer', font: '600 12px var(--font)', color: '#fff' }}>Yes</button>
                  <button onClick={() => setConfirm(null)} style={{ padding: '4px 10px', background: 'none', border: '1px solid var(--border)', borderRadius: 5, cursor: 'pointer', font: '400 12px var(--font)', color: 'var(--text3)' }}>No</button>
                </div>
              );

              return (
                <button key={opt.type} onClick={() => !sent && setConfirm(opt.type)} style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
                  background: sent ? `${opt.color}0e` : 'var(--surface2)',
                  border: `1px solid ${sent ? opt.color + '40' : recommended ? opt.color + '55' : 'var(--border)'}`,
                  borderRadius: 8, cursor: sent ? 'default' : 'pointer',
                  transition: 'all .15s', width: '100%',
                }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: sent ? opt.color : `${opt.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={13} color={sent ? '#fff' : opt.color} />
                  </div>
                  <span style={{ font: '600 13px var(--font)', color: sent ? opt.color : 'var(--text)', flex: 1, textAlign: 'left' }}>{opt.label}</span>
                  {recommended && !sent && <span style={{ font: '500 9px var(--font)', color: opt.color, background: `${opt.color}15`, padding: '2px 5px', borderRadius: 3 }}>AI rec.</span>}
                  {sent ? <Check size={13} color={opt.color} /> : <Send size={12} color="var(--text3)" />}
                </button>
              );
            })}
          </div>
        </div>
        <div>
          <button onClick={() => setShowTx(v => !v)} style={{
            width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '9px 12px', background: 'var(--surface2)', border: '1px solid var(--border)',
            borderRadius: 8, cursor: 'pointer', marginBottom: showTx ? 7 : 0,
            font: '500 12px var(--font)', color: 'var(--text2)',
          }}>
            Transcript ({call.transcript?.length || 0})
            <ChevronDown size={13} style={{ transform: showTx ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
          </button>
          {showTx && (call.transcript?.length > 0 ? call.transcript.map((e, i) => {
            const isAI = e.role === 'assistant';
            return (
              <div key={i} style={{
                padding: '8px 11px',
                background: isAI ? 'rgba(37,99,235,.05)' : 'var(--surface2)',
                border: `1px solid ${isAI ? 'rgba(37,99,235,.2)' : 'var(--border)'}`,
                borderRadius: 7, marginBottom: 5,
              }}>
                <div style={{
                  font: '600 9px var(--font)',
                  color: isAI ? 'var(--blue)' : 'var(--orange)',
                  textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 3,
                }}>
                  {isAI ? 'Vigil AI' : 'Caller'}
                </div>
                <p style={{ font: '400 12px/1.55 var(--font)', color: 'var(--text2)', margin: 0 }}>{e.text}</p>
              </div>
            );
          }) : (
            <div style={{ padding: '10px 12px', font: '400 11px var(--font)', color: 'var(--text3)', textAlign: 'center' }}>
              No transcript yet…
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

export default function Dashboard() {
  const [calls, setCalls]           = useState([]);
  const [selected, setSelected]     = useState(null);
  const [dark, setDark]             = useState(false);
  const [toast, setToast]           = useState(null);
  const [time, setTime]             = useState('');
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortBy, setSortBy]         = useState('severity');
  const [filterStatus, setFilterStatus] = useState('all');
  const [apiError, setApiError]     = useState(false);

  const selectedRef      = useRef(selected);
  const callsRef         = useRef(calls);
  const hasAutoSelected  = useRef(false);
  const userHasPickedRef = useRef(false);
  selectedRef.current = selected;
  callsRef.current    = calls;

  const handleUserSelect = (id) => { userHasPickedRef.current = true; setSelected(id); };
  const handleMapSelect  = (id) => { if (!userHasPickedRef.current) setSelected(id); };

  useEffect(() => {
    if (dark) document.documentElement.setAttribute('data-dark', '');
    else       document.documentElement.removeAttribute('data-dark');
  }, [dark]);

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const t = setInterval(() => {
      setCalls(prev =>
        prev.map(c =>
          c.status === 'active' || c.status === 'dispatched'
            ? { ...c, callDuration: c.callDuration + 1 }
            : c
        )
      );
    }, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const fetchCalls = async () => {
      try {
        const res  = await fetch(`${API_URL}/api/calls`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setCalls(prev => {
            const prevMap = Object.fromEntries(prev.map(c => [c.id, c]));
            return data.map(serverCall => {
              const local  = prevMap[serverCall.id];
              const isLive = serverCall.status === 'active' || serverCall.status === 'dispatched';
              return {
                ...serverCall,
                callDuration: (local && isLive) ? local.callDuration : serverCall.callDuration,
              };
            });
          });
          setApiError(false);
          if (!hasAutoSelected.current && !selectedRef.current && data.length > 0) {
            hasAutoSelected.current  = true;
            userHasPickedRef.current = true;
            setSelected(data[0].id);
          }
        }
      } catch (err) {
        if (!cancelled) { console.error('Failed to fetch calls:', err); setApiError(true); }
      }
    };
    fetchCalls();
    const t = setInterval(fetchCalls, POLL_INTERVAL_MS);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  const transfer = async (callId) => {
    try {
      await fetch(`${API_URL}/transfer-call`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ call_sid: callId }),
      });
      const num = callsRef.current.find(c => c.id === callId)?.call_number ?? callId.slice(-4);
      setCalls(p => p.map(c => c.id === callId ? { ...c, status: 'transferred' } : c));
      showToast(`Call #${num} transferred to your device`);
    } catch (err) { console.error('Transfer failed:', err); }
  };

  const dispatch = async (callId, type) => {
    try {
      await fetch(`${API_URL}/dispatch`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ call_sid: callId, type }),
      });
      const num = callsRef.current.find(c => c.id === callId)?.call_number ?? callId.slice(-4);
      setCalls(p => p.map(c =>
        c.id === callId
          ? { ...c, dispatched: [...new Set([...(c.dispatched || []), type])], status: 'dispatched' }
          : c
      ));
      showToast(`${type.charAt(0).toUpperCase() + type.slice(1)} dispatched to Call #${num}`);
    } catch (err) { console.error('Dispatch failed:', err); }
  };

  const updateCall = (callId, fields) => {
    setCalls(p => p.map(c => c.id === callId ? { ...c, ...fields } : c));
    showToast('Incident details updated');
  };

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3500); };

  const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

  const filtered = calls.filter(c => {
    if (filterStatus === 'all')        return true;
    if (filterStatus === 'active')     return c.status === 'active';
    if (filterStatus === 'dispatched') return c.status === 'dispatched';
    if (filterStatus === 'resolved')   return c.status === 'resolved' || c.status === 'transferred';
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'severity')      return (SEV_ORDER[a.severity] ?? 2) - (SEV_ORDER[b.severity] ?? 2);
    if (sortBy === 'duration_asc')  return a.callDuration - b.callDuration;
    if (sortBy === 'duration_desc') return b.callDuration - a.callDuration;
    if (sortBy === 'recent')        return b.callDuration - a.callDuration;
    return 0;
  });

  const mapCallsKey = calls
    .map(c => `${c.id}:${c.location?.lat}:${c.location?.lng}:${c.severity}:${c.status}:${c.call_number}`)
    .join('|');

  const mapCalls = useMemo(
    () => calls.map(({ id, call_number, location, severity, status }) => ({ id, call_number, location, severity, status })),
    [mapCallsKey]
  );

  const selectedCall = calls.find(c => c.id === selected) || null;
  const liveCount    = calls.filter(c => c.status === 'active').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>

      <Topbar dark={dark} toggle={() => setDark(d => !d)} time={time} liveCount={liveCount} />

      {apiError && (
        <div style={{ background: 'rgba(220,38,38,.1)', borderBottom: '1px solid rgba(220,38,38,.3)', padding: '7px 20px', font: '500 12px var(--font)', color: '#dc2626', textAlign: 'center' }}>
          Cannot reach backend at {API_URL} — check that main.py is running
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        <div style={{ width: 290, flexShrink: 0, background: 'var(--surface)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: filterOpen ? 12 : 0 }}>
              <div>
                <div style={{ font: '700 13px var(--font)', color: 'var(--text)' }}>Incidents</div>
                <div style={{ font: '400 10px var(--font)', color: 'var(--text3)', marginTop: 2 }}>{sorted.length} showing · {liveCount} live</div>
              </div>
              <button onClick={() => setFilterOpen(v => !v)} style={{
                display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7,
                background: filterOpen ? 'var(--blue)' : 'var(--surface2)',
                border: `1px solid ${filterOpen ? 'var(--blue)' : 'var(--border)'}`,
                cursor: 'pointer', color: filterOpen ? '#fff' : 'var(--text2)', font: '500 11px var(--font)',
              }}>
                <SlidersHorizontal size={12} />
                Filter
                {(sortBy !== 'severity' || filterStatus !== 'all') && (
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: filterOpen ? '#fff' : 'var(--blue)', marginLeft: 2 }} />
                )}
              </button>
            </div>

            {filterOpen && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <div style={{ font: '600 9px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 5 }}>Sort by</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {[
                      { val: 'severity',      label: 'Criticality' },
                      { val: 'duration_desc', label: 'Longest call' },
                      { val: 'duration_asc',  label: 'Shortest call' },
                      { val: 'recent',        label: 'Most recent' },
                    ].map(o => (
                      <button key={o.val} onClick={() => setSortBy(o.val)} style={{
                        padding: '4px 9px', borderRadius: 5,
                        background: sortBy === o.val ? 'var(--blue)' : 'var(--surface2)',
                        border: `1px solid ${sortBy === o.val ? 'var(--blue)' : 'var(--border)'}`,
                        color: sortBy === o.val ? '#fff' : 'var(--text2)', font: '500 11px var(--font)', cursor: 'pointer',
                      }}>{o.label}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ font: '600 9px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 5 }}>Show</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {[
                      { val: 'all', label: 'All' }, { val: 'active', label: 'Live only' },
                      { val: 'dispatched', label: 'Dispatched' }, { val: 'resolved', label: 'Resolved' },
                    ].map(o => (
                      <button key={o.val} onClick={() => setFilterStatus(o.val)} style={{
                        padding: '4px 9px', borderRadius: 5,
                        background: filterStatus === o.val ? 'var(--blue)' : 'var(--surface2)',
                        border: `1px solid ${filterStatus === o.val ? 'var(--blue)' : 'var(--border)'}`,
                        color: filterStatus === o.val ? '#fff' : 'var(--text2)', font: '500 11px var(--font)', cursor: 'pointer',
                      }}>{o.label}</button>
                    ))}
                  </div>
                </div>
                {(sortBy !== 'severity' || filterStatus !== 'all') && (
                  <button onClick={() => { setSortBy('severity'); setFilterStatus('all'); }} style={{
                    padding: '4px 9px', borderRadius: 5, alignSelf: 'flex-start',
                    background: 'none', border: '1px solid var(--border)', color: 'var(--text3)', font: '500 11px var(--font)', cursor: 'pointer',
                  }}>Reset filters</button>
                )}
              </div>
            )}
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {sorted.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', font: '400 12px var(--font)', color: 'var(--text3)' }}>
                {calls.length === 0 ? 'No calls yet. Waiting for incoming calls…' : 'No calls match the current filter.'}
              </div>
            ) : sorted.map(c => (
              <CallCard key={c.id} call={c} selected={selected === c.id} onSelect={handleUserSelect} />
            ))}
          </div>
        </div>

        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <Map calls={mapCalls} selectedId={selected} onSelect={handleMapSelect} dark={dark} />
        </div>

        <div style={{ width: 320, flexShrink: 0, background: 'var(--surface)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <div style={{ font: '700 13px var(--font)', color: 'var(--text)' }}>Incident Detail</div>
            <div style={{ font: '400 10px var(--font)', color: 'var(--text3)', marginTop: 2 }}>
              {selectedCall ? `Last updated ${new Date().toLocaleTimeString()}` : 'Select a call to view'}
            </div>
          </div>
          <Detail
            call={selectedCall}
            onDispatch={dispatch}
            onTransfer={transfer}
            onClose={() => setSelected(null)}
            onUpdate={updateCall}
          />
        </div>

      </div>

      {toast && (
        <div className="fadeup" style={{
          position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--surface)', border: '1px solid var(--green)',
          borderRadius: 10, padding: '9px 18px',
          font: '500 13px var(--font)', color: 'var(--green)',
          boxShadow: 'var(--shadow-lg)', zIndex: 9999,
          display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap',
        }}>
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--green)' }} />
          {toast}
        </div>
      )}

    </div>
  );
}