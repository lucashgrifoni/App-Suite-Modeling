import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, BookOpen, Sparkles } from "lucide-react";
import { useRef } from "react";
import { ParticleField } from "../effects/ParticleField";
import { GlowOrbs } from "../effects/GlowOrbs";
import { HeroVisual } from "../effects/HeroVisual";
import { hero } from "../../data/content";
import { docsReadmeUrl, repoUrl } from "../../config/site";

export function HeroSection() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const y1 = useTransform(scrollYProgress, [0, 1], [0, 80]);
  const y2 = useTransform(scrollYProgress, [0, 1], [0, 60]);
  const op = useTransform(scrollYProgress, [0, 0.5], [1, 0]);

  return (
    <section
      ref={ref}
      id="top"
      className="relative min-h-[100svh] overflow-hidden pt-24 md:pt-28"
    >
      <div className="absolute inset-0 bg-midnight" />
      <div
        className="absolute inset-0 bg-[length:48px_48px] opacity-[0.35]"
        style={{
          backgroundImage: `
            linear-gradient(to bottom, rgba(12,18,76,0) 0%, #0c124c 95%),
            linear-gradient(rgba(8,185,139,0.07) 1px, transparent 1px),
            linear-gradient(90deg, rgba(8,185,139,0.07) 1px, transparent 1px)
          `,
        }}
        aria-hidden
      />
      <GlowOrbs />
      <ParticleField />

      <div className="relative z-10 mx-auto grid max-w-7xl gap-10 px-4 pb-20 md:grid-cols-2 md:items-center md:gap-12 md:px-8 lg:gap-16">
        <motion.div style={{ y: y2, opacity: op }} className="max-w-xl">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-2 rounded-full border border-mint/30 bg-mint/10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-mint shadow-[0_0_40px_-8px_rgba(8,185,139,0.6)]"
          >
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            Open source · AppSec · DevSecOps
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.75, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
            className="mt-6 font-display text-4xl font-semibold leading-[1.05] tracking-tight text-mist md:text-5xl lg:text-6xl"
          >
            App Suite{" "}
            <span className="animate-gradient-shift bg-gradient-to-r from-mint via-emerald-200 to-mint bg-[length:200%_auto] bg-clip-text text-transparent">
              Modeling
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.15 }}
            className="mt-5 text-xl font-medium text-mist/95 md:text-2xl"
          >
            {hero.tagline}
          </motion.p>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.22 }}
            className="mt-4 text-base leading-relaxed text-steel md:text-lg"
          >
            {hero.subtitle}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.32 }}
            className="mt-10 flex flex-wrap gap-4"
          >
            <a
              href={repoUrl}
              className="group inline-flex items-center gap-2 rounded-xl bg-mint px-6 py-3.5 text-sm font-semibold text-midnight shadow-mint transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mint"
            >
              View on GitHub
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </a>
            <a
              href={docsReadmeUrl}
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/[0.04] px-6 py-3.5 text-sm font-semibold text-mist backdrop-blur-md transition hover:border-mint/40 hover:bg-white/[0.07]"
            >
              <BookOpen className="h-4 w-4 text-mint" />
              Documentation
            </a>
          </motion.div>
        </motion.div>

        <motion.div
          style={{ y: y1 }}
          className="relative flex min-h-[280px] items-center justify-center md:min-h-[360px] lg:min-h-[420px]"
        >
          <HeroVisual />
        </motion.div>
      </div>
    </section>
  );
}
