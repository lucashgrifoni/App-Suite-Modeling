import { motion } from "framer-motion";
import { methodologies } from "../../data/content";
import type { Maturity } from "../../data/content";
import { AnimatedSection } from "../ui/AnimatedSection";
import { SectionHeading } from "../ui/SectionHeading";

function MaturityPill({ m }: { m: Maturity }) {
  const styles: Record<Maturity, string> = {
    Core: "border-mint/40 bg-mint/15 text-mint",
    Advanced: "border-steel/50 bg-white/5 text-mist",
    Experimental: "border-white/20 bg-white/5 text-steel",
  };
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${styles[m]}`}
    >
      {m}
    </span>
  );
}

export function MethodologiesSection() {
  return (
    <AnimatedSection
      id="methodologies"
      className="relative border-y border-white/5 bg-[#080c38] py-24 md:py-32"
    >
      <div className="mx-auto max-w-7xl px-4 md:px-8">
        <SectionHeading
          eyebrow="Methodologies"
          title="Native support for the frameworks you already trust"
          subtitle="Pick the lens that matches the system—privacy, risk, AI, or classic STRIDE."
        />
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {methodologies.map((m, i) => (
            <motion.article
              key={m.id}
              initial={{ opacity: 0, rotateX: -8, y: 28 }}
              whileInView={{ opacity: 1, rotateX: 0, y: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{ delay: i * 0.05, duration: 0.55 }}
              style={{ perspective: 1200 }}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.07] to-transparent p-6 shadow-card"
            >
              <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-mint/50 to-transparent opacity-0 transition group-hover:opacity-100" />
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-lg font-semibold text-mist">{m.name}</h3>
                <MaturityPill m={m.maturity} />
              </div>
              <p className="mt-3 text-sm leading-relaxed text-steel">{m.summary}</p>
              <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate">
                When to use
              </p>
              <p className="mt-1 text-sm text-mist/90">{m.when}</p>
            </motion.article>
          ))}
        </div>
      </div>
    </AnimatedSection>
  );
}
