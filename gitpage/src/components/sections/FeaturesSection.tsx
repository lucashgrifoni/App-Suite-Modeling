import { motion } from "framer-motion";
import {
  Bot,
  BookMarked,
  Code2,
  FileInput,
  GitCompare,
  LayoutDashboard,
  ListTodo,
  Server,
  Shapes,
} from "lucide-react";
import { features } from "../../data/content";
import { AnimatedSection } from "../ui/AnimatedSection";
import { SectionHeading } from "../ui/SectionHeading";

const featIcons = [
  LayoutDashboard,
  Code2,
  Server,
  Shapes,
  FileInput,
  GitCompare,
  ListTodo,
  BookMarked,
  Bot,
];

export function FeaturesSection() {
  return (
    <AnimatedSection id="features" className="relative py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 md:px-8">
        <SectionHeading
          eyebrow="Capabilities"
          title="Everything you need to model threats at scale"
          subtitle="One platform—multiple surfaces—consistent artifacts."
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => {
            const Icon = featIcons[i % featIcons.length];
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, scale: 0.97 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: (i % 9) * 0.04, duration: 0.45 }}
                className="glass-strong flex gap-4 rounded-2xl p-5"
              >
                <span className="mt-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-midnight text-mint ring-1 ring-mint/25">
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                <div>
                  <h3 className="font-semibold text-mist">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-steel">{f.body}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </AnimatedSection>
  );
}
