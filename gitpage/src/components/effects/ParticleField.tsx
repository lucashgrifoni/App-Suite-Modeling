import { useEffect, useRef } from "react";
import { tokens } from "../../lib/tokens";
import { useReducedMotion } from "../../hooks/useReducedMotion";

/** Mint / neutral canvas specks plus sparse red “threat” accents (matches semantic danger). */
type ParticleKind = "mint" | "steel" | "danger";

type Particle = {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  r: number;
  kind: ParticleKind;
};

/** ~14% red specks — visible on dark hero without overwhelming mint palette. */
const DANGER_FRACTION = 0.14;

function pickParticleKind(z: number, roll: number): ParticleKind {
  if (roll < DANGER_FRACTION) return "danger";
  if (z > 0.55) return "mint";
  return "steel";
}

/**
 * Lightweight canvas particle layer — depth via parallax on pointer move (desktop).
 */
export function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || reduced) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let particles: Particle[] = [];
    let w = 0;
    let h = 0;
    let mx = 0;
    let my = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(120, Math.floor((w * h) / 18000));
      particles = Array.from({ length: count }, () => {
        const z = Math.random();
        const kind = pickParticleKind(z, Math.random());
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          z,
          vx: (Math.random() - 0.5) * 0.25,
          vy: (Math.random() - 0.5) * 0.25,
          r: (kind === "danger" ? 1.15 : 1) * (Math.random() * 1.8 + 0.4),
          kind,
        };
      });
    };

    const onMove = (e: MouseEvent) => {
      mx = (e.clientX / w - 0.5) * 2;
      my = (e.clientY / h - 0.5) * 2;
    };

    const tick = () => {
      ctx.clearRect(0, 0, w, h);
      const parallaxX = mx * 18;
      const parallaxY = my * 12;

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        const alpha = 0.15 + p.z * 0.55;
        const px = p.x + parallaxX * p.z;
        const py = p.y + parallaxY * p.z;
        ctx.beginPath();
        if (p.kind === "danger") {
          const a = Math.min(0.95, alpha * 0.95 + 0.12);
          // semantic.dangerStrong #ef4444 — canvas fill (8-digit hex support varies)
          ctx.fillStyle = `rgba(239, 68, 68, ${a})`;
        } else if (p.kind === "mint") {
          ctx.fillStyle = `rgba(8, 185, 139, ${alpha})`;
        } else {
          ctx.fillStyle = `rgba(124, 131, 148, ${alpha * 0.7})`;
        }
        ctx.arc(px, py, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(tick);
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMove, { passive: true });
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMove);
    };
  }, [reduced]);

  if (reduced) {
    return (
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background: `radial-gradient(circle at 50% 30%, ${tokens.mint}22, transparent 55%)`,
        }}
        aria-hidden
      />
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full opacity-90"
      aria-hidden
    />
  );
}
