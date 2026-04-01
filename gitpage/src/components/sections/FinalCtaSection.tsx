import { motion } from "framer-motion";
import { ArrowRight, Compass, FileText, Hammer } from "lucide-react";
import { docsReadmeUrl, issuesUrl, repoUrl } from "../../config/site";

const actions = [
  {
    href: repoUrl,
    label: "View the project",
    sub: "Source, issues, and roadmap",
    icon: Compass,
    primary: true,
  },
  {
    href: docsReadmeUrl,
    label: "Explore documentation",
    sub: "Setup, architecture, and workflows",
    icon: FileText,
    primary: false,
  },
  {
    href: issuesUrl,
    label: "Contribute",
    sub: "Good first issues welcome",
    icon: Hammer,
    primary: false,
  },
];

export function FinalCtaSection() {
  return (
    <section
      id="cta"
      className="relative overflow-hidden border-t border-white/10 py-24 md:py-32"
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-mint/10 via-transparent to-transparent" />
      <div className="relative mx-auto max-w-5xl px-4 text-center md:px-8">
        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="font-display text-3xl font-semibold tracking-tight text-mist md:text-4xl lg:text-5xl"
        >
          Start modeling threats like you mean it
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.05 }}
          className="mx-auto mt-5 max-w-2xl text-lg text-steel"
        >
          Ship safer systems with structured analysis, explainable outputs, and automation that
          fits your pipeline.
        </motion.p>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {actions.map((item, i) => {
            const Icon = item.icon;
            return (
              <motion.a
                key={item.label}
                href={item.href}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                whileHover={{ y: -3 }}
                className={`group flex flex-col rounded-2xl border p-6 text-left transition ${
                  item.primary
                    ? "border-mint/40 bg-mint/10 shadow-mint/20 shadow-[0_0_40px_-12px_rgba(8,185,139,0.5)]"
                    : "border-white/10 bg-white/[0.03] hover:border-mint/30"
                }`}
              >
                <Icon
                  className={`h-6 w-6 ${
                    item.primary ? "text-mint" : "text-steel group-hover:text-mint"
                  }`}
                />
                <span className="mt-4 font-semibold text-mist">{item.label}</span>
                <span className="mt-1 text-sm text-steel">{item.sub}</span>
                <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-mint">
                  Continue
                  <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                </span>
              </motion.a>
            );
          })}
        </div>
      </div>
    </section>
  );
}
