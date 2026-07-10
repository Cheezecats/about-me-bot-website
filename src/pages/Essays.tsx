import Reveal from "../components/Reveal";
import { essays } from "../data/content";

export default function Essays() {
  return (
    <div className="mx-auto max-w-[860px] px-6 pb-28 pt-28 sm:px-8 sm:pt-36">
      <Reveal>
        <span className="eyebrow">Essays</span>
        <h1 className="mt-4 text-[clamp(2.2rem,6vw,4rem)] font-bold leading-[1.02] tracking-[-0.03em]">
          Research & writing.
        </h1>
        <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-[var(--color-muted)]">
          Academic work on machine learning and medical imaging — with figures
          and full PDFs.
        </p>
      </Reveal>

      <div className="mt-16 flex flex-col gap-16">
        {essays.map((essay, i) => (
          <Reveal key={essay.title} delay={i * 0.05}>
            <article className="border-t border-[var(--color-edge)] pt-10">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <h2 className="max-w-2xl text-2xl font-bold leading-tight tracking-tight sm:text-3xl">
                  <a
                    href={essay.pdf}
                    target="_blank"
                    rel="noreferrer"
                    className="transition-colors hover:text-[var(--color-muted)]"
                  >
                    {essay.title}
                  </a>
                </h2>
                <a
                  href={essay.pdf}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex shrink-0 items-center gap-2 rounded-full border border-[var(--color-edge)] px-5 py-2.5 text-[13px] font-medium transition-all duration-300 hover:border-[var(--color-fg)]"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
                  </svg>
                  PDF
                </a>
              </div>

              <p className="mt-5 text-[16px] leading-[1.75] text-[var(--color-muted)]">
                {essay.abstract}
              </p>

              <div className="mt-8 flex flex-col items-center gap-6">
                {essay.figures.map((fig) => (
                  <figure key={fig.src} className="w-full text-center">
                    <img
                      src={fig.src}
                      alt={fig.alt}
                      loading="lazy"
                      style={{ width: fig.width, maxWidth: "100%" }}
                      className="mx-auto block rounded-[var(--radius-xl)] border border-[var(--color-edge)]"
                    />
                    <figcaption className="mt-3 text-[12.5px] text-[var(--color-muted)]">
                      {fig.alt}
                    </figcaption>
                  </figure>
                ))}
              </div>
            </article>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
