import { motion } from "framer-motion";
import { Database, Layers, Sparkles } from "lucide-react";
import { AnimatedSection } from "../ui/AnimatedSection";
import { SectionHeading } from "../ui/SectionHeading";

const highlights = [
  {
    title: "Industry packs",
    body: "Curated starters for SaaS, APIs, cloud-native, and regulated contexts.",
  },
  {
    title: "Composable models",
    body: "Mix objectives and domains without losing traceability across layers.",
  },
  {
    title: "Release-ready",
    body: "Templates align with docs and automation—same language from IDE to review.",
  },
];

export function TemplatesSection() {
  return (
    <AnimatedSection
      id="templates"
      className="relative border-t border-white/5 bg-gradient-to-b from-midnight to-[#070a32] py-24 md:py-32"
    >
      <div className="mx-auto max-w-7xl px-4 md:px-8">
        <SectionHeading
          eyebrow="Templates & catalog"
          title="A premium catalog for consistent threat modeling"
          subtitle="Start fast. Stay consistent. Scale across teams without diluting rigor."
        />
        <div className="grid gap-8 lg:grid-cols-3">
          {highlights.map((h, i) => (
            <motion.div
              key={h.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] p-8"
            >
              <div className="absolute -right-8 -top-8 opacity-20">
                {i === 0 ? (
                  <Layers className="h-32 w-32 text-mint" />
                ) : i === 1 ? (
                  <Sparkles className="h-32 w-32 text-mint" />
                ) : (
                  <Database className="h-32 w-32 text-mint" />
                )}
              </div>
              <h3 className="relative text-lg font-semibold text-mist">{h.title}</h3>
              <p className="relative mt-3 text-sm leading-relaxed text-steel">{h.body}</p>
            </motion.div>
          ))}
        </div>
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mt-14 rounded-2xl border border-mint/25 bg-gradient-to-r from-mint/10 via-transparent to-steel/10 p-6 text-center md:p-10"
        >
          <p className="text-sm font-medium text-mist md:text-base">
            The template system is designed like a product surface: searchable metadata, clear
            boundaries, and predictable structure—so security reviews stay efficient as the catalog
            grows.
          </p>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}
