import { motion } from "motion/react";
import { heroImage, heroCaption, bio } from "../data/content";

const ease = [0.25, 1, 0.5, 1] as const;

export default function Hero() {
  return (
    <section className="relative flex h-[100svh] min-h-[640px] w-full items-center justify-center overflow-hidden">
      {/* Background photograph */}
      <motion.div
        className="absolute inset-0"
        initial={{ scale: 1.08, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 1.6, ease }}
      >
        <img
          src={heroImage}
          alt={heroCaption}
          className="h-full w-full origin-center scale-[1.06] object-cover"
          fetchPriority="high"
        />
      </motion.div>

      {/* Cinematic veils */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.28) 38%, rgba(0,0,0,0.62) 100%)",
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 80% at 50% 42%, transparent 40%, rgba(0,0,0,0.5) 100%)",
        }}
      />

      {/* Content */}
      <div className="relative z-10 mx-auto flex max-w-[1180px] flex-col items-center px-6 text-center">
        <motion.span
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.35, ease }}
          className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-1.5 text-[12px] font-medium uppercase tracking-[0.22em] text-white/75 backdrop-blur-md"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          {bio.location}
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.5, ease }}
          className="text-[clamp(2.8rem,9vw,7.5rem)] font-extrabold leading-[0.92] tracking-[-0.03em] text-white"
        >
          James Sui.
        </motion.h1>

        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.68, ease }}
          className="headline-gradient mt-3 text-[clamp(1.5rem,4.6vw,3.6rem)] font-semibold leading-[1.05] tracking-[-0.02em]"
        >
          Tech, Motion, and Perspective.
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.86, ease }}
          className="mt-7 max-w-xl text-[15px] leading-relaxed text-white/65 sm:text-base"
        >
          A 17-year-old photographer, filmmaker, and technologist exploring the
          space where light, motion, and ideas meet.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.02, ease }}
          className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
        >
          <a
            href="#showcase"
            className="group inline-flex items-center gap-2 rounded-full bg-white px-7 py-3 text-[14px] font-semibold text-black transition-all duration-300 hover:gap-3 hover:shadow-[0_12px_40px_rgba(255,255,255,0.25)]"
          >
            Explore the work
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform duration-300 group-hover:translate-x-0.5">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </a>
          <a
            href={`mailto:${bio.email}`}
            className="inline-flex items-center gap-2 rounded-full border border-white/25 px-7 py-3 text-[14px] font-medium text-white/85 backdrop-blur-md transition-all duration-300 hover:border-white/50 hover:text-white"
          >
            Get in touch
          </a>
        </motion.div>
      </div>

      {/* Scroll cue */}
      <motion.a
        href="#showcase"
        aria-label="Scroll down"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.4 }}
        className="absolute bottom-7 left-1/2 z-10 -translate-x-1/2 flex flex-col items-center gap-2 text-white/55"
      >
        <span className="text-[10px] uppercase tracking-[0.3em]">Scroll</span>
        <span className="flex h-9 w-5 items-start justify-center rounded-full border border-white/30 p-1">
          <span
            className="h-1.5 w-1 rounded-full bg-white/80"
            style={{ animation: "scroll-cue 1.8s ease-in-out infinite" }}
          />
        </span>
      </motion.a>
    </section>
  );
}
