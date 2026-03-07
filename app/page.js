'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import {
  Eye, Sun, Moon, SlidersHorizontal,
  ShieldCheck, Flame, Ambulance, Wrench, AlertTriangle,
  MapPin, Clock, Heart, Phone, User, ChevronDown, Send, Check, X, PhoneForwarded
} from 'lucide-react';
import { MOCK_CALLS } from '../data/mockCalls';

const Map = dynamic(() => import('../components/Map'), { ssr: false, loading: () => (
  <div style={{ width: '100%', height: '100%', background: 'var(--surface2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <span style={{ font: '12px var(--font)', color: 'var(--text3)' }}>Loading map…</span>
  </div>
) });

const SEV = {
  critical: { color: '#dc2626', bg: 'rgba(220,38,38,.1)',  label: 'Critical' },
  high:     { color: '#ea580c', bg: 'rgba(234,88,12,.1)',  label: 'High' },
  medium:   { color: '#d97706', bg: 'rgba(217,119,6,.1)',  label: 'Medium' },
  low:      { color: '#16a34a', bg: 'rgba(22,163,74,.1)',  label: 'Low' },
};

const STAT = {
  active:     { color: '#16a34a', label: 'Live' },
  pending:    { color: '#d97706', label: 'Queued' },
  dispatched: { color: '#2563eb', label: 'Dispatched' },
  resolved:   { color: '#94a3b8', label: 'Resolved' },
  transferred: { color: '#7c3aed', label: 'Transferred' },
};

const EMOTIONAL = {
  calm:        { color: '#16a34a', label: 'Calm' },
  distressed:  { color: '#d97706', label: 'Distressed' },
  panic:       { color: '#dc2626', label: 'Panicking' },
  unresponsive:{ color: '#94a3b8', label: 'Unresponsive' },
};

const DISPATCH_OPTS = [
  { type: 'police',    label: 'Police',    color: '#2563eb', icon: ShieldCheck },
  { type: 'fire',      label: 'Fire Dept', color: '#ea580c', icon: Flame },
  { type: 'ambulance', label: 'Ambulance', color: '#dc2626', icon: Ambulance },
  { type: 'hazmat',    label: 'Hazmat',    color: '#d97706', icon: AlertTriangle },
  { type: 'rescue',    label: 'Rescue',    color: '#16a34a', icon: Wrench },
];

function fmt(s) {
  return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
}

// ─── Topbar ───────────────────────────────────────────────────────────────────
function Topbar({ dark, toggle, time }) {
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
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Eye size={15} color="#fff" />
        </div>
        <div>
          <div style={{ font: '700 15px var(--font)', color: 'var(--text)', lineHeight: 1 }}>Vigil</div>
          <div style={{ font: '500 9px var(--font)', color: 'var(--text3)', letterSpacing: '.07em', textTransform: 'uppercase' }}>Dispatch Intelligence</div>
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Clock */}
      <span style={{ font: '600 14px var(--font)', color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{time}</span>

      <div style={{ width: 1, height: 28, background: 'var(--border)' }} />

      {/* Theme */}
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

// ─── Call card ────────────────────────────────────────────────────────────────
function CallCard({ call, selected, onSelect }) {
  const sev = SEV[call.severity];
  const stat = STAT[call.status];
  const isLive = call.status === 'active';

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
          <span style={{ font: '400 10px var(--font)', color: 'var(--text3)' }}>#{call.id}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          {isLive && <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', animation: 'blink 1.2s step-end infinite' }} />}
          <span style={{ font: '500 10px var(--font)', color: stat.color }}>{stat.label}</span>
        </div>
      </div>

      <div style={{ font: '600 12px/1.35 var(--font)', color: 'var(--text)', marginBottom: 5 }}>{call.incident}</div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 3, marginBottom: 5 }}>
        <MapPin size={9} color="var(--text3)" />
        <span style={{ font: '400 10px var(--font)', color: 'var(--text3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {call.location.address}
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <Clock size={9} color="var(--text3)" />
          <span style={{ font: '400 10px var(--font)', color: 'var(--text3)' }}>{fmt(call.callDuration)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: EMOTIONAL[call.emotionalState].color }} />
          <span style={{ font: '400 10px var(--font)', color: 'var(--text3)', textTransform: 'capitalize' }}>{call.emotionalState}</span>
        </div>
      </div>

      {isLive && (
        <div style={{ marginTop: 7, padding: '5px 8px', background: 'rgba(22,163,74,.07)', border: '1px solid rgba(22,163,74,.18)', borderRadius: 5, font: '500 10px var(--font)', color: 'var(--green)' }}>
          ◈ {call.aiStep}
        </div>
      )}
    </div>
  );
}

// ─── Detail panel ─────────────────────────────────────────────────────────────
function Detail({ call, onDispatch, onTransfer, onClose }) {
  const [confirm, setConfirm] = useState(null);
  const [showTx, setShowTx] = useState(false);

  if (!call) return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 24 }}>
      <div style={{ width: 44, height: 44, borderRadius: 10, background: 'var(--surface2)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <MapPin size={20} color="var(--text3)" />
      </div>
      <span style={{ font: '500 12px var(--font)', color: 'var(--text3)' }}>Select an incident</span>
    </div>
  );

  const sev = SEV[call.severity];
  const emo = EMOTIONAL[call.emotionalState];
  const emoLevel = { panic: 5, distressed: 3, unresponsive: 1, calm: 2 }[call.emotionalState] || 2;

  return (
    <div className="slidein" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Accent bar */}
      <div style={{ height: 3, background: sev.color, flexShrink: 0 }} />

      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: sev.color }} />
              <span style={{ font: '700 14px var(--font)', color: 'var(--text)' }}>Incident #{call.id}</span>
            </div>
            <div style={{ font: '500 11px/1.4 var(--font)', color: 'var(--text2)', paddingLeft: 15 }}>{call.incident}</div>
          </div>
          <button onClick={onClose} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, padding: 5, cursor: 'pointer', color: 'var(--text3)', display: 'flex' }}>
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* Quick info */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {[
            { icon: <Phone size={11} color="var(--text3)" />, label: 'Phone', value: call.phone },
            { icon: <Clock size={11} color="var(--text3)" />, label: 'Duration', value: fmt(call.callDuration) },
            { icon: <User size={11} color="var(--text3)" />, label: 'Caller', value: call.name || 'Unknown' },
            { icon: <MapPin size={11} color="var(--text3)" />, label: 'Address', value: call.location.address.split(',')[0] },
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

        {/* Emotional state */}
        <div style={{ padding: '10px 12px', background: `${emo.color}0f`, border: `1px solid ${emo.color}28`, borderRadius: 9, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Heart size={14} color={emo.color} />
          <div style={{ flex: 1 }}>
            <div style={{ font: '600 12px var(--font)', color: emo.color }}>{emo.label}</div>
          </div>
          <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
            {[1,2,3,4,5].map(i => (
              <div key={i} style={{ width: 5, borderRadius: 3, height: 8 + i*3, background: i <= emoLevel ? emo.color : 'var(--border)' }} />
            ))}
          </div>
        </div>

        {/* AI summary */}
        <div style={{ padding: '11px 13px', background: 'rgba(22,163,74,.06)', border: '1px solid rgba(22,163,74,.2)', borderRadius: 9 }}>
          <div style={{ font: '700 9px var(--font)', color: 'var(--green)', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 6 }}>◈ AI Assessment</div>
          <p style={{ font: '400 12px/1.6 var(--font)', color: 'var(--text2)', marginBottom: 8 }}>{call.aiSummary}</p>
          <div style={{ borderTop: '1px solid rgba(22,163,74,.15)', paddingTop: 8, font: '500 11px var(--font)', color: 'var(--green)' }}>
            → {call.aiStep}
          </div>
        </div>


        {/* Transfer Call */}
        {call.status !== 'resolved' && call.status !== 'transferred' && (
          <div style={{ padding: '11px 13px', background: 'rgba(124,58,237,.06)', border: '1px solid rgba(124,58,237,.2)', borderRadius: 9 }}>
            <div style={{ font: '700 9px var(--font)', color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 6 }}>
              Hand Off to Operator
            </div>
            <p style={{ font: '400 11px/1.5 var(--font)', color: 'var(--text2)', marginBottom: 10 }}>
              Transfer this call from AI assistance to a live operator. The operator will take over and continue assisting the caller directly.
            </p>
            <button
              onClick={() => onTransfer(call.id)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                padding: '9px 14px',
                background: '#7c3aed', border: 'none', borderRadius: 7,
                cursor: 'pointer', font: '600 13px var(--font)', color: '#fff',
              }}
            >
              <PhoneForwarded size={14} color="#fff" />
              Transfer Call to My Device
            </button>
          </div>
        )}

        {call.status === 'transferred' && (
          <div style={{ padding: '11px 13px', background: 'rgba(124,58,237,.08)', border: '1px solid rgba(124,58,237,.3)', borderRadius: 9, display: 'flex', alignItems: 'center', gap: 10 }}>
            <PhoneForwarded size={15} color="#7c3aed" />
            <div>
              <div style={{ font: '600 12px var(--font)', color: '#7c3aed' }}>Call Transferred</div>
              <div style={{ font: '400 10px var(--font)', color: 'var(--text3)', marginTop: 2 }}>Now handled by live operator</div>
            </div>
          </div>
        )}

        {/* Dispatch */}
        <div>
          <div style={{ font: '700 10px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 8 }}>Dispatch Units</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {DISPATCH_OPTS.map(opt => {
              const Icon = opt.icon;
              const sent = call.dispatched.includes(opt.type);
              const confirming = confirm === opt.type;

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
                  border: `1px solid ${sent ? opt.color + '40' : 'var(--border)'}`,
                  borderRadius: 8, cursor: sent ? 'default' : 'pointer',
                  transition: 'all .15s', width: '100%',
                }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: sent ? opt.color : `${opt.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={13} color={sent ? '#fff' : opt.color} />
                  </div>
                  <span style={{ font: '600 13px var(--font)', color: sent ? opt.color : 'var(--text)', flex: 1, textAlign: 'left' }}>{opt.label}</span>
                  {sent ? <Check size={13} color={opt.color} /> : <Send size={12} color="var(--text3)" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Transcript */}
        <div>
          <button onClick={() => setShowTx(v => !v)} style={{
            width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '9px 12px', background: 'var(--surface2)', border: '1px solid var(--border)',
            borderRadius: 8, cursor: 'pointer', marginBottom: showTx ? 7 : 0,
            font: '500 12px var(--font)', color: 'var(--text2)',
          }}>
            Transcript ({call.transcript.length})
            <ChevronDown size={13} style={{ transform: showTx ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
          </button>
          {showTx && call.transcript.map((e, i) => (
            <div key={i} style={{ padding: '8px 11px', background: e.role === 'ai' ? 'rgba(22,163,74,.05)' : 'var(--surface2)', border: `1px solid ${e.role === 'ai' ? 'rgba(22,163,74,.18)' : 'var(--border)'}`, borderRadius: 7, marginBottom: 5 }}>
              <div style={{ font: '600 9px var(--font)', color: e.role === 'ai' ? 'var(--green)' : 'var(--orange)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 3 }}>
                {e.role === 'ai' ? '◈ Vigil AI' : '↗ Caller'} · {e.time}
              </div>
              <p style={{ font: '400 12px/1.55 var(--font)', color: 'var(--text2)' }}>{e.text}</p>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

// ─── Main dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [calls, setCalls] = useState(MOCK_CALLS);
  const [selected, setSelected] = useState('C001');
  const [dark, setDark] = useState(false);
  const [toast, setToast] = useState(null);
  const [time, setTime] = useState('');
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortBy, setSortBy] = useState('severity');
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    if (dark) document.documentElement.setAttribute('data-dark', '');
    else document.documentElement.removeAttribute('data-dark');
  }, [dark]);

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const t = setInterval(() => setCalls(p => p.map(c =>
      c.status === 'active' || c.status === 'dispatched' ? { ...c, callDuration: c.callDuration + 1 } : c
    )), 1000);
    return () => clearInterval(t);
  }, []);

  const transfer = (callId) => {
    setCalls(p => p.map(c => c.id === callId ? { ...c, status: 'transferred' } : c));
    setToast(`Call #${callId} transferred to your device`);
    setTimeout(() => setToast(null), 3500);
  };

  const dispatch = (callId, type) => {
    setCalls(p => p.map(c => c.id === callId ? { ...c, dispatched: [...new Set([...c.dispatched, type])], status: 'dispatched' } : c));
    setToast(`${type.charAt(0).toUpperCase() + type.slice(1)} dispatched to #${callId}`);
    setTimeout(() => setToast(null), 3500);
  };

  const SEV_ORDER = { critical:0, high:1, medium:2, low:3 };
  const filtered = calls.filter(c => {
    if (filterStatus === 'all') return true;
    if (filterStatus === 'active') return c.status === 'active';
    if (filterStatus === 'dispatched') return c.status === 'dispatched';
    if (filterStatus === 'resolved') return c.status === 'resolved' || c.status === 'transferred';
    return true;
  });
  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'severity') return SEV_ORDER[a.severity] - SEV_ORDER[b.severity];
    if (sortBy === 'duration_asc') return a.callDuration - b.callDuration;
    if (sortBy === 'duration_desc') return b.callDuration - a.callDuration;
    if (sortBy === 'recent') return b.callDuration - a.callDuration;
    return 0;
  });
  const selectedCall = calls.find(c => c.id === selected) || null;
  const active = calls.filter(c => c.status === 'active' || c.status === 'dispatched').length;
  const critical = calls.filter(c => c.severity === 'critical').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>

      <Topbar dark={dark} toggle={() => setDark(d => !d)} time={time} />

      {/* 3-column body */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* LEFT — incident list */}
        <div style={{ width: 290, flexShrink: 0, background: 'var(--surface)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* List header */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: filterOpen ? 12 : 0 }}>
              <div>
                <div style={{ font: '700 13px var(--font)', color: 'var(--text)' }}>Incidents</div>
                <div style={{ font: '400 10px var(--font)', color: 'var(--text3)', marginTop: 2 }}>
                  {sorted.length} showing · {calls.filter(c => c.status === 'active').length} live
                </div>
              </div>
              <button
                onClick={() => setFilterOpen(v => !v)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  padding: '5px 10px', borderRadius: 7,
                  background: filterOpen ? 'var(--blue)' : 'var(--surface2)',
                  border: `1px solid ${filterOpen ? 'var(--blue)' : 'var(--border)'}`,
                  cursor: 'pointer', color: filterOpen ? '#fff' : 'var(--text2)',
                  font: '500 11px var(--font)',
                }}
              >
                <SlidersHorizontal size={12} />
                Filter
                {(sortBy !== 'severity' || filterStatus !== 'all') && (
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: filterOpen ? '#fff' : 'var(--blue)', marginLeft: 2 }} />
                )}
              </button>
            </div>

            {/* Filter panel */}
            {filterOpen && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Sort by */}
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
                        color: sortBy === o.val ? '#fff' : 'var(--text2)',
                        font: '500 11px var(--font)', cursor: 'pointer',
                      }}>{o.label}</button>
                    ))}
                  </div>
                </div>
                {/* Filter by status */}
                <div>
                  <div style={{ font: '600 9px var(--font)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 5 }}>Show</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {[
                      { val: 'all',        label: 'All' },
                      { val: 'active',     label: 'Live only' },
                      { val: 'dispatched', label: 'Dispatched' },
                      { val: 'resolved',   label: 'Resolved' },
                    ].map(o => (
                      <button key={o.val} onClick={() => setFilterStatus(o.val)} style={{
                        padding: '4px 9px', borderRadius: 5,
                        background: filterStatus === o.val ? 'var(--blue)' : 'var(--surface2)',
                        border: `1px solid ${filterStatus === o.val ? 'var(--blue)' : 'var(--border)'}`,
                        color: filterStatus === o.val ? '#fff' : 'var(--text2)',
                        font: '500 11px var(--font)', cursor: 'pointer',
                      }}>{o.label}</button>
                    ))}
                  </div>
                </div>
                {/* Reset */}
                {(sortBy !== 'severity' || filterStatus !== 'all') && (
                  <button onClick={() => { setSortBy('severity'); setFilterStatus('all'); }} style={{
                    padding: '4px 9px', borderRadius: 5, alignSelf: 'flex-start',
                    background: 'none', border: '1px solid var(--border)',
                    color: 'var(--text3)', font: '500 11px var(--font)', cursor: 'pointer',
                  }}>Reset filters</button>
                )}
              </div>
            )}
          </div>
          {/* Cards */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {sorted.map(c => (
              <CallCard key={c.id} call={c} selected={selected === c.id} onSelect={setSelected} />
            ))}
          </div>
        </div>

        {/* CENTER — map */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <Map calls={calls} selectedId={selected} onSelect={setSelected} dark={dark} />
        </div>

        {/* RIGHT — detail */}
        <div style={{ width: 320, flexShrink: 0, background: 'var(--surface)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Right header */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <div style={{ font: '700 13px var(--font)', color: 'var(--text)' }}>Incident Detail</div>
            <div style={{ font: '400 10px var(--font)', color: 'var(--text3)', marginTop: 2 }}>Select a call to view</div>
          </div>
          <Detail call={selectedCall} onDispatch={dispatch} onTransfer={transfer} onClose={() => setSelected(null)} />
        </div>

      </div>

      {/* Toast */}
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