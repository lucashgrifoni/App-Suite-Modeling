import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
} from "framer-motion";
import { Shield, Workflow } from "lucide-react";
import { useCallback, useRef } from "react";
import { useReducedMotion } from "../../hooks/useReducedMotion";
import { HeroRadar } from "./HeroRadar";

const ORBIT_NODES = [
  { className: "left-[24%] top-[22%]", delay: 0 },
  { className: "right-[22%] top-[26%] left-auto", delay: 0.15 },
  { className: "left-[26%] bottom-[28%] top-auto", delay: 0.3 },
  { className: "right-[24%] bottom-[26%] left-auto top-auto", delay: 0.45 },
];

const SPARK_POSITIONS: Array<{ top: string; left: string; delay: number }> = [
  { top: "12%", left: "18%", delay: 0 },
  { top: "20%", left: "82%", delay: 0.4 },
  { top: "78%", left: "14%", delay: 0.8 },
  { top: "84%", left: "76%", delay: 1.2 },
  { top: "48%", left: "8%", delay: 0.6 },
  { top: "52%", left: "88%", delay: 1 },
];

/**
 * Painel hero com “3D” em CSS (perspectiva + camadas Z + tilt) e animações ricas.
 * Sem WebGL — bundle leve e comportamento previsível.
 */
export function HeroVisual() {
  const reduced = useReducedMotion();
  const wrapRef = useRef<HTMLDivElement>(null);
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const springConfig = { stiffness: 280, damping: 28, mass: 0.6 };
  const springX = useSpring(mx, springConfig);
  const springY = useSpring(my, springConfig);

  const rotateX = useTransform(springY, [-0.5, 0.5], reduced ? ["0deg", "0deg"] : ["8deg", "-8deg"]);
  const rotateY = useTransform(springX, [-0.5, 0.5], reduced ? ["0deg", "0deg"] : ["-11deg", "11deg"]);

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (reduced || !wrapRef.current) return;
      const r = wrapRef.current.getBoundingClientRect();
      mx.set((e.clientX - r.left) / r.width - 0.5);
      my.set((e.clientY - r.top) / r.height - 0.5);
    },
    [reduced, mx, my],
  );

  const onPointerLeave = useCallback(() => {
    mx.set(0);
    my.set(0);
  }, [mx, my]);

  return (
    <div
      className="relative mx-auto aspect-square w-full max-w-[min(100%,480px)] md:max-w-[520px] md:justify-self-end [perspective:1200px] [perspective-origin:50%_50%]"
      aria-hidden
    >
      {/* Halo externo pulsante */}
      <motion.div
        className="pointer-events-none absolute -inset-8 rounded-[2.5rem] bg-[radial-gradient(ellipse_65%_55%_at_50%_45%,rgba(8,185,139,0.22),transparent_72%)] blur-2xl md:-inset-10"
        animate={
          reduced
            ? {}
            : { opacity: [0.65, 1, 0.65], scale: [1, 1.04, 1] }
        }
        transition={{ duration: 5, repeat: reduced ? 0 : Infinity, ease: "easeInOut" }}
      />

      {/* Anel orbitando em 3D (plano inclinado + rotação no filho — evita choque de transform) */}
      <div
        className="pointer-events-none absolute -inset-3 md:-inset-4 [transform-style:preserve-3d]"
        style={{ transform: "rotateX(58deg) translateZ(-12px)" }}
      >
        <motion.div
          className="h-full w-full rounded-[2.2rem] border border-mint/15"
          animate={reduced ? {} : { rotateZ: 360 }}
          transition={{ duration: 28, repeat: reduced ? 0 : Infinity, ease: "linear" }}
        />
      </div>

      <motion.div
        ref={wrapRef}
        className="relative h-full w-full cursor-default [transform-style:preserve-3d]"
        style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
        onPointerMove={onPointerMove}
        onPointerLeave={onPointerLeave}
        animate={
          reduced
            ? {}
            : { y: [0, -6, 0] }
        }
        transition={{
          y: { duration: 6, repeat: Infinity, ease: "easeInOut" },
        }}
      >
        {/* Borda cônica animada (entre o glow e o card) */}
        {!reduced ? (
          <motion.div
            className="pointer-events-none absolute -inset-[2px] rounded-[1.85rem] opacity-60 blur-[0.5px] md:rounded-[2.1rem]"
            style={{
              background:
                "conic-gradient(from 0deg, rgba(8,185,139,0.55), transparent 35%, rgba(124,131,148,0.25), transparent 65%, rgba(8,185,139,0.45))",
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
          />
        ) : null}

        <div
          className="relative h-full overflow-hidden rounded-[1.75rem] border border-white/10 bg-gradient-to-br from-white/[0.08] via-[#0c124c]/85 to-midnight p-6 shadow-[0_28px_90px_-28px_rgba(0,0,0,0.65),0_0_0_1px_rgba(8,185,139,0.14),inset_0_1px_0_rgba(255,255,255,0.06)] md:rounded-[2rem] md:p-8"
          style={{ aspectRatio: "1 / 1", transformStyle: "preserve-3d" }}
        >
          {/* Camada de profundidade: grade “afundada” */}
          <div
            className="pointer-events-none absolute inset-[6%] rounded-[1.25rem] opacity-[0.35] md:inset-[7%]"
            style={{
              transform: "translateZ(-36px) scale(1.06)",
              backgroundImage: `
                linear-gradient(rgba(8,185,139,0.12) 1px, transparent 1px),
                linear-gradient(90deg, rgba(8,185,139,0.12) 1px, transparent 1px)
              `,
              backgroundSize: "18px 18px",
              transformStyle: "preserve-3d",
            }}
          />

          <div className="absolute inset-x-0 top-0 z-20 h-px bg-gradient-to-r from-transparent via-mint/50 to-transparent" />

          {/* Anéis: wrapper fixo em Z; rotação só no filho (sem sobrescrever translateZ) */}
          <div
            className="absolute left-1/2 top-1/2 z-[5] aspect-square w-[78%] -translate-x-1/2 -translate-y-1/2"
            style={{ transform: "translate(-50%, -50%) translateZ(8px)", transformStyle: "preserve-3d" }}
          >
            <motion.div
              className="h-full w-full rounded-full border border-mint/25 shadow-[0_0_32px_-8px_rgba(8,185,139,0.35)]"
              animate={reduced ? {} : { rotate: 360 }}
              transition={{ duration: 48, repeat: reduced ? 0 : Infinity, ease: "linear" }}
            />
          </div>
          <div
            className="absolute left-1/2 top-1/2 z-[4] aspect-square w-[58%] -translate-x-1/2 -translate-y-1/2"
            style={{ transform: "translate(-50%, -50%) translateZ(4px)", transformStyle: "preserve-3d" }}
          >
            <motion.div
              className="h-full w-full rounded-full border border-steel/45"
              animate={reduced ? {} : { rotate: -360 }}
              transition={{ duration: 64, repeat: reduced ? 0 : Infinity, ease: "linear" }}
            />
          </div>
          <div
            className="absolute left-1/2 top-1/2 z-[4] aspect-square w-[44%] -translate-x-1/2 -translate-y-1/2"
            style={{ transform: "translate(-50%, -50%) translateZ(12px)", transformStyle: "preserve-3d" }}
          >
            <motion.div
              className="h-full w-full rounded-full border border-dashed border-mint/20"
              animate={reduced ? {} : { rotate: 360 }}
              transition={{ duration: 36, repeat: reduced ? 0 : Infinity, ease: "linear" }}
            />
          </div>

          {/* Núcleo */}
          <div
            className="absolute left-1/2 top-1/2 z-[6] -translate-x-1/2 -translate-y-1/2"
            style={{ transform: "translate(-50%, -50%) translateZ(18px)", transformStyle: "preserve-3d" }}
          >
            <motion.div
              className="h-3 w-3 rounded-full bg-mint shadow-[0_0_28px_rgba(8,185,139,0.85)] ring-2 ring-mint/30"
              animate={
                reduced
                  ? {}
                  : {
                      scale: [1, 1.25, 1],
                      boxShadow: [
                        "0 0 28px rgba(8,185,139,0.85)",
                        "0 0 40px rgba(8,185,139,1)",
                        "0 0 28px rgba(8,185,139,0.85)",
                      ],
                    }
              }
              transition={{ duration: 2.4, repeat: reduced ? 0 : Infinity, ease: "easeInOut" }}
            />
          </div>

          {ORBIT_NODES.map((n, i) => (
            <div
              key={i}
              className={`absolute z-[7] ${n.className}`}
              style={{ transform: "translateZ(22px)", transformStyle: "preserve-3d" }}
            >
              <motion.div
                className="h-2 w-2 rounded-sm bg-mist/90 shadow-[0_0_12px_rgba(8,185,139,0.4)] ring-1 ring-mint/50"
                animate={
                  reduced
                    ? {}
                    : {
                        opacity: [0.5, 1, 0.5],
                        scale: [0.88, 1.08, 0.88],
                        y: [0, -4, 0],
                      }
                }
                transition={{
                  duration: 3.2,
                  repeat: reduced ? 0 : Infinity,
                  delay: n.delay,
                  ease: "easeInOut",
                }}
              />
            </div>
          ))}

          {/* Partículas / faíscas */}
          {SPARK_POSITIONS.map((s, i) => (
            <div
              key={`spark-${i}`}
              className="pointer-events-none absolute z-[8]"
              style={{
                top: s.top,
                left: s.left,
                transform: "translateZ(26px)",
                transformStyle: "preserve-3d",
              }}
            >
              <motion.div
                className="h-1 w-1 rounded-full bg-mint shadow-[0_0_10px_2px_rgba(8,185,139,0.9)]"
                animate={
                  reduced
                    ? {}
                    : {
                        opacity: [0.2, 1, 0.2],
                        scale: [0.6, 1.4, 0.6],
                      }
                }
                transition={{
                  duration: 2.2,
                  repeat: reduced ? 0 : Infinity,
                  delay: s.delay,
                  ease: "easeInOut",
                }}
              />
            </div>
          ))}

          <motion.svg
            className="pointer-events-none absolute inset-0 z-[6] h-full w-full text-mint/30"
            style={{ transform: "translateZ(14px)" }}
            viewBox="0 0 200 200"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            animate={reduced ? {} : { opacity: [0.22, 0.4, 0.22] }}
            transition={{ duration: 4, repeat: reduced ? 0 : Infinity, ease: "easeInOut" }}
          >
            <path d="M100 36 L100 164 M36 100 L164 100" stroke="currentColor" strokeWidth="0.5" />
            <circle cx="100" cy="100" r="54" stroke="currentColor" strokeWidth="0.5" strokeDasharray="4 6" />
          </motion.svg>

          {/* Varredura de brilho */}
          {!reduced ? (
            <motion.div
              className="pointer-events-none absolute inset-y-0 left-0 z-[24] w-[42%] mix-blend-overlay"
              initial={false}
              animate={{ x: ["-20%", "280%"] }}
              transition={{ duration: 4.2, repeat: Infinity, ease: "linear", repeatDelay: 1.2 }}
              style={{
                background:
                  "linear-gradient(95deg, transparent, rgba(213,216,221,0.2), transparent)",
              }}
            />
          ) : null}

          {/* Cubinhos decorativos nos cantos (ilusão 3D isométrica) */}
          {!reduced ? (
            <>
              <div
                className="pointer-events-none absolute left-[10%] top-[14%] z-[9]"
                style={{
                  transform: "translateZ(34px) rotateX(54deg) rotateZ(45deg)",
                  transformStyle: "preserve-3d",
                }}
              >
                <motion.div
                  className="h-5 w-5 rounded-md border border-mint/35 bg-gradient-to-br from-mint/25 to-transparent"
                  animate={{ y: [0, -5, 0], rotateZ: [0, 5, 0] }}
                  transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                />
              </div>
              <div
                className="pointer-events-none absolute bottom-[16%] right-[12%] z-[9]"
                style={{
                  transform: "translateZ(30px) rotateX(54deg) rotateZ(-25deg)",
                  transformStyle: "preserve-3d",
                }}
              >
                <motion.div
                  className="h-4 w-4 rounded border border-steel/50 bg-gradient-to-br from-white/10 to-transparent"
                  animate={{ y: [0, 6, 0] }}
                  transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
                />
              </div>
            </>
          ) : null}

          <div
            className="relative z-[30] flex h-full min-h-0 flex-col justify-between [transform:translateZ(42px)]"
            style={{ transformStyle: "preserve-3d" }}
          >
            <motion.div
              className="flex shrink-0 items-start justify-between gap-3"
              initial={{ opacity: 0.85, y: 6 }}
              animate={reduced ? {} : { opacity: 1, y: [0, -3, 0] }}
              transition={{ duration: 3.5, repeat: reduced ? 0 : Infinity, ease: "easeInOut" }}
            >
              <span className="inline-flex items-center gap-2 rounded-lg border border-white/12 bg-midnight/70 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-steel shadow-lg backdrop-blur-sm md:text-xs">
                <Workflow className="h-3.5 w-3.5 text-mint" />
                Model graph
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-mint/30 bg-mint/12 px-2.5 py-1.5 text-[10px] font-semibold text-mint shadow-[0_0_20px_-6px_rgba(8,185,139,0.7)] md:text-xs">
                <Shield className="h-3.5 w-3.5" />
                STRIDE-ready
              </span>
            </motion.div>

            <div className="flex min-h-[140px] flex-1 items-center justify-center py-2 md:min-h-[160px] md:py-4">
              <HeroRadar reduced={reduced} />
            </div>

            <motion.div
              className="shrink-0 space-y-2 rounded-xl border border-white/8 bg-midnight/50 p-3 shadow-inner backdrop-blur-sm md:p-4"
              animate={reduced ? {} : { boxShadow: ["inset 0 0 20px rgba(8,185,139,0.04)", "inset 0 0 28px rgba(8,185,139,0.1)", "inset 0 0 20px rgba(8,185,139,0.04)"] }}
              transition={{ duration: 3, repeat: reduced ? 0 : Infinity, ease: "easeInOut" }}
            >
              <motion.div
                className="h-1.5 w-3/4 rounded bg-gradient-to-r from-mint/70 to-transparent"
                animate={reduced ? {} : { opacity: [0.7, 1, 0.7], x: [0, 4, 0] }}
                transition={{ duration: 2.8, repeat: reduced ? 0 : Infinity, ease: "easeInOut" }}
              />
              <div className="h-1.5 w-1/2 rounded bg-white/12" />
              <motion.div
                className="h-1.5 w-5/6 rounded bg-white/12"
                animate={reduced ? {} : { scaleX: [0.92, 1, 0.92] }}
                transition={{ duration: 2.5, repeat: reduced ? 0 : Infinity, ease: "easeInOut" }}
              />
            </motion.div>
          </div>

          <div className="pointer-events-none absolute inset-0 z-[19] bg-[radial-gradient(ellipse_80%_70%_at_50%_50%,transparent_35%,rgba(12,18,76,0.55)_100%)]" />
        </div>
      </motion.div>
    </div>
  );
}
