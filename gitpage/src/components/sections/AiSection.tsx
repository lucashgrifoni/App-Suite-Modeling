import { motion, useScroll, useTransform } from "framer-motion";
import { Cpu, Network, ShieldCheck } from "lucide-react";
import { useRef } from "react";
import { AnimatedSection } from "../ui/AnimatedSection";

export function AiSection() {
  const parallaxRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: parallaxRef,
    offset: ["start end", "end start"],
  });
  const x = useTransform(scrollYProgress, [0, 1], [40, -40]);
  const glow = useTransform(scrollYProgress, [0, 0.5, 1], [0.3, 0.85, 0.4]);

  return (
    <AnimatedSection id="ai" className="relative overflow-hidden py-28 md:py-36">
      <div ref={parallaxRef} className="relative">
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <motion.div
          className="absolute left-1/2 top-1/2 h-[120%] w-[120%] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            background:
              "conic-gradient(from 120deg at 50% 50%, rgba(8,185,139,0.15), transparent 40%, rgba(124,131,148,0.2), transparent 70%)",
            opacity: glow,
          }}
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(8,185,139,0.25),transparent_45%)]" />
      </div>

      <div className="relative z-10 mx-auto grid max-w-7xl items-center gap-12 px-4 md:grid-cols-2 md:px-8">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-mint">
            AI & PLOT4ai
          </p>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-mist md:text-4xl lg:text-5xl">
            Futuristic modeling for{" "}
            <span className="text-gradient-mint">ML systems</span>—without the theater
          </h2>
          <p className="mt-6 text-lg leading-relaxed text-steel">
            Map agents, pipelines, and data dependencies with AI-native plotlines. Structure
            detection outputs, preserve rationale, and keep humans in the loop—where security
            actually happens.
          </p>
          <ul className="mt-10 space-y-4">
            {[
              {
                icon: Cpu,
                t: "Model boundaries for inference, tools, and sensitive prompts.",
              },
              {
                icon: Network,
                t: "Trace data lineage and third-party touchpoints with clarity.",
              },
              {
                icon: ShieldCheck,
                t: "Explainable outputs that survive audit—not just demo screenshots.",
              },
            ].map((row) => (
              <motion.li
                key={row.t}
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                className="flex gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-md"
              >
                <row.icon className="mt-0.5 h-5 w-5 shrink-0 text-mint" aria-hidden />
                <span className="text-sm leading-relaxed text-mist/95">{row.t}</span>
              </motion.li>
            ))}
          </ul>
        </div>

        <motion.div style={{ x }} className="relative min-h-[320px] md:min-h-[400px]">
          <div className="absolute inset-0 rounded-3xl border border-mint/20 bg-gradient-to-br from-mint/10 via-transparent to-steel/20 p-[1px] shadow-[0_0_80px_-20px_rgba(8,185,139,0.7)]">
            <div className="relative h-full overflow-hidden rounded-3xl bg-midnight/80 p-8 backdrop-blur-xl">
              <div className="font-mono text-[11px] leading-relaxed text-steel md:text-xs/4">
                <p className="text-mint">// plot4ai · structured threat trace</p>
                <p className="mt-4 text-mist/90">
                  <span className="text-steel">model_surface:</span> inference_api
                </p>
                <p className="text-mist/90">
                  <span className="text-steel">assets:</span> weights, prompts, eval_sets
                </p>
                <p className="text-mist/90">
                  <span className="text-steel">abuse:</span> prompt_injection, data_exfil
                </p>
                <motion.div
                  className="mt-6 h-px w-full bg-gradient-to-r from-mint via-mist/40 to-transparent"
                  initial={{ scaleX: 0 }}
                  whileInView={{ scaleX: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8 }}
                />
                <p className="mt-6 text-mist/80">
                  Output is tied to components—not floating bullet points. That is how you scale
                  reviews when models change weekly.
                </p>
              </div>
              <motion.div
                className="pointer-events-none absolute -bottom-10 right-0 h-40 w-40 rounded-full bg-mint/30 blur-3xl"
                animate={{ opacity: [0.4, 0.75, 0.4] }}
                transition={{ duration: 5, repeat: Infinity }}
              />
            </div>
          </div>
        </motion.div>
      </div>
      </div>
    </AnimatedSection>
  );
}
