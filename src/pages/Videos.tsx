import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { videos, youtubeThumb, type VideoItem } from "../data/content";

export default function Videos() {
  const [active, setActive] = useState<VideoItem | null>(null);

  useEffect(() => {
    if (!active) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setActive(null); };
    window.addEventListener("keydown", close);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", close); document.body.style.overflow = previousOverflow; };
  }, [active]);

  const featured = videos[0];
  return (
    <div className="pb-28 pt-20 sm:pt-24">
      <section className="relative overflow-hidden bg-[var(--color-sky)] px-5 pb-14 pt-16 text-white sm:px-8 sm:pb-20 sm:pt-20">
        <div className="pointer-events-none absolute inset-0 opacity-75" style={{ background: "radial-gradient(circle at 88% 8%, rgba(255,255,255,0.5), transparent 25%), linear-gradient(125deg, transparent 38%, rgba(34,207,203,0.55) 100%)" }} />
        <div className="relative mx-auto max-w-[1180px]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/70">Moving pictures · 2024—2025</p>
          <div className="mt-5 grid gap-9 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
            <div><h1 className="text-[clamp(3.8rem,9vw,8.8rem)] font-semibold leading-[0.78] tracking-[-0.08em]">A little<br />closer.</h1><p className="mt-7 max-w-md text-[16px] leading-relaxed text-white/80">Small films from the places I have been, built around the feeling that stays after a scene ends.</p></div>
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: [0.25, 1, 0.5, 1] }} className="border-[8px] border-white/80 bg-white p-2 shadow-[0_22px_60px_rgba(7,56,129,0.3)]">
              <button type="button" onClick={() => setActive(featured)} className="group relative block w-full overflow-hidden text-left" aria-label={`Watch ${featured.title}`}>
                <img src={youtubeThumb(featured.youtubeId)} alt={`${featured.title} film thumbnail`} fetchPriority="high" className="aspect-video w-full object-cover transition duration-700 group-hover:scale-[1.025]" />
                <span className="absolute bottom-4 left-4 flex items-center gap-2 bg-white px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#163852] shadow-sm transition group-hover:bg-[var(--color-turquoise)]">Watch film <Play /></span>
              </button>
            </motion.div>
          </div>
          <div className="mt-8 grid gap-4 border-t border-white/35 pt-5 sm:grid-cols-[1fr_auto] sm:items-start"><div><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/65">Featured · {featured.quality} · {featured.year}</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.045em]">{featured.title}</h2></div><p className="max-w-xl text-[14px] leading-relaxed text-white/82 sm:text-right">{featured.description}</p></div>
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 py-24 sm:px-8 sm:py-32" aria-label="Film collection">
        <div className="flex flex-col gap-4 border-b border-[var(--color-edge)] pb-8 sm:flex-row sm:items-end sm:justify-between"><div><span className="cinema-kicker">The collection</span><h2 className="mt-4 text-[clamp(2.8rem,6vw,5.8rem)] font-semibold leading-[0.9] tracking-[-0.065em]">Three films.</h2></div><p className="max-w-sm text-[15px] leading-relaxed text-[var(--color-muted)] sm:text-right">Open any film directly, then return to the full collection whenever you are ready.</p></div>
        <div className="mt-9 grid gap-5 md:grid-cols-3">{videos.map((video, index) => <FilmCard key={video.id} video={video} index={index} onWatch={() => setActive(video)} />)}</div>
      </section>

      <AnimatePresence>{active && <motion.div className="fixed inset-0 z-50 grid place-items-center bg-[#071d31]/88 p-4 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} role="dialog" aria-modal="true" aria-label={`Playing ${active.title}`} onMouseDown={(event) => { if (event.target === event.currentTarget) setActive(null); }}><motion.div initial={{ opacity: 0, y: 20, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 14, scale: 0.98 }} transition={{ duration: 0.28 }} className="w-full max-w-5xl overflow-hidden rounded-2xl bg-[#102c46] shadow-2xl"><div className="aspect-video bg-black"><iframe className="h-full w-full" src={`https://www.youtube-nocookie.com/embed/${active.youtubeId}?autoplay=1`} title={active.title} allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen /></div><div className="flex items-center justify-between gap-4 px-5 py-4 text-white"><div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-turquoise)]">{active.quality} · {active.year}</p><h3 className="mt-1 text-xl font-semibold">{active.title}</h3></div><button type="button" onClick={() => setActive(null)} className="rounded-lg border border-white/25 px-4 py-2 text-[13px] font-semibold text-white transition hover:border-[var(--color-turquoise)] hover:text-[var(--color-turquoise)]">Close</button></div></motion.div></motion.div>}</AnimatePresence>
    </div>
  );
}

function FilmCard({ video, index, onWatch }: { video: VideoItem; index: number; onWatch: () => void }) {
  return <motion.article initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-10%" }} transition={{ duration: 0.6, delay: index * 0.08 }} className="overflow-hidden rounded-[1.4rem] border border-[var(--color-edge)] bg-[var(--color-surface)] p-3 shadow-[0_12px_32px_rgba(8,73,135,0.1)]"><button type="button" onClick={onWatch} className="group relative block w-full overflow-hidden rounded-xl text-left" aria-label={`Watch ${video.title}`}><img src={youtubeThumb(video.youtubeId)} alt={`${video.title} thumbnail`} loading="lazy" className="aspect-[4/3] w-full object-cover transition duration-700 group-hover:scale-[1.045]" /><span className="absolute bottom-3 left-3 flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--color-turquoise)] text-[#163852] shadow-sm"><Play /></span></button><div className="px-2 pb-2 pt-5"><p className="text-[10px] font-semibold uppercase tracking-[0.19em] text-[var(--color-sky)]">{String(index + 1).padStart(2, "0")} · {video.quality} · {video.year}</p><h3 className="mt-2 text-3xl font-semibold tracking-[-0.05em]">{video.title}</h3><p className="mt-3 min-h-[5rem] text-[14px] leading-relaxed text-[var(--color-muted)]">{video.description}</p><button type="button" onClick={onWatch} className="mt-5 inline-flex items-center gap-2 rounded-lg border border-[var(--color-edge)] px-4 py-2.5 text-[12px] font-semibold text-[var(--color-fg)] transition hover:border-[var(--color-sky)] hover:text-[var(--color-sky)]">Watch now <Arrow /></button></div></motion.article>;
}

function Play() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" /></svg>; }
function Arrow() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>; }
