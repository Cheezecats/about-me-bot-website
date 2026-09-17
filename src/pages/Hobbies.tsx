import { useState } from "react";
import { motion } from "motion/react";
import Reveal from "../components/Reveal";
import Lightbox from "../components/Lightbox";
import { sports, otherHobbies } from "../data/content";

type LbImage = { full: string; caption?: string };

export default function Hobbies() {
  const [lbImages, setLbImages] = useState<LbImage[]>([]);
  const [lbIndex, setLbIndex] = useState<number | null>(null);

  const openSport = (sportName: string, images: string[], j: number) => {
    setLbImages(images.map((src) => ({ full: src, caption: sportName })));
    setLbIndex(j);
  };

  return (
    <div className="relative mx-auto max-w-[1000px] px-6 pb-28 pt-28 sm:px-8 sm:pt-36">
      <Reveal>
        <span className="eyebrow">Hobbies</span>
        <h1 className="mt-4 text-[clamp(2.2rem,6vw,4rem)] font-bold leading-[1.02] tracking-[-0.03em]">
          Sport, play, craft.
        </h1>
        <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)]">
          A life in motion — ordered by the year each passion began.
        </p>
      </Reveal>

      <motion.dl
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.7, delay: 0.15, ease: [0.25, 1, 0.5, 1] }}
        className="mt-10 grid max-w-2xl grid-cols-3 border-y border-[var(--color-edge)] py-5"
      >
        <div className="pr-4">
          <dt className="eyebrow">Sports</dt>
          <dd className="mt-1 text-2xl font-bold tracking-tight">04</dd>
        </div>
        <div className="border-l border-[var(--color-edge)] px-4">
          <dt className="eyebrow">First started</dt>
          <dd className="mt-1 text-2xl font-bold tracking-tight">2013</dd>
        </div>
        <div className="border-l border-[var(--color-edge)] pl-4">
          <dt className="eyebrow">Photo moments</dt>
          <dd className="mt-1 text-2xl font-bold tracking-tight">09</dd>
        </div>
      </motion.dl>

      {/* Sports timeline */}
      <div className="relative mt-14 pl-8 sm:pl-12">
        <div className="mb-7 flex items-center justify-between pr-1">
          <span className="eyebrow">The timeline</span>
          <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-[var(--color-muted)]">
            2013 — now
          </span>
        </div>
        <motion.div
          initial={{ scaleY: 0, opacity: 0 }}
          whileInView={{ scaleY: 1, opacity: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 1.4, ease: [0.25, 1, 0.5, 1] }}
          className="absolute bottom-6 left-[3px] top-12 w-px origin-top bg-gradient-to-b from-[var(--color-fg)] via-[var(--color-edge)] to-transparent sm:left-[5px]"
        />
        {sports.map((sport, i) => (
          <Reveal key={sport.name} delay={i * 0.05}>
            <motion.div
              whileHover={{ x: 4 }}
              transition={{ type: "spring", stiffness: 280, damping: 24 }}
              className="group relative mb-10 overflow-hidden rounded-[var(--radius-2xl)] border border-[var(--color-edge)] bg-[var(--color-surface)] p-5 transition-colors duration-500 hover:border-[var(--color-fg)] sm:p-7"
            >
              <div
                className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-700 group-hover:opacity-100"
                style={{
                  background:
                    "radial-gradient(500px 220px at 0% 0%, color-mix(in srgb, var(--color-fg) 6%, transparent), transparent 72%)",
                }}
              />
              <motion.span
                initial={{ scale: 0, opacity: 0 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ type: "spring", stiffness: 360, damping: 20, delay: i * 0.05 }}
                className="absolute -left-[27px] top-7 h-2.5 w-2.5 rounded-full bg-[var(--color-fg)] shadow-[0_0_0_5px_var(--color-bg),0_0_20px_var(--color-fg)] sm:-left-[39px]"
              />

              <div className="relative flex flex-wrap items-center gap-x-3 gap-y-2">
                <motion.span
                  whileHover={{ rotate: 8, scale: 1.12 }}
                  transition={{ type: "spring", stiffness: 360, damping: 16 }}
                  className="flex h-10 w-10 shrink-0 origin-bottom items-center justify-center rounded-full bg-[var(--color-bg)] text-2xl shadow-[0_6px_18px_rgba(0,0,0,0.06)]"
                >
                  {sport.emoji}
                </motion.span>
                <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
                  {sport.name}
                </h2>
                <span className="rounded-full border border-[var(--color-edge)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-muted)]">
                  Since {sport.since}
                </span>
              </div>

              <p className="relative mt-5 max-w-2xl text-[15.5px] leading-relaxed text-[var(--color-muted)]">
                {sport.description}
              </p>

              <div className="relative mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                {sport.images.map((src, j) => (
                  <motion.button
                    key={src}
                    onClick={() => openSport(sport.name, sport.images, j)}
                    aria-label={`Open ${sport.name} photo ${j + 1}`}
                    whileHover={{ y: -6, scale: 1.015 }}
                    whileTap={{ scale: 0.98 }}
                    transition={{ type: "spring", stiffness: 300, damping: 24 }}
                    className="group relative aspect-[4/3] overflow-hidden rounded-[var(--radius-xl)] border border-[var(--color-edge)] bg-[var(--color-surface)]"
                  >
                    <img
                      src={src}
                      alt={`${sport.name} ${j + 1}`}
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-[1.1s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-[1.06]"
                    />
                    <div className="absolute inset-0 bg-black/0 transition-colors duration-500 group-hover:bg-black/15" />
                  </motion.button>
                ))}
              </div>
            </motion.div>
          </Reveal>
        ))}
      </div>

      {/* Other hobbies */}
      <div className="mt-20 border-t border-[var(--color-edge)] pt-16">
        <Reveal>
          <span className="eyebrow">More</span>
        </Reveal>
        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          {otherHobbies.map((hobby, i) => (
            <Reveal key={hobby.name} delay={i * 0.06}>
              <motion.div
                whileHover={{ y: -7 }}
                transition={{ type: "spring", stiffness: 280, damping: 24 }}
                className="group relative h-full overflow-hidden rounded-[var(--radius-2xl)] border border-[var(--color-edge)] bg-[var(--color-surface)] p-7 transition-colors duration-500 hover:border-[var(--color-fg)]"
              >
                <div
                  className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full opacity-0 blur-3xl transition-opacity duration-700 group-hover:opacity-20"
                  style={{ background: "var(--color-fg)" }}
                />
                <div className="relative flex items-center gap-3">
                  <motion.span
                    whileHover={{ rotate: -8, scale: 1.12 }}
                    transition={{ type: "spring", stiffness: 360, damping: 16 }}
                    className="origin-bottom text-3xl"
                  >
                    {hobby.emoji}
                  </motion.span>
                  <h3 className="text-xl font-bold tracking-tight">
                    {hobby.name}
                  </h3>
                </div>
                <p className="relative mt-4 text-[15px] leading-relaxed text-[var(--color-muted)]">
                  {hobby.description}
                </p>
                <div className="relative mt-6 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)] transition-colors duration-300 group-hover:text-[var(--color-fg)]">
                  <span className="h-px w-6 bg-current transition-all duration-500 group-hover:w-10" />
                  Part of the mix
                </div>
              </motion.div>
            </Reveal>
          ))}
        </div>
      </div>

      <Lightbox
        images={lbImages}
        index={lbIndex}
        onClose={() => setLbIndex(null)}
        setIndex={setLbIndex}
      />
    </div>
  );
}
