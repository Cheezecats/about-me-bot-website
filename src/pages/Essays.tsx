import { motion } from "motion/react";
import Reveal from "../components/Reveal";
import { essays } from "../data/content";

export default function Essays() {
  return (
    <div className="relative mx-auto max-w-[860px] px-6 pb-28 pt-28 sm:px-8 sm:pt-36">
      <Reveal>
        <span className="eyebrow">Essays</span>
        <h1 className="mt-4 text-[clamp(2.2rem,6vw,4rem)] font-bold leading-[1.02] tracking-[-0.03em]">
          Research & writing.
        </h1>
        <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)]">
          Academic work on machine learning and medical imaging — with figures
          and full PDFs.
        </p>
      </Reveal>

      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute right-8 top-32 hidden w-36 opacity-40 sm:block"
        initial={{ opacity: 0, x: 18 }}
        animate={{ opacity: 0.4, x: 0 }}
        transition={{ duration: 1, delay: 0.4, ease: [0.25, 1, 0.5, 1] }}
      >
        <div className="mb-3 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
          <span>Field notes</span>
          <span>02</span>
        </div>
        <div className="space-y-2">
          {["72%", "48%", "86%", "35%"].map((width, i) => (
            <motion.div
              key={width}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.8, delay: 0.55 + i * 0.1, ease: [0.25, 1, 0.5, 1] }}
              className="h-px origin-left bg-[var(--color-fg)]"
              style={{ width }}
            />
          ))}
        </div>
      </motion.div>

      <div className="mt-16 flex flex-col gap-16">
        {essays.map((essay, i) => (
          <Reveal key={essay.title} delay={i * 0.05}>
            <motion.article
              whileHover={{ y: -5 }}
              transition={{ type: "spring", stiffness: 280, damping: 24 }}
              className="group relative overflow-hidden rounded-[var(--radius-2xl)] border border-[var(--color-edge)] bg-[var(--color-surface)] p-6 transition-colors duration-500 hover:border-[var(--color-fg)] sm:p-8"
            >
              <motion.div
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 1, ease: [0.25, 1, 0.5, 1] }}
                className="absolute inset-x-0 top-0 h-px origin-left bg-[var(--color-fg)]"
              />
              <div
                className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-700 group-hover:opacity-100"
                style={{
                  background:
                    "radial-gradient(500px 180px at 20% 0%, color-mix(in srgb, var(--color-fg) 7%, transparent), transparent 70%)",
                }}
              />

              <div className="relative z-10 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="mb-4 flex items-center gap-3">
                    <span className="font-mono text-[11px] text-[var(--color-muted)]">
                      0{i + 1}
                    </span>
                    <span className="eyebrow">Research note</span>
                  </div>
                  <h2 className="max-w-2xl text-2xl font-bold leading-tight tracking-tight sm:text-3xl">
                  <a
                    href={essay.pdf}
                    target="_blank"
                    rel="noreferrer"
                    className="transition-colors duration-300 group-hover:text-[var(--color-muted)]"
                  >
                    {essay.title}
                  </a>
                  </h2>
                </div>
                <motion.a
                  href={essay.pdf}
                  target="_blank"
                  rel="noreferrer"
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.97 }}
                  className="group/pdf inline-flex shrink-0 items-center gap-2 rounded-full border border-[var(--color-edge)] px-5 py-2.5 text-[13px] font-medium transition-all duration-300 hover:border-[var(--color-fg)]"
                >
                  <svg className="transition-transform duration-300 group-hover/pdf:translate-y-0.5" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
                  </svg>
                  PDF
                </motion.a>
              </div>

              <p className="relative z-10 mt-6 text-[16px] leading-[1.75] text-[var(--color-muted)]">
                {essay.abstract}
              </p>

              <div className="relative z-10 mt-8 flex flex-col items-center gap-6">
                {essay.figures.map((fig) => (
                  <motion.figure
                    key={fig.src}
                    whileHover={{ y: -4 }}
                    transition={{ type: "spring", stiffness: 280, damping: 24 }}
                    className="group/figure w-full text-center"
                  >
                    <img
                      src={fig.src}
                      alt={fig.alt}
                      loading="lazy"
                      style={{ width: fig.width, maxWidth: "100%" }}
                      className="mx-auto block rounded-[var(--radius-xl)] border border-[var(--color-edge)] shadow-[0_8px_30px_rgba(0,0,0,0.04)] transition-transform duration-700 ease-[cubic-bezier(0.25,1,0.5,1)] group-hover/figure:scale-[1.01]"
                    />
                    <figcaption className="mt-3 text-[12.5px] text-[var(--color-muted)] transition-colors duration-300 group-hover/figure:text-[var(--color-fg)]">
                      {fig.alt}
                    </figcaption>
                  </motion.figure>
                ))}
              </div>
            </motion.article>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
