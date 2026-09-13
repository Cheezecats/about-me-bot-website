import { useRef, useState } from "react";
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll, useTransform } from "motion/react";
import Reveal from "../components/Reveal";
import Lightbox from "../components/Lightbox";
import { photos } from "../data/content";
import photoDimensions from "../../data/photo_dimensions.json";

function SelectedJourney({ onOpen }: { onOpen: (index: number) => void }) {
  const journeyRef = useRef<HTMLElement>(null);
  const reduceMotion = useReducedMotion();
  const choices = photos.filter((photo) => photo.featured);
  const [choiceIndex, setChoiceIndex] = useState(0);
  const { scrollYProgress } = useScroll({ target: journeyRef, offset: ["start start", "end end"] });
  const photoY = useTransform(scrollYProgress, [0, 1], ["0%", "-5%"]);
  const copyY = useTransform(scrollYProgress, [0, 1], ["0%", "-13%"]);
  useMotionValueEvent(scrollYProgress, "change", (progress) => {
    if (reduceMotion || choices.length < 2) return;
    const next = Math.min(choices.length - 1, Math.floor(progress * choices.length));
    setChoiceIndex((current) => current === next ? current : next);
  });
  if (!choices.length) return null;
  const active = choices[choiceIndex];
  const archiveIndex = photos.indexOf(active);
  return <section ref={journeyRef} id="authors-choice" style={{ scrollMarginTop: 0 }} className="relative h-[220svh] min-h-[1450px]">
    <div className="sticky top-0 flex min-h-[690px] overflow-hidden bg-[var(--color-bg)] px-5 py-24 sm:px-8 sm:py-28">
      <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(circle at 86% 14%, color-mix(in srgb, var(--color-turquoise) 38%, transparent), transparent 24%), linear-gradient(135deg, color-mix(in srgb, var(--color-sky) 12%, var(--color-bg)), var(--color-bg) 52%, color-mix(in srgb, var(--color-coral) 15%, var(--color-bg)))" }} />
      <div className="relative z-10 mx-auto grid w-full max-w-[1240px] gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-center">
        <motion.div style={{ y: reduceMotion ? "0%" : copyY }} className="order-2 lg:order-1"><p className="cinema-kicker">Author’s choice · scroll through</p><h1 className="mt-5 text-[clamp(3.8rem,8vw,8rem)] font-semibold leading-[0.78] tracking-[-0.08em] text-[var(--color-sky)]">Frames<br /><span className="text-[var(--color-fg)]">of light.</span></h1><p className="mt-8 max-w-md text-[15px] leading-relaxed text-[var(--color-muted)] sm:text-[17px]">{active.caption ?? "A frame selected from the archive."}</p><div className="mt-8 flex flex-wrap items-center gap-3"><button type="button" onClick={() => onOpen(archiveIndex)} className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-sky)] px-5 py-3 text-[13px] font-semibold text-white transition hover:-translate-y-0.5">Open full frame <Arrow /></button><a href="#archive" className="rounded-xl border border-[var(--color-edge)] px-5 py-3 text-[12px] font-semibold uppercase tracking-[0.15em] text-[var(--color-fg)] transition hover:border-[var(--color-sky)] hover:text-[var(--color-sky)]">Full archive</a></div><div className="mt-10 flex items-center gap-2" aria-label="Selected photographs">{choices.map((photo, index) => <button key={photo.full} type="button" onClick={() => setChoiceIndex(index)} className={`h-2 rounded-full transition-all ${index === choiceIndex ? "w-10 bg-[var(--color-sky)]" : "w-2 bg-[var(--color-edge)] hover:bg-[var(--color-turquoise)]"}`} aria-label={`View selected photo ${index + 1}`} aria-current={index === choiceIndex} />)}<span className="ml-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">{String(choiceIndex + 1).padStart(2, "0")} / {String(choices.length).padStart(2, "0")}</span></div></motion.div>
        <motion.div style={{ y: reduceMotion ? "0%" : photoY }} className="order-1 lg:order-2"><AnimatePresence mode="wait"><motion.figure key={active.full} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: reduceMotion ? 0 : 0.58, ease: [0.25, 1, 0.5, 1] }} className="relative flex min-h-[360px] items-center justify-center overflow-hidden rounded-[1.7rem] border-[11px] border-white/80 bg-[color-mix(in_srgb,var(--color-sky)_7%,white)] p-3 shadow-[0_26px_70px_rgba(8,73,135,0.2)] sm:min-h-[560px] sm:p-5"><img src={active.full} alt={active.caption ?? "Selected photograph"} fetchPriority="high" className="max-h-[68svh] w-full object-contain" /><span className="pointer-events-none absolute right-5 top-5 h-14 w-14 rounded-full border-[5px] border-white/75 bg-[var(--color-coral)] opacity-90" aria-hidden="true" /></motion.figure></AnimatePresence></motion.div>
      </div>
    </div>
  </section>;
}

export default function Photography() {
  const [index, setIndex] = useState<number | null>(null);
  return <div><SelectedJourney onOpen={setIndex} />
    <section id="archive" className="mx-auto max-w-[1280px] px-5 py-24 sm:px-8 sm:py-32" aria-label="Photography archive"><Reveal><div className="flex flex-col gap-5 border-b border-[var(--color-edge)] pb-10 sm:flex-row sm:items-end sm:justify-between"><div><span className="cinema-kicker">The archive</span><h2 className="mt-4 text-[clamp(2.8rem,6vw,5.8rem)] font-semibold leading-[0.9] tracking-[-0.065em]">Every frame.</h2></div><p className="max-w-sm text-[15px] leading-relaxed text-[var(--color-muted)] sm:text-right">A selection of frames from Italy, Greece, Japan, and closer to home—shot on the Nikon Z8.</p></div></Reveal>
      <div className="mt-8 columns-1 gap-3 sm:columns-2 lg:columns-3 xl:columns-4">{photos.map((photo, photoIndex) => { const dimensions = (photoDimensions as Record<string, { width: number; height: number }>)[decodeURIComponent(photo.thumb.split("/").at(-1) ?? "")]; return <Reveal key={photo.full} delay={(photoIndex % 4) * 0.05} className="mb-3 break-inside-avoid"><motion.button type="button" onClick={() => setIndex(photoIndex)} whileHover={{ y: -4 }} whileTap={{ scale: 0.985 }} transition={{ type: "spring", stiffness: 300, damping: 24 }} className={`group relative block w-full overflow-hidden rounded-[1.15rem] border-[3px] bg-white text-left shadow-[0_8px_24px_rgba(8,73,135,0.09)] ${photo.featured ? "border-[var(--color-turquoise)]" : "border-white"}`} aria-label={`Open ${photo.caption ?? `photograph ${photoIndex + 1}`}`}><img src={photo.thumb} width={dimensions?.width} height={dimensions?.height} alt={photo.caption ?? "Photograph"} loading="lazy" className="w-full object-cover transition-transform duration-[1.1s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-[1.045]" /><div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[#163852]/72 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />{photo.caption && <p className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-3 p-4 text-[12px] leading-snug text-white opacity-0 transition-all duration-500 group-hover:translate-y-0 group-hover:opacity-100">{photo.caption}</p>}{photo.featured && <span className="absolute left-3 top-3 rounded-lg bg-[var(--color-turquoise)] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-[#163852]">Selected</span>}</motion.button></Reveal>; })}</div>
    </section><Lightbox images={photos} index={index} onClose={() => setIndex(null)} setIndex={setIndex} /></div>;
}

function Arrow() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>; }
