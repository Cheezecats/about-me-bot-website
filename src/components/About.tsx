import Reveal from "./Reveal";
import GenerativeCanvas from "./GenerativeCanvas";
import { bio } from "../data/content";

export default function About() {
  return (
    <section className="relative flex min-h-[520px] items-center overflow-hidden">
      {/* Ambient generative band */}
      <div className="absolute inset-x-0 top-0 h-full opacity-90">
        <GenerativeCanvas height={520} seed={11} particleCount={320} />
      </div>
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, var(--color-bg) 0%, transparent 22%, transparent 70%, var(--color-bg) 100%)",
        }}
      />

      <div className="relative mx-auto flex w-full max-w-[920px] -translate-y-4 flex-col items-center justify-center px-6 py-24 text-center sm:-translate-y-5 sm:py-28">
        <Reveal>
          <span className="eyebrow">About</span>
        </Reveal>

        <Reveal delay={0.05}>
          <h2 className="mx-auto mt-6 max-w-3xl text-[clamp(1.6rem,4.4vw,3rem)] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-fg)]">
            I capture the world through a lens, a camera, and a curious mind.
          </h2>
        </Reveal>

        <div className="mx-auto mt-8 flex max-w-2xl flex-col gap-5">
          {bio.paragraphs.map((para, i) => (
            <Reveal key={i} delay={0.1 + i * 0.08}>
              <p className="text-[16px] leading-relaxed text-[var(--color-muted)] sm:text-[17px]">
                {para}
              </p>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.3}>
          <dl className="mx-auto mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-[var(--color-edge)] pt-8">
            <div>
              <dt className="eyebrow">Age</dt>
              <dd className="mt-1 text-2xl font-bold tracking-tight text-[var(--color-fg)]">
                {bio.age}
              </dd>
            </div>
            <div>
              <dt className="eyebrow">Based</dt>
              <dd className="mt-1 text-2xl font-bold tracking-tight text-[var(--color-fg)]">
                Shanghai
              </dd>
            </div>
            <div>
              <dt className="eyebrow">Focus</dt>
              <dd className="mt-1 text-2xl font-bold tracking-tight text-[var(--color-fg)]">
                Motion
              </dd>
            </div>
          </dl>
        </Reveal>
      </div>
    </section>
  );
}
