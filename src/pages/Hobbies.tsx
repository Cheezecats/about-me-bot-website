import { useState } from "react";
import { motion } from "motion/react";
import Lightbox from "../components/Lightbox";
import { sports, otherHobbies } from "../data/content";

type LbImage = { full: string; caption?: string };

function Arrow() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export default function Hobbies() {
  const [lbImages, setLbImages] = useState<LbImage[]>([]);
  const [lbIndex, setLbIndex] = useState<number | null>(null);

  const openSport = (sportName: string, images: string[], index: number) => {
    setLbImages(images.map((src) => ({ full: src, caption: sportName })));
    setLbIndex(index);
  };

  return (
    <div className="pb-28 pt-24 sm:pt-32">
      <header className="mx-auto max-w-[1180px] px-6 pb-20 sm:px-8 sm:pb-28">
        <motion.span
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.25, 1, 0.5, 1] }}
          className="cinema-kicker"
        >
          Off camera
        </motion.span>
        <motion.h1
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.08, ease: [0.25, 1, 0.5, 1] }}
          className="mt-5 max-w-4xl text-[clamp(3rem,9.5vw,9rem)] font-semibold leading-[0.82] tracking-[-0.075em] text-[var(--color-sky)]"
        >
          A life
          <br />
          in motion.
        </motion.h1>
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.18, ease: [0.25, 1, 0.5, 1] }}
          className="mt-10 flex flex-col gap-6 border-t border-[var(--color-edge)] pt-5 sm:flex-row sm:items-start sm:justify-between"
        >
          <p className="max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)]">
            Sport, play, and craft—four chapters that have shaped how I spend time away from the camera.
          </p>
          <dl className="grid grid-cols-3 gap-5 text-right sm:min-w-[280px]">
            <div>
              <dt className="cinema-kicker">Chapters</dt>
              <dd className="mt-2 text-xl font-semibold">04</dd>
            </div>
            <div>
              <dt className="cinema-kicker">Since</dt>
              <dd className="mt-2 text-xl font-semibold">2013</dd>
            </div>
            <div>
              <dt className="cinema-kicker">Still going</dt>
              <dd className="mt-2 text-xl font-semibold">Now</dd>
            </div>
          </dl>
        </motion.div>
      </header>

      <div className="cinema-rule" />

      <ol aria-label="Sport chapters">
        {sports.map((sport, chapterIndex) => (
          <li key={sport.name}>
            <section className={`relative min-h-[128svh] border-b border-[var(--color-edge)] px-5 py-10 sm:px-8 sm:py-14 ${chapterIndex % 2 === 0 ? "bg-[color-mix(in_srgb,var(--color-sky)_5%,var(--color-bg))]" : "bg-[var(--color-surface)]"}`}>
              <div className="mx-auto grid min-h-[calc(100svh-5rem)] max-w-[1280px] gap-8 md:sticky md:top-0 md:grid-cols-[1.06fr_0.94fr] md:items-center md:gap-12">
                <motion.button
                  type="button"
                  onClick={() => openSport(sport.name, sport.images, 0)}
                  initial={{ opacity: 0, scale: 0.94, y: 24 }}
                  whileInView={{ opacity: 1, scale: 1, y: 0 }}
                  viewport={{ once: true, margin: "-10%" }}
                  transition={{ duration: 1, ease: [0.25, 1, 0.5, 1] }}
                  whileHover={{ scale: 1.012 }}
                  className={`group relative aspect-[4/5] w-full overflow-hidden rounded-[1.8rem] border-[7px] border-white/70 bg-[var(--color-surface)] text-left shadow-[0_20px_52px_rgba(8,73,135,0.14)] md:aspect-[4/4.6] ${chapterIndex % 2 === 0 ? "md:order-2" : "md:order-1"}`}
                  aria-label={`Open ${sport.name} photo`}
                >
                  <img
                    src={sport.images[0]}
                    alt={`${sport.name} in motion`}
                    loading={chapterIndex === 0 ? "eager" : "lazy"}
                    className="h-full w-full object-cover transition-transform duration-[1.4s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-[1.055]"
                  />
                  <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-[#163852]/70 to-transparent" />
                  <span className="absolute bottom-5 left-5 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.19em] text-white/90">
                    Open still <Arrow />
                  </span>
                </motion.button>

                <motion.div
                  initial={{ opacity: 0, y: 26 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-10%" }}
                  transition={{ duration: 0.85, delay: 0.08, ease: [0.25, 1, 0.5, 1] }}
                  className={`relative md:py-12 ${chapterIndex % 2 === 0 ? "md:order-1" : "md:order-2"}`}
                >
                  <span className="cinema-kicker">Chapter {String(chapterIndex + 1).padStart(2, "0")}</span>
                  <div className="pointer-events-none absolute -left-4 top-6 select-none text-[clamp(7rem,18vw,16rem)] font-semibold leading-none tracking-[-0.1em] text-[var(--color-sky)] opacity-[0.13]">
                    {sport.since}
                  </div>
                  <div className="relative mt-6 flex items-center gap-3">
                    <span className="text-3xl" aria-hidden="true">{sport.emoji}</span>
                    <span className="rounded-lg bg-[var(--color-turquoise)] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#163852]">
                      Since {sport.since}
                    </span>
                  </div>
                  <h2 id={`chapter-${sport.name.toLowerCase().replaceAll(" ", "-")}`} className="relative mt-6 text-[clamp(3.1rem,7.5vw,7.4rem)] font-semibold leading-[0.84] tracking-[-0.075em] text-[var(--color-sky)]">
                    {sport.name}
                  </h2>
                  <p className="relative mt-8 max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)] sm:text-[17px]">
                    {sport.description}
                  </p>
                  <div className="relative mt-9 flex flex-wrap gap-3">
                    {sport.images.slice(1).map((src, imageIndex) => (
                      <motion.button
                        key={src}
                        type="button"
                        onClick={() => openSport(sport.name, sport.images, imageIndex + 1)}
                        whileHover={{ y: -5 }}
                        whileTap={{ scale: 0.98 }}
                        className="group/thumb relative h-20 w-28 overflow-hidden rounded-xl border-[3px] border-white/75 bg-[var(--color-surface)] shadow-[0_8px_20px_rgba(8,73,135,0.12)] sm:h-24 sm:w-36"
                        aria-label={`Open ${sport.name} photo ${imageIndex + 2}`}
                      >
                        <img src={src} alt="" loading="lazy" className="h-full w-full object-cover transition-transform duration-700 group-hover/thumb:scale-110" />
                      </motion.button>
                    ))}
                    <span className="flex h-20 items-center border-l border-[var(--color-edge)] pl-4 text-[10px] font-medium uppercase tracking-[0.16em] text-[var(--color-muted)] sm:h-24">
                      {sport.images.length} stills
                    </span>
                  </div>
                </motion.div>
              </div>
            </section>
          </li>
        ))}
      </ol>

      <section className="mx-auto max-w-[1180px] px-6 pt-24 sm:px-8 sm:pt-32">
        <span className="cinema-kicker">Between the chapters</span>
        <div className="mt-5 flex flex-col gap-5 border-b border-[var(--color-edge)] pb-10 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="max-w-2xl text-[clamp(2.8rem,6vw,5.8rem)] font-semibold leading-[0.9] tracking-[-0.065em]">
            Small obsessions, kept close.
          </h2>
          <p className="max-w-sm text-[15px] leading-relaxed text-[var(--color-muted)]">The quieter routines that fill the space between a hard practice and the next trip.</p>
        </div>

        <div className="mt-4">
          {otherHobbies.map((hobby, index) => (
            <motion.article
              key={hobby.name}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-12%" }}
              transition={{ duration: 0.75, delay: index * 0.08, ease: [0.25, 1, 0.5, 1] }}
              className="group grid gap-4 border-b border-[var(--color-edge)] py-8 sm:grid-cols-[86px_0.72fr_1.28fr] sm:items-start sm:gap-8"
            >
              <span className="text-4xl" aria-hidden="true">{hobby.emoji}</span>
              <h3 className="text-3xl font-semibold tracking-[-0.05em] transition-colors duration-300 group-hover:text-[var(--color-accent)]">{hobby.name}</h3>
              <p className="text-[15px] leading-relaxed text-[var(--color-muted)]">{hobby.description}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <Lightbox images={lbImages} index={lbIndex} onClose={() => setLbIndex(null)} setIndex={setLbIndex} />
    </div>
  );
}
