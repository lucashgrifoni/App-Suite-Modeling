import {
  AnimatePresence,
  motion,
  useMotionTemplate,
  useMotionValue,
  useSpring,
  useTransform,
} from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Shield, Workflow } from "lucide-react";
import { useReducedMotion } from "../../hooks/useReducedMotion";

const springCfg = { stiffness: 300, damping: 30, mass: 0.82 };

const RADAR_CONTACTS = [
  { xPct: 58, yPct: 30, ok: true },
  { xPct: 74, yPct: 44, ok: true },
  { xPct: 40, yPct: 52, ok: false },
  { xPct: 54, yPct: 66, ok: true },
  { xPct: 34, yPct: 36, ok: false },
  { xPct: 68, yPct: 58, ok: true },
  { xPct: 48, yPct: 42, ok: true },
  { xPct: 62, yPct: 54, ok: false },
] as const;

const SCAN_MESSAGES = [
  {
    level: "ok" as const,
    text: "Trust boundaries validated against the deployment diagram.",
  },
  {
    level: "alert" as const,
    text: "New external dependency: LLM API — review data flow and retention.",
  },
  {
    level: "ok" as const,
    text: "STRIDE coverage complete for the public API surface.",
  },
  {
    level: "alert" as const,
    text: "High-severity spoofing scenario still lacks documented mitigations.",
  },
  {
    level: "ok" as const,
    text: "Template catalog synced with the latest industry pack revision.",
  },
  {
    level: "alert" as const,
    text: "Privileged admin path flagged — LINDDUN privacy review suggested.",
  },
  {
    level: "ok" as const,
    text: "Diff between model v1.2 and v1.3 shows no orphaned threats.",
  },
  {
    level: "alert" as const,
    text: "Webhook ingress: unsigned payloads detected in staging graph.",
  },
] as const;

function RadarFace({ reduced }: { reduced: boolean }) {
  return (
    <div
      className="relative isolate mx-auto aspect-square w-full max-w-[min(240px,72vw)] overflow-hidden rounded-full border border-mint/30 bg-[radial-gradient(circle_at_50%_50%,rgba(8,185,139,0.14)_0%,rgba(12,18,76,0.94)_50%,var(--semantic-surface-deep)_100%)] shadow-[inset_0_0_60px_rgba(0,0,0,0.5),0_0_48px_-10px_rgba(8,185,139,0.35)]"
      aria-hidden
    >
      <div
        className="pointer-events-none absolute inset-0 rounded-full opacity-70"
        style={{
          background:
            "radial-gradient(circle at 50% 100%, rgba(8,185,139,0.08) 0%, transparent 45%)",
        }}
      />

      <svg
        className="pointer-events-none absolute inset-[4%] h-[92%] w-[92%] text-mint/25"
        viewBox="0 0 100 100"
        fill="none"
      >
        <circle cx="50" cy="50" r="46" stroke="currentColor" strokeWidth="0.35" />
        <circle cx="50" cy="50" r="32" stroke="currentColor" strokeWidth="0.25" />
        <circle cx="50" cy="50" r="18" stroke="currentColor" strokeWidth="0.25" />
        <line x1="50" y1="4" x2="50" y2="96" stroke="currentColor" strokeWidth="0.2" />
        <line x1="4" y1="50" x2="96" y2="50" stroke="currentColor" strokeWidth="0.2" />
        <line
          x1="50"
          y1="50"
          x2="96"
          y2="50"
          stroke="currentColor"
          strokeWidth="0.15"
          opacity="0.5"
          transform="rotate(45 50 50)"
        />
        <line
          x1="50"
          y1="50"
          x2="96"
          y2="50"
          stroke="currentColor"
          strokeWidth="0.15"
          opacity="0.5"
          transform="rotate(-45 50 50)"
        />
      </svg>

      {!reduced ? (
        <motion.div
          className="pointer-events-none absolute inset-[5%] rounded-full"
          style={{
            background:
              "conic-gradient(from -12deg at 50% 50%, rgba(8,185,139,0.48) 0deg, rgba(8,185,139,0.14) 26deg, transparent 34deg, transparent 360deg)",
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        />
      ) : (
        <div
          className="pointer-events-none absolute inset-[5%] rounded-full opacity-40"
          style={{
            background:
              "conic-gradient(from 40deg at 50% 50%, rgba(8,185,139,0.35) 0deg, transparent 32deg, transparent 360deg)",
          }}
        />
      )}

      <div className="pointer-events-none absolute inset-0 z-[1] rounded-full bg-[radial-gradient(circle_at_50%_50%,transparent_40%,rgba(12,18,76,0.6)_100%)]" />

      {RADAR_CONTACTS.map((c, i) => (
        <motion.div
          key={i}
          className={`absolute rounded-full ring-2 [transform:translate(-50%,-50%)] ${
            c.ok
              ? "h-2 w-2 bg-mint ring-mint/50 shadow-[0_0_14px_rgba(8,185,139,0.95)]"
              : "h-3 w-3 bg-danger-strong ring-danger ring-offset-1 ring-offset-[rgba(12,18,76,0.35)] shadow-[0_0_20px_rgba(239,68,68,1)]"
          }`}
          style={{ left: `${c.xPct}%`, top: `${c.yPct}%`, zIndex: 5 }}
          initial={false}
          animate={
            reduced
              ? { opacity: 1, scale: 1 }
              : {
                  opacity: [0.65, 1, 0.65],
                  scale: c.ok ? [0.9, 1.1, 0.9] : [0.92, 1.12, 0.92],
                }
          }
          transition={{
            duration: 2.35,
            repeat: reduced ? 0 : Infinity,
            delay: i * 0.12,
            ease: "easeInOut",
          }}
        />
      ))}

      <div className="pointer-events-none absolute left-1/2 top-1/2 z-[6] h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-mint shadow-[0_0_20px_rgba(8,185,139,1)] ring-2 ring-mint/50" />
    </div>
  );
}

function ScanTicker({ reduced }: { reduced: boolean }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const ms = reduced ? 6000 : 4200;
    const id = window.setInterval(() => {
      setIndex((n) => (n + 1) % SCAN_MESSAGES.length);
    }, ms);
    return () => window.clearInterval(id);
  }, [reduced]);

  const msg = SCAN_MESSAGES[index];
  const isAlert = msg.level === "alert";

  return (
    <div
      className="min-h-[4.5rem] md:min-h-[5rem]"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="mb-2 flex items-center gap-2 border-b border-white/10 pb-2">
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-steel md:text-[11px]">
          Live scan
        </span>
        <span className="h-1 w-1 rounded-full bg-mint shadow-[0_0_8px_var(--semantic-success)] animate-pulse" />
      </div>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={index}
          initial={reduced ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduced ? { opacity: 1 } : { opacity: 0, y: -6 }}
          transition={{ duration: reduced ? 0 : 0.35, ease: [0.16, 1, 0.3, 1] }}
          className="flex gap-2.5"
        >
          {isAlert ? (
            <AlertTriangle
              className="mt-0.5 h-4 w-4 shrink-0 text-danger-strong drop-shadow-[0_0_10px_rgba(239,68,68,0.55)]"
              aria-hidden
            />
          ) : (
            <CheckCircle2
              className="mt-0.5 h-4 w-4 shrink-0 text-mint"
              aria-hidden
            />
          )}
          <p
            className={`text-left text-[11px] leading-snug md:text-xs/4 ${
              isAlert
                ? "font-medium text-danger-strong"
                : "text-mist/90"
            }`}
          >
            {isAlert ? (
              <>
                <span className="mr-1.5 inline font-bold uppercase tracking-wide text-danger-strong">
                  Alert
                </span>
                <span className="text-danger">{msg.text}</span>
              </>
            ) : (
              msg.text
            )}
          </p>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

/**
 * Hero visual: stack 3D (CSS), tilt, radar semântico ok/alert, ticker.
 */
export function HeroVisual() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  const mx = useMotionValue(0);
  const my = useMotionValue(0);

  const tiltOutX = reduced ? [0, 0] : [13, -13];
  const tiltOutY = reduced ? [0, 0] : [-17, 17];

  const rotateX = useSpring(useTransform(my, [-1, 1], tiltOutX), springCfg);
  const rotateY = useSpring(useTransform(mx, [-1, 1], tiltOutY), springCfg);

  const glareX = useSpring(mx, { stiffness: 180, damping: 26 });
  const glareY = useSpring(my, { stiffness: 180, damping: 26 });
  const glareGx = useTransform(glareX, [-1, 1], [18, 82]);
  const glareGy = useTransform(glareY, [-1, 1], [22, 78]);
  const glareBg = useMotionTemplate`radial-gradient(380px circle at ${glareGx}% ${glareGy}%, rgba(255,255,255,0.24) 0%, transparent 52%)`;

  useEffect(() => {
    const root = wrapRef.current;
    if (!root || reduced) return;

    const onMove = (e: PointerEvent) => {
      const r = root.getBoundingClientRect();
      const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
      const ny = ((e.clientY - r.top) / r.height) * 2 - 1;
      mx.set(Math.max(-1, Math.min(1, nx)));
      my.set(Math.max(-1, Math.min(1, ny)));
    };

    const off = () => {
      mx.set(0);
      my.set(0);
    };

    root.addEventListener("pointermove", onMove, { passive: true });
    root.addEventListener("pointerleave", off);
    root.addEventListener("pointercancel", off);
    return () => {
      root.removeEventListener("pointermove", onMove);
      root.removeEventListener("pointerleave", off);
      root.removeEventListener("pointercancel", off);
    };
  }, [reduced, mx, my]);

  return (
    <div
      ref={wrapRef}
      className="relative mx-auto w-full max-w-[min(100%,480px)] md:max-w-[520px] md:justify-self-end"
      style={{ perspective: "1200px", perspectiveOrigin: "48% 42%" }}
    >
      <motion.div
        className="pointer-events-none absolute -inset-10 rounded-[2.75rem] bg-[radial-gradient(ellipse_58%_52%_at_50%_40%,rgba(8,185,139,0.32),transparent_70%)] blur-2xl md:-inset-14"
        animate={
          reduced
            ? {}
            : { opacity: [0.55, 0.95, 0.55], scale: [0.94, 1.04, 0.94] }
        }
        transition={
          reduced ? {} : { duration: 6, repeat: Infinity, ease: "easeInOut" }
        }
      />

      <motion.div
        className="pointer-events-none absolute -inset-2 rounded-[2.1rem] opacity-40 md:-inset-3 md:rounded-[2.2rem]"
        style={{
          background:
            "conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(8,185,139,0.5) 55deg, transparent 115deg, rgba(124,131,148,0.3) 195deg, transparent 260deg)",
        }}
        animate={reduced ? {} : { rotate: -360 }}
        transition={
          reduced
            ? {}
            : { duration: 16, repeat: Infinity, ease: "linear" }
        }
      />

      <motion.div
        className="relative w-full [transform-style:preserve-3d] will-change-transform"
        style={{ rotateX, rotateY }}
        animate={reduced ? {} : { y: [0, -6, 0] }}
        transition={
          reduced
            ? {}
            : { y: { duration: 5.5, repeat: Infinity, ease: "easeInOut" } }
        }
      >
        {/* Camada traseira — profundidade / “base” do stack */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-[14px] rounded-[1.55rem] border border-mint/10 bg-midnight/90 shadow-[0_50px_100px_-20px_rgba(0,0,0,0.65)] md:inset-[18px] md:rounded-[1.65rem]"
          style={{
            transform: "translateZ(-52px) scale(1.05)",
            filter: reduced ? undefined : "brightness(0.85)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-[8px] rounded-[1.65rem] border border-white/[0.07] bg-gradient-to-b from-mint/[0.08] via-transparent to-transparent md:inset-[10px] md:rounded-[1.75rem]"
          style={{ transform: "translateZ(-26px)" }}
        />

        <div
          className="relative z-[4] overflow-hidden rounded-[1.75rem] border bg-gradient-to-br from-white/[0.1] via-midnight/90 to-midnight p-6 shadow-hero-stack md:rounded-[2rem] md:p-8"
          style={{
            aspectRatio: "1 / 1",
            transform: "translateZ(22px)",
            boxShadow: `
              0 28px 80px -28px rgba(0,0,0,0.7),
              0 0 0 1px rgba(8,185,139,0.16),
              inset 0 1px 0 rgba(255,255,255,0.08),
              inset 0 -20px 40px -24px rgba(0,0,0,0.35)
            `,
          }}
        >
          {/* Vinheta atrás do conteúdo — evita cobrir radar/ticker (z-10) */}
          <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_88%_75%_at_50%_45%,transparent_28%,rgba(12,18,76,0.42)_100%)]" />

          {!reduced ? (
            <motion.div
              className="pointer-events-none absolute inset-0 z-[1] rounded-[inherit] opacity-90"
              style={{
                background: glareBg,
                mixBlendMode: "overlay",
              }}
            />
          ) : null}

          <div className="absolute inset-x-0 top-0 z-20 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent" />

          {!reduced ? (
            <motion.div
              className="pointer-events-none absolute inset-y-0 -left-1/2 z-[15] w-2/3 skew-x-[-16deg] bg-gradient-to-r from-transparent via-white/18 to-transparent opacity-60"
              animate={{ x: ["-35%", "230%"] }}
              transition={{
                duration: 3,
                repeat: Infinity,
                repeatDelay: 2.2,
                ease: "easeInOut",
              }}
            />
          ) : null}

          <motion.div
            className="pointer-events-none absolute inset-[11%] z-[1] rounded-2xl border bg-mint/[0.04]"
            animate={reduced ? {} : { scale: [0.98, 1, 0.98], opacity: [0.45, 0.8, 0.45] }}
            transition={
              reduced
                ? {}
                : { duration: 4.5, repeat: Infinity, ease: "easeInOut" }
            }
          />

          {/*
            Sem translateZ interno: overflow-hidden + preserve-3d no mesmo cartão
            fazia o motor achatar/ocultar o miolo (radar + ticker) em alguns browsers.
          */}
          <div className="relative z-10 flex h-full min-h-0 flex-col justify-between gap-3">
            <div
              className="flex shrink-0 items-start justify-between gap-3"
              aria-hidden
            >
              <motion.span
                className="inline-flex items-center gap-2 rounded-lg border bg-midnight/70 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-steel shadow-hero-lip backdrop-blur-sm md:text-xs"
                animate={reduced ? {} : { y: [0, -3, 0] }}
                transition={
                  reduced
                    ? {}
                    : { duration: 3.8, repeat: Infinity, ease: "easeInOut" }
                }
              >
                <Workflow className="h-3.5 w-3.5 text-mint" />
                Model graph
              </motion.span>
              <motion.span
                className="inline-flex items-center gap-1.5 rounded-lg border border-mint/35 px-2.5 py-1.5 text-[10px] font-semibold text-mint shadow-[0_0_24px_-8px_rgba(8,185,139,0.85)] md:text-xs"
                animate={reduced ? {} : { y: [0, 3, 0] }}
                transition={
                  reduced
                    ? {}
                    : {
                        duration: 4.2,
                        repeat: Infinity,
                        ease: "easeInOut",
                        delay: 0.35,
                      }
                }
              >
                <Shield className="h-3.5 w-3.5" />
                STRIDE-ready
              </motion.span>
            </div>

            <div
              className="relative flex min-h-[140px] w-full min-w-0 flex-1 flex-col items-center justify-center py-2"
              aria-hidden
            >
              <motion.div
                animate={
                  reduced
                    ? {}
                    : { rotate: [-1.5, 1.5, -1.5] }
                }
                transition={{
                  duration: 10,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
                className="w-full max-w-[min(240px,72vw)]"
              >
                <RadarFace reduced={reduced} />
              </motion.div>
            </div>

            <div className="shrink-0 rounded-xl border bg-midnight/60 p-3 shadow-hero-lip backdrop-blur-md md:p-4">
              <ScanTicker reduced={reduced} />
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
