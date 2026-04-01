import { motion } from "framer-motion";
import {
  Boxes,
  Brain,
  Diff,
  FileStack,
  Layers,
  ListChecks,
  Lock,
  Radar,
  Sparkles,
  Workflow,
  Wrench,
} from "lucide-react";
import { differentiators } from "../../data/content";
import { AnimatedSection } from "../ui/AnimatedSection";
import { SectionHeading } from "../ui/SectionHeading";

const icons = [
  Radar,
  Lock,
  Workflow,
  Brain,
  FileStack,
  Diff,
  ListChecks,
  Sparkles,
  Boxes,
  Layers,
  Wrench,
];

export function DifferentiatorsSection() {
  return (
    <AnimatedSection
      id="differentiators"
      className="relative py-24 md:py-32"
    >
      <div className="pointer-events-none absolute inset-0 bg-radial-glow opacity-70" aria-hidden />
      <div className="relative mx-auto max-w-7xl px-4 md:px-8">
        <SectionHeading
          eyebrow="Differentiators"
          title="Why teams pick App Suite Modeling"
          subtitle="Premium workflows—without proprietary lock-in. Opinionated defaults, open architecture."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {differentiators.map((item, i) => {
            const Icon = icons[i % icons.length];
            return (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-8%" }}
                transition={{ delay: (i % 6) * 0.04, duration: 0.5 }}
                whileHover={{ y: -4, transition: { duration: 0.25 } }}
                className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.07] to-transparent p-6 shadow-card"
              >
                <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-mint/10 blur-2xl transition group-hover:bg-mint/20" />
                <div className="relative flex items-start gap-4">
                  <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-mint/25 bg-mint/10 text-mint">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <div>
                    <h3 className="font-semibold text-mist">{item.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-steel">{item.body}</p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </AnimatedSection>
  );
}
