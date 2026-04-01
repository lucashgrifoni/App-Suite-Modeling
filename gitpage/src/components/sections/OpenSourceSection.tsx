import { motion } from "framer-motion";
import { BookOpen, GitBranch, Heart, Package, Rocket, Users } from "lucide-react";
import { AnimatedSection } from "../ui/AnimatedSection";
import { SectionHeading } from "../ui/SectionHeading";
import { docsReadmeUrl, repoUrl } from "../../config/site";

const items = [
  {
    icon: GitBranch,
    title: "Open source",
    body: "Transparent development model—inspect, fork, and improve.",
  },
  {
    icon: Package,
    title: "Extensible",
    body: "Hooks for packs, integrations, and organization-specific workflows.",
  },
  {
    icon: Users,
    title: "Community-ready",
    body: "Documentation and structure aimed at contributors and adopters.",
  },
  {
    icon: BookOpen,
    title: "Deep docs",
    body: "Guides that match how engineers actually ship software.",
  },
  {
    icon: Rocket,
    title: "Release discipline",
    body: "Predictable artifacts for teams that need repeatable delivery.",
  },
  {
    icon: Heart,
    title: "GitHub-native",
    body: "Issues, discussions, and PRs—where developers already live.",
  },
];

export function OpenSourceSection() {
  return (
    <AnimatedSection id="opensource" className="relative py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 md:px-8">
        <SectionHeading
          eyebrow="Open source"
          title="Built to be adopted—and extended"
          subtitle="Serious tooling for serious teams. No black boxes."
        />
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: (i % 6) * 0.05 }}
              className="flex gap-4 rounded-2xl border border-white/10 bg-midnight/50 p-5 backdrop-blur-sm"
            >
              <item.icon className="mt-0.5 h-6 w-6 shrink-0 text-mint" aria-hidden />
              <div>
                <h3 className="font-semibold text-mist">{item.title}</h3>
                <p className="mt-2 text-sm text-steel">{item.body}</p>
              </div>
            </motion.div>
          ))}
        </div>
        <div className="mt-12 flex flex-wrap justify-center gap-4">
          <a
            href={repoUrl}
            className="inline-flex items-center justify-center rounded-xl bg-mint px-6 py-3 text-sm font-semibold text-midnight transition hover:brightness-110"
          >
            Explore the repository
          </a>
          <a
            href={docsReadmeUrl}
            className="inline-flex items-center justify-center rounded-xl border border-white/15 px-6 py-3 text-sm font-semibold text-mist hover:border-mint/40"
          >
            Read the documentation
          </a>
        </div>
      </div>
    </AnimatedSection>
  );
}
