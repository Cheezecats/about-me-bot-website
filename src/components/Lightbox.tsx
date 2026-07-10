import { useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "motion/react";

type LightboxImage = { full: string; caption?: string };

type LightboxProps = {
  images: LightboxImage[];
  index: number | null;
  onClose: () => void;
  setIndex: (i: number | null) => void;
};

export default function Lightbox({
  images,
  index,
  onClose,
  setIndex,
}: LightboxProps) {
  const isOpen = index !== null;

  const go = useCallback(
    (dir: number) => {
      if (index === null) return;
      const n = images.length;
      const next = (index + dir + n) % n;
      setIndex(next);
    },
    [index, images.length, setIndex]
  );

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [isOpen, onClose, go]);

  const current = index !== null ? images[index] : null;

  return (
    <AnimatePresence>
      {isOpen && current && (
        <motion.div
          className="fixed inset-0 z-[120] flex items-center justify-center p-4 sm:p-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.25, 1, 0.5, 1] }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label="Image viewer"
        >
          <div className="absolute inset-0 bg-black/85 backdrop-blur-xl" />

          <button
            onClick={onClose}
            aria-label="Close"
            className="absolute right-4 top-4 z-10 flex h-11 w-11 items-center justify-center rounded-full text-white/90 transition hover:bg-white/10 hover:text-white"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>

          {images.length > 1 && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  go(-1);
                }}
                aria-label="Previous"
                className="absolute left-3 sm:left-6 z-10 flex h-12 w-12 items-center justify-center rounded-full text-white/80 transition hover:bg-white/10 hover:text-white"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  go(1);
                }}
                aria-label="Next"
                className="absolute right-3 sm:right-6 z-10 flex h-12 w-12 items-center justify-center rounded-full text-white/80 transition hover:bg-white/10 hover:text-white"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </button>
            </>
          )}

          <motion.figure
            key={current.full}
            className="relative z-[5] flex max-h-[88vh] max-w-[94vw] flex-col items-center"
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={current.full}
              alt={current.caption ?? "Photograph"}
              className="max-h-[82vh] max-w-[94vw] rounded-xl object-contain"
              style={{ boxShadow: "0 0 80px rgba(0,0,0,0.6)" }}
            />
            {current.caption && (
              <figcaption className="mt-5 max-w-xl text-center text-sm leading-relaxed text-white/70">
                {current.caption}
              </figcaption>
            )}
          </motion.figure>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
