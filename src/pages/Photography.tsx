import { useEffect, useState } from "react";
import { motion } from "motion/react";
import Reveal from "../components/Reveal";
import Lightbox from "../components/Lightbox";
import { photos } from "../data/content";

export default function Photography() {
  const [index, setIndex] = useState<number | null>(null);
  const [choiceIndex, setChoiceIndex] = useState(0);
  const [choicePaused, setChoicePaused] = useState(false);
  const authorChoices = photos.filter((photo) => photo.featured);

  useEffect(() => {
    if (choicePaused || authorChoices.length < 2) return;
    const timer = window.setInterval(() => {
      setChoiceIndex((current) => (current + 1) % authorChoices.length);
    }, 5200);
    return () => window.clearInterval(timer);
  }, [authorChoices.length, choicePaused]);

  const moveChoice = (direction: number) => {
    setChoicePaused(true);
    setChoiceIndex((current) => {
      const next = (current + direction) % authorChoices.length;
      return next < 0 ? next + authorChoices.length : next;
    });
  };

  const renderPhoto = (photo: (typeof photos)[number], i: number, featured = false) => {
    const photoIndex = photos.indexOf(photo);
    return (
      <Reveal
        key={photo.full}
        delay={(i % 4) * 0.05}
        className="break-inside-avoid"
      >
        <motion.button
          onClick={() => setIndex(photoIndex)}
          whileHover={{ y: -4 }}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className={`group relative block w-full overflow-hidden rounded-[var(--radius-xl)] border bg-[var(--color-surface)] ${
            featured
              ? "border-[var(--color-accent)]/35 shadow-[0_16px_50px_rgba(0,0,0,0.12)]"
              : "border-[var(--color-edge)]"
          }`}
        >
          <img
            src={photo.thumb}
            alt={photo.caption ?? "Photograph"}
            loading={featured ? "eager" : "lazy"}
            className="w-full transform-gpu object-cover transition-transform duration-[1.1s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-[1.05]"
          />
          <div className="absolute inset-0 bg-black/0 transition-colors duration-500 group-hover:bg-black/15" />
          {photo.caption && (
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-2 p-4 text-left text-[12.5px] leading-snug text-white/0 opacity-0 transition-all duration-500 group-hover:translate-y-0 group-hover:text-white/90 group-hover:opacity-100"
              style={{
                background: "linear-gradient(to top, rgba(0,0,0,0.72), transparent)",
              }}
            >
              {photo.caption}
            </div>
          )}
        </motion.button>
      </Reveal>
    );
  };

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

      <div className="mt-14 columns-1 gap-2 sm:columns-2 lg:columns-3 xl:columns-4">
        {photos.map((photo, i) => (
          <div
            key={`frame-${photo.full}`}
            className="mb-2 break-inside-avoid"
          >
            {renderPhoto(photo, i, photo.featured)}
          </div>
        ))}
      </div>

      {authorChoices.length > 0 && (
        <Reveal>
          <section
            className="mt-32 border-t border-[var(--color-edge)] pt-16"
            aria-label="The edit"
            onMouseEnter={() => setChoicePaused(true)}
            onMouseLeave={() => setChoicePaused(false)}
          >
            <div className="mx-auto max-w-2xl text-center">
              <span className="eyebrow">The edit</span>
              <h2 className="mt-4 text-[clamp(1.8rem,4vw,3rem)] font-semibold tracking-[-0.03em]">
                Five frames that stayed with me.
              </h2>
              <p className="mx-auto mt-4 max-w-lg text-sm leading-relaxed text-[var(--color-muted)]">
                Light, distance, and the quiet moments between them.
              </p>
            </div>

            <div
              className="relative mx-auto mt-12 h-[410px] max-w-[1120px] overflow-hidden px-4 py-8 sm:h-[590px] sm:px-8 sm:py-12"
              style={{ perspective: "1200px" }}
              role="region"
              aria-roledescription="carousel"
              aria-label="The edit gallery"
            >
              {authorChoices.map((photo, photoIndex) => {
                const distance = photoIndex - choiceIndex;
                const wrappedDistance =
                  distance > authorChoices.length / 2
                    ? distance - authorChoices.length
                    : distance < -authorChoices.length / 2
                      ? distance + authorChoices.length
                      : distance;
                const absoluteDistance = Math.abs(wrappedDistance);
                const photoIndexInArchive = photos.indexOf(photo);

                return (
                  <motion.div
                    key={photo.full}
                    className="absolute left-1/2 top-1/2 aspect-[4/3] w-[min(88vw,620px)]"
                    style={{
                      marginLeft: "calc(min(88vw, 620px) / -2)",
                      marginTop: "calc(min(66vw, 465px) / -2)",
                      transformStyle: "preserve-3d",
                    }}
                    initial={false}
                    animate={{
                      x: wrappedDistance * 210,
                      rotateY: wrappedDistance * -22,
                      rotateZ: wrappedDistance * -2,
                      scale: 1 - absoluteDistance * 0.1,
                      opacity: absoluteDistance > 2 ? 0 : 1 - absoluteDistance * 0.18,
                      zIndex: 10 - absoluteDistance,
                    }}
                    transition={{ type: "spring", stiffness: 160, damping: 22 }}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setChoicePaused(true);
                        setChoiceIndex(photoIndex);
                        setIndex(photoIndexInArchive);
                      }}
                      className="relative block w-full overflow-hidden bg-transparent"
                      aria-label={`Open ${photo.caption ?? "selected photograph"}`}
                    >
                      <img
                        src={photo.thumb}
                        alt={photo.caption ?? "Selected photograph"}
                        className="aspect-[4/3] w-full object-contain bg-transparent"
                      />
                    </button>
                  </motion.div>
                );
              })}
            </div>

            <div className="mt-6 flex items-center justify-center gap-4">
              <button
                type="button"
                onClick={() => moveChoice(-1)}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--color-edge)] text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-ink)]"
                aria-label="Previous author's choice"
              >
                ←
              </button>
              <div className="flex items-center gap-2" aria-label="Choose photograph">
                {authorChoices.map((photo, photoIndex) => (
                  <button
                    key={photo.full}
                    type="button"
                    onClick={() => {
                      setChoicePaused(true);
                      setChoiceIndex(photoIndex);
                    }}
                    className={`h-1.5 rounded-full transition-all ${
                      photoIndex === choiceIndex
                        ? "w-8 bg-[var(--color-accent)]"
                        : "w-1.5 bg-[var(--color-edge)] hover:bg-[var(--color-muted)]"
                    }`}
                    aria-label={`Show choice ${photoIndex + 1}`}
                    aria-current={photoIndex === choiceIndex}
                  />
                ))}
              </div>
              <button
                type="button"
                onClick={() => moveChoice(1)}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--color-edge)] text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-ink)]"
                aria-label="Next author's choice"
              >
                →
              </button>
            </div>

            <p className="mx-auto mt-5 max-w-lg text-center text-sm leading-relaxed text-[var(--color-muted)]" aria-live="polite">
              {authorChoices[choiceIndex].caption ?? "A selected frame from the archive."}
            </p>
          </section>
        </Reveal>
      )}

      <Lightbox
        images={photos}
        index={index}
        onClose={() => setIndex(null)}
        setIndex={setIndex}
      />
    </div>
  );
}
