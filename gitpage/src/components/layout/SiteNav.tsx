import { motion, useScroll, useTransform } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useState } from "react";

const links = [
  { href: "#about", label: "About" },
  { href: "#differentiators", label: "Why it wins" },
  { href: "#methodologies", label: "Methodologies" },
  { href: "#features", label: "Capabilities" },
  { href: "#ai", label: "AI & PLOT4ai" },
  { href: "#templates", label: "Templates" },
  { href: "#opensource", label: "Open source" },
];

export function SiteNav() {
  const [open, setOpen] = useState(false);
  const { scrollY } = useScroll();

  return (
    <motion.header
      className="fixed inset-x-0 top-0 z-50 border-b border-white/5"
      style={{
        backgroundColor: useTransform(
          scrollY,
          [0, 80],
          ["rgba(12, 18, 76, 0.45)", "rgba(12, 18, 76, 0.92)"],
        ),
        backdropFilter: useTransform(
          scrollY,
          [0, 80],
          ["blur(8px)", "blur(20px)"],
        ),
      }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 md:px-8">
        <a
          href="#top"
          className="group flex items-center gap-2 font-semibold tracking-tight text-mist"
        >
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-mint/40 bg-mint/10 text-mint shadow-[0_0_24px_-4px_color-mix(in_srgb,var(--color-mint)_20%,transparent)] transition group-hover:border-mint/70">
            ASM
          </span>
          <span className="hidden sm:inline">App Suite Modeling</span>
        </a>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-lg px-3 py-2 text-sm text-steel transition hover:bg-white/5 hover:text-mist"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <button
          type="button"
          className="inline-flex items-center justify-center rounded-lg border border-white/10 p-2 text-mist lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          <span className="sr-only">Toggle menu</span>
        </button>
      </div>

      {open ? (
        <div
          id="mobile-nav"
          className="border-t border-white/10 bg-midnight/95 px-4 py-4 lg:hidden"
        >
          <div className="flex flex-col gap-1">
            {links.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="rounded-lg px-3 py-2 text-steel hover:bg-white/5 hover:text-mist"
                onClick={() => setOpen(false)}
              >
                {l.label}
              </a>
            ))}
          </div>
        </div>
      ) : null}
    </motion.header>
  );
}
