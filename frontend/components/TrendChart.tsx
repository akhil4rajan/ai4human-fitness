"use client";

import { useState } from "react";

export interface Point { label: string; value: number }

const W = 320, H = 120, PAD = { l: 34, r: 10, t: 10, b: 20 };

/** Single-series line chart: 2px line, 8px end marker with surface ring, hairline grid,
 *  pointer/keyboard tooltip. Identity comes from the title; text never wears the series color. */
export default function TrendChart({ title, unit, points }: { title: string; unit: string; points: Point[] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (points.length === 0) {
    return (
      <figure className="rounded-lg border border-border bg-surface p-4">
        <figcaption className="text-sm font-medium">{title}</figcaption>
        <p className="mt-2 text-sm text-muted">No data yet.</p>
      </figure>
    );
  }
  const vals = points.map((p) => p.value);
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (lo === hi) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
  const x = (i: number) => PAD.l + (points.length === 1 ? (W - PAD.l - PAD.r) / 2 : (i / (points.length - 1)) * (W - PAD.l - PAD.r));
  const y = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo)) * (H - PAD.t - PAD.b);
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const last = points.length - 1;
  const active = hover ?? last;
  const fmt = (v: number) => `${Math.round(v * 10) / 10}${unit}`;
  const ticks = [lo + pad, (lo + hi) / 2, hi - pad];

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = 0;
    points.forEach((_, i) => { if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i; });
    setHover(best);
  }

  return (
    <figure className="rounded-lg border border-border bg-surface p-4">
      <figcaption className="flex items-baseline justify-between text-sm">
        <span className="font-medium">{title}</span>
        <span className="text-muted" aria-live="polite">{points[active].label}: <strong className="text-foreground">{fmt(points[active].value)}</strong></span>
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${title} trend, latest ${fmt(points[last].value)}`}
        tabIndex={0}
        className="mt-2 w-full touch-none"
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") setHover(Math.max(0, active - 1));
          if (e.key === "ArrowRight") setHover(Math.min(last, active + 1));
          if (e.key === "Escape") setHover(null);
        }}
      >
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="var(--grid)" strokeWidth={1} />
            <text x={PAD.l - 6} y={y(t) + 3} textAnchor="end" fontSize={9} fill="var(--muted)">{Math.round(t * 10) / 10}</text>
          </g>
        ))}
        <text x={PAD.l} y={H - 4} fontSize={9} fill="var(--muted)">{points[0].label}</text>
        {points.length > 1 && <text x={W - PAD.r} y={H - 4} fontSize={9} textAnchor="end" fill="var(--muted)">{points[last].label}</text>}
        <path d={path} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={H - PAD.b} stroke="var(--muted)" strokeWidth={1} />}
        <circle cx={x(active)} cy={y(points[active].value)} r={4} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
      </svg>
      <details className="mt-2 text-xs text-muted">
        <summary className="cursor-pointer">View as table</summary>
        <table className="mt-1 w-full text-left">
          <thead><tr><th scope="col">Date</th><th scope="col">{title}</th></tr></thead>
          <tbody>{points.map((p, i) => <tr key={i}><td>{p.label}</td><td>{fmt(p.value)}</td></tr>)}</tbody>
        </table>
      </details>
    </figure>
  );
}
