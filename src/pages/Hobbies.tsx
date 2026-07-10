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
    <div className="mx-auto max-w-[1000px] px-6 pb-28 pt-28 sm:px-8 sm:pt-36">
      <Reveal>
        <span className="eyebrow">Hobbies</span>
        <h1 className="mt-4 text-[clamp(2.2rem,6vw,4rem)] font-bold leading-[1.02] tracking-[-0.03em]">
          Sport, play, craft.
        </h1>
        <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)]">
          A life in motion — ordered by the year each passion began.
        </p>
      </Reveal>

      {/* Sports timeline */}
      <div className="relative mt-16 pl-8 sm:pl-12">
        <div className="absolute bottom-2 left-[3px] top-2 w-px bg-[var(--color-edge)] sm:left-[5px]" />
        {sports.map((sport, i) => (
          <Reveal key={sport.name} delay={i * 0.05}>
            <div className="relative mb-16 last:mb-0">
              <span className="absolute -left-[27px] top-2 h-2.5 w-2.5 rounded-full bg-[var(--color-fg)] sm:-left-[39px]" />

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className="text-3xl">{sport.emoji}</span>
                <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
                  {sport.name}
                </h2>
                <span className="rounded-full bg-[var(--color-surface)] px-3 py-1 text-[12px] font-semibold tracking-wide text-[var(--color-muted)]">
                  Since {sport.since}
                </span>
              </div>

              <p className="mt-4 max-w-2xl text-[15.5px] leading-relaxed text-[var(--color-muted)]">
                {sport.description}
              </p>

              <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                {sport.images.map((src, j) => (
                  <motion.button
                    key={src}
                    onClick={() => openSport(sport.name, sport.images, j)}
                    whileHover={{ y: -4 }}
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
            </div>
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
              <div className="h-full rounded-[var(--radius-2xl)] border border-[var(--color-edge)] bg-[var(--color-surface)] p-7">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{hobby.emoji}</span>
                  <h3 className="text-xl font-bold tracking-tight">
                    {hobby.name}
                  </h3>
                </div>
                <p className="mt-4 text-[15px] leading-relaxed text-[var(--color-muted)]">
                  {hobby.description}
                </p>
              </div>
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
