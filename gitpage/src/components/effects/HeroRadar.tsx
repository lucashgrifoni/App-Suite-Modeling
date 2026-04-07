import { motion } from "framer-motion";

/** Bearing em graus (0 = topo, horário). dist: 0–1 a partir do centro. */
function polarToPercent(bearingDeg: number, dist: number): { left: number; top: number } {
  const rad = (bearingDeg * Math.PI) / 180;
  const r = dist * 41;
  return {
    left: 50 + Math.sin(rad) * r,
    top: 50 - Math.cos(rad) * r,
  };
}

const BLIPS: Array<{ bearing: number; dist: number; delay: number }> = [
  { bearing: 28, dist: 0.72, delay: 0 },
  { bearing: 142, dist: 0.45, delay: 0.35 },
  { bearing: 218, dist: 0.68, delay: 0.7 },
  { bearing: 332, dist: 0.38, delay: 1.05 },
  { bearing: 88, dist: 0.58, delay: 1.4 },
];

type Props = {
  reduced: boolean;
};

/**
 * Radar “de detecção” em CSS/SVG — varredura, anéis, blips pulsantes.
 */
export function HeroRadar({ reduced }: Props) {
  return (
    <div
      className="pointer-events-none relative mx-auto w-full max-w-[210px] [transform:translateZ(48px)] md:max-w-[240px]"
      style={{ transformStyle: "preserve-3d" }}
      aria-hidden
    >
      <div className="relative isolate aspect-square w-full overflow-hidden rounded-full border border-mint/25 bg-[radial-gradient(circle_at_50%_50%,rgba(8,185,139,0.06)_0%,rgba(12,18,76,0.92)_65%,#0c124c_100%)] shadow-[inset_0_0_40px_rgba(0,0,0,0.45),0_0_32px_-8px_rgba(8,185,139,0.25)]">
        {/* Anéis estáticos de alcance */}
        <div className="absolute inset-[7%] rounded-full border border-mint/15" />
        <div className="absolute inset-[18%] rounded-full border border-steel/30" />
        <div className="absolute inset-[29%] rounded-full border border-mint/12" />
        <div className="absolute inset-[40%] rounded-full border border-white/8" />

        {/* Grade */}
        <div className="absolute inset-0 rounded-full opacity-[0.35]" style={{
          backgroundImage: `
            linear-gradient(rgba(8,185,139,0.12) 1px, transparent 1px),
            linear-gradient(90deg, rgba(8,185,139,0.12) 1px, transparent 1px)
          `,
          backgroundSize: "14px 14px",
        }} />

        {/* Cruz */}
        <div className="absolute left-1/2 top-[8%] h-[84%] w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-mint/25 to-transparent" />
        <div className="absolute top-1/2 left-[8%] h-px w-[84%] -translate-y-1/2 bg-gradient-to-r from-transparent via-mint/25 to-transparent" />

        {/* Setor de varredura (cone suave) */}
        {!reduced ? (
          <motion.div
            className="pointer-events-none absolute inset-[5%] z-[1] rounded-full"
            style={{
              background:
                "conic-gradient(from 0deg at 50% 50%, rgba(8,185,139,0.42) 0deg, rgba(8,185,139,0.12) 38deg, transparent 52deg, transparent 360deg)",
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 3.4, repeat: Infinity, ease: "linear" }}
          />
        ) : (
          <div
            className="pointer-events-none absolute inset-[5%] z-[1] rounded-full opacity-40"
            style={{
              background:
                "conic-gradient(from 0deg at 50% 50%, rgba(8,185,139,0.25) 0deg, transparent 55deg, transparent 360deg)",
            }}
          />
        )}

        {/* Linha do feixe — pivô no centro (bottom-1/2 = borda inferior no meio do disco) */}
        {!reduced ? (
          <motion.div
            className="absolute bottom-1/2 left-1/2 z-[2] w-0.5 origin-bottom -translate-x-1/2 rounded-full bg-gradient-to-t from-transparent via-mint/85 to-mint"
            style={{ height: "42%" }}
            animate={{ rotate: 360 }}
            transition={{ duration: 3.4, repeat: Infinity, ease: "linear" }}
          />
        ) : (
          <div
            className="absolute bottom-1/2 left-1/2 z-[2] w-0.5 origin-bottom rounded-full bg-mint/40 opacity-60"
            style={{ height: "42%", transform: "translateX(-50%) rotate(-40deg)" }}
          />
        )}

        {/* Onda de “ping” no anel médio */}
        {!reduced ? (
          <motion.div
            className="pointer-events-none absolute inset-[18%] z-[3] rounded-full border border-mint/40"
            animate={{ opacity: [0.15, 0.55, 0.15], scale: [0.92, 1.04, 0.92] }}
            transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
          />
        ) : null}

        {/* Blips / alvos */}
        {BLIPS.map((b, i) => {
          const { left, top } = polarToPercent(b.bearing, b.dist);
          return (
            <motion.div
              key={`${b.bearing}-${i}`}
              className="absolute z-[15]"
              style={{ left: `${left}%`, top: `${top}%`, transform: "translate(-50%, -50%)" }}
              animate={
                reduced
                  ? { opacity: 0.65 }
                  : {
                      opacity: [0.2, 1, 0.35, 1, 0.2],
                      scale: [0.85, 1.2, 0.9, 1.1, 0.85],
                      boxShadow: [
                        "0 0 6px rgba(8,185,139,0.4)",
                        "0 0 16px rgba(8,185,139,0.95)",
                        "0 0 8px rgba(8,185,139,0.5)",
                        "0 0 14px rgba(8,185,139,0.9)",
                        "0 0 6px rgba(8,185,139,0.4)",
                      ],
                    }
              }
              transition={{
                duration: 3.6,
                repeat: reduced ? 0 : Infinity,
                delay: b.delay,
                ease: "easeInOut",
              }}
            >
              <div className="relative flex h-2.5 w-2.5 items-center justify-center">
                <span className="absolute inset-0 rounded-sm border border-mint/60 bg-mint/30" />
                <span className="h-1 w-1 rounded-full bg-mist shadow-[0_0_8px_#08b98b]" />
              </div>
            </motion.div>
          );
        })}

        {/* Centro */}
        <div className="absolute left-1/2 top-1/2 z-20 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-mint ring-2 ring-mint/40 ring-offset-2 ring-offset-[#0a0e38]" />

        {/* Legenda HUD */}
        <div className="absolute bottom-[6%] left-0 right-0 text-center">
          <span className="font-mono text-[9px] font-semibold uppercase tracking-[0.35em] text-mint/70 md:text-[10px]">
            sweep active
          </span>
        </div>
      </div>
    </div>
  );
}
