import { useState } from "react";
import { motion } from "motion/react";
import Reveal from "../components/Reveal";
import Lightbox from "../components/Lightbox";
import { photos } from "../data/content";

export default function Photography() {
  const [index, setIndex] = useState<number | null>(null);

  return (
    <div className="mx-auto max-w-[1180px] px-6 pb-28 pt-28 sm:px-8 sm:pt-36">
      <Reveal>
        <span className="eyebrow">Photography</span>
        <h1 className="mt-4 text-[clamp(2.2rem,6vw,4rem)] font-bold leading-[1.02] tracking-[-0.03em]">
          Frames of light.
        </h1>
        <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)]">
          A selection of frames from Italy, Greece, and Japan — shot on the
          Nikon Z8. Tap any image to view it full-screen.
        </p>
      </Reveal>

      <div className="mt-14 columns-1 gap-3 sm:columns-2 lg:columns-3 xl:columns-4">
        {photos.map((photo, i) => (
          <Reveal key={photo.full} delay={(i % 4) * 0.05} className="mb-3 break-inside-avoid">
            <motion.button
              onClick={() => setIndex(i)}
              whileHover={{ y: -4 }}
              transition={{ type: "spring", stiffness: 300, damping: 24 }}
              className="group relative block w-full overflow-hidden rounded-[var(--radius-xl)] border border-[var(--color-edge)] bg-[var(--color-surface)]"
            >
              <img
                src={photo.thumb}
                alt={photo.caption ?? "Photograph"}
                loading="lazy"
                className="w-full transform-gpu object-cover transition-transform duration-[1.1s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-[1.05]"
              />
              <div className="absolute inset-0 bg-black/0 transition-colors duration-500 group-hover:bg-black/15" />
              {photo.caption && (
                <div
                  className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-2 p-4 text-left text-[12.5px] leading-snug text-white/0 opacity-0 transition-all duration-500 group-hover:translate-y-0 group-hover:text-white/90 group-hover:opacity-100"
                  style={{
                    background:
                      "linear-gradient(to top, rgba(0,0,0,0.72), transparent)",
                  }}
                >
                  {photo.caption}
                </div>
              )}
            </motion.button>
          </Reveal>
        ))}
      </div>

      <Lightbox
        images={photos}
        index={index}
        onClose={() => setIndex(null)}
        setIndex={setIndex}
      />
    </div>
  );
}
