import { motion, useInView } from "framer-motion";
import { useRef, type ReactNode } from "react";

type Props = {
  id?: string;
  className?: string;
  children: ReactNode;
  delay?: number;
};

export function AnimatedSection({ id, className, children, delay = 0 }: Props) {
  const ref = useRef<HTMLElement | null>(null);
  const isInView = useInView(ref, { once: true, margin: "-12% 0px" });

  return (
    <motion.section
      ref={ref}
      id={id}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 40 }}
      transition={{
        duration: 0.65,
        delay,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={className}
    >
      {children}
    </motion.section>
  );
}
