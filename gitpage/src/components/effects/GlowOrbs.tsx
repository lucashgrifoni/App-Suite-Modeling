import { motion } from "framer-motion";

/** Soft radial glows for depth (no external assets). */
export function GlowOrbs() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      <motion.div
        className="absolute -left-[20%] top-[-10%] h-[55vh] w-[55vh] rounded-full bg-mint/20 blur-[120px]"
        animate={{ opacity: [0.35, 0.55, 0.35], scale: [1, 1.05, 1] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -right-[15%] top-[20%] h-[45vh] w-[45vh] rounded-full bg-midnight blur-[100px]"
        style={{ boxShadow: "0 0 120px rgba(124,131,148,0.35)" }}
        animate={{ opacity: [0.25, 0.45, 0.25] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[-20%] left-[25%] h-[40vh] w-[40vh] rounded-full bg-steel/25 blur-[100px]"
        animate={{ y: [0, -20, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
