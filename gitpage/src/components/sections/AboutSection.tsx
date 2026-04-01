import { AnimatedSection } from "../ui/AnimatedSection";
import { SectionHeading } from "../ui/SectionHeading";
import { about } from "../../data/content";
import { motion } from "framer-motion";

export function AboutSection() {
  return (
    <AnimatedSection
      id="about"
      className="relative border-t border-white/5 bg-gradient-to-b from-midnight to-[#0a0e38] py-24 md:py-32"
    >
      <div className="mx-auto max-w-5xl px-4 md:px-8">
        <SectionHeading
          eyebrow="What it is"
          title="A threat modeling platform built for real delivery"
          subtitle="From workshops to CI—structure, traceability, and speed without sacrificing depth."
        />
        <div className="grid gap-8 md:grid-cols-3">
          {about.paragraphs.map((p, i) => (
            <motion.article
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08, duration: 0.55 }}
              className="glass rounded-2xl p-6 md:p-7"
            >
              <p className="text-sm leading-relaxed text-mist/90 md:text-base">{p}</p>
            </motion.article>
          ))}
        </div>
      </div>
    </AnimatedSection>
  );
}
