import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import Reveal from "../components/Reveal";
import { videos, youtubeThumb, type VideoItem } from "../data/content";

function PlayIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5.5v13l11-6.5z" />
    </svg>
  );
}

export default function Videos() {
  const [active, setActive] = useState<VideoItem | null>(null);

  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setActive(null);
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [active]);

  return (
    <div className="mx-auto max-w-[1040px] px-6 pb-28 pt-28 sm:px-8 sm:pt-36">
      <Reveal>
        <span className="eyebrow">Videos</span>
        <h1 className="mt-4 text-[clamp(2.2rem,6vw,4rem)] font-bold leading-[1.02] tracking-[-0.03em]">
          Film & motion.
        </h1>
        <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)]">
          Travel films and vlogs captured in 8K and 4K on the Nikon Z8. Click a
          card to play.
        </p>
      </Reveal>

      <div className="mt-14 flex flex-col gap-12">
        {videos.map((v, i) => (
          <Reveal key={v.id} delay={i * 0.06}>
            <div className="grid gap-6 md:grid-cols-[1.4fr_1fr] md:items-center">
              <motion.button
                onClick={() => setActive(v)}
                whileHover={{ y: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
                className="group relative aspect-video w-full overflow-hidden rounded-[var(--radius-2xl)] border border-[var(--color-edge)] bg-black"
              >
                <img
                  src={youtubeThumb(v.youtubeId)}
                  alt={v.title}
                  loading="lazy"
                  className="h-full w-full object-cover opacity-90 transition-all duration-700 group-hover:scale-[1.04] group-hover:opacity-100"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/20 transition-colors duration-500 group-hover:bg-black/30">
                  <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white/90 text-black shadow-[0_10px_40px_rgba(0,0,0,0.4)] transition-transform duration-500 group-hover:scale-110">
                    <PlayIcon />
                  </span>
                </div>
                <span className="absolute left-4 top-4 rounded-full bg-black/55 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-white backdrop-blur-md">
                  {v.quality} · {v.year}
                </span>
              </motion.button>

              <div>
                <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
                  {v.title}
                </h2>
                <span className="mt-2 inline-block text-[13px] font-medium text-[var(--color-muted)]">
                  {v.quality} · {v.year}
                </span>
                <p className="mt-4 text-[15.5px] leading-relaxed text-[var(--color-muted)]">
                  {v.description}
                </p>
                <button
                  onClick={() => setActive(v)}
                  className="mt-6 inline-flex items-center gap-2 rounded-full border border-[var(--color-edge)] px-5 py-2.5 text-[13.5px] font-medium transition-all duration-300 hover:border-[var(--color-fg)]"
                >
                  Watch film
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </button>
              </div>
            </div>
          </Reveal>
        ))}
      </div>

      <AnimatePresence>
        {active && (
          <motion.div
            className="fixed inset-0 z-[120] flex items-center justify-center p-4 sm:p-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            onClick={() => setActive(null)}
            role="dialog"
            aria-modal="true"
            aria-label={active.title}
          >
            <div className="absolute inset-0 bg-black/90 backdrop-blur-xl" />
            <motion.div
              className="relative z-[5] w-full max-w-4xl"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={{ duration: 0.35, ease: [0.25, 1, 0.5, 1] }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="aspect-video w-full overflow-hidden rounded-[var(--radius-2xl)] bg-black shadow-[0_0_80px_rgba(0,0,0,0.6)]">
                <iframe
                  className="h-full w-full"
                  src={`https://www.youtube.com/embed/${active.youtubeId}?autoplay=1&rel=0&modestbranding=1`}
                  title={active.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  referrerPolicy="strict-origin-when-cross-origin"
                  allowFullScreen
                />
              </div>
              <div className="mt-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white">{active.title}</h3>
                <button
                  onClick={() => setActive(null)}
                  className="rounded-full border border-white/20 px-4 py-2 text-[13px] font-medium text-white/80 transition hover:border-white/50 hover:text-white"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
