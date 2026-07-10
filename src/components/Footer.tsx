import { Link } from "react-router-dom";
import { bio, socials } from "../data/content";

function MailIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="14" rx="2.5" />
      <path d="M3.5 7.5l8.5 6 8.5-6" />
    </svg>
  );
}

function YouTubeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2.5" y="5.5" width="19" height="13" rx="4" />
      <path d="M10 9.2l5 2.8-5 2.8z" fill="currentColor" stroke="none" />
    </svg>
  );
}

const iconFor = (kind: string) =>
  kind === "email" ? <MailIcon /> : <YouTubeIcon />;

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-[var(--color-edge)] bg-[var(--color-bg)]">
      <div className="mx-auto max-w-[1180px] px-6 py-16 sm:px-8 sm:py-20">
        <div className="flex flex-col gap-12 md:flex-row md:items-end md:justify-between">
          <div className="max-w-md">
            <Link
              to="/"
              className="text-2xl font-bold tracking-tight text-[var(--color-fg)]"
            >
              James Sui
            </Link>
            <p className="mt-3 text-[15px] leading-relaxed text-[var(--color-muted)]">
              {bio.tagline} A 17-year-old photographer, athlete, and technologist
              based in {bio.location}.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            <span className="eyebrow">Get in touch</span>
            <a
              href={`mailto:${bio.email}`}
              className="text-lg font-medium tracking-tight text-[var(--color-fg)] underline-offset-4 transition hover:underline"
            >
              {bio.email}
            </a>
            <div className="flex items-center gap-2">
              {socials.map((s) => (
                <a
                  key={s.label}
                  href={s.href}
                  target={s.kind === "youtube" ? "_blank" : undefined}
                  rel={s.kind === "youtube" ? "noreferrer" : undefined}
                  aria-label={s.label}
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--color-edge)] text-[var(--color-muted)] transition-all duration-300 hover:-translate-y-0.5 hover:border-[var(--color-fg)] hover:text-[var(--color-fg)]"
                >
                  {iconFor(s.kind)}
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-14 flex flex-col items-start justify-between gap-3 border-t border-[var(--color-edge)] pt-6 text-[13px] text-[var(--color-muted)] sm:flex-row sm:items-center">
          <span>© {year} James Sui. All rights reserved.</span>
          <span>Designed & built with care. Powered by React.</span>
        </div>
      </div>
    </footer>
  );
}
