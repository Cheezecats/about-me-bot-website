import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      <span className="eyebrow">404</span>
      <h1 className="mt-4 text-[clamp(3rem,12vw,8rem)] font-extrabold leading-none tracking-[-0.04em]">
        Lost the frame.
      </h1>
      <p className="mt-5 max-w-md text-[16px] leading-relaxed text-[var(--color-muted)]">
        The page you're looking for doesn't exist — or has moved. Let's get you
        back to a clear view.
      </p>
      <Link
        to="/"
        className="mt-9 inline-flex items-center gap-2 rounded-full bg-[var(--color-fg)] px-7 py-3 text-[14px] font-semibold text-[var(--color-bg)] transition-all duration-300 hover:gap-3"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M11 18l-6-6 6-6" />
        </svg>
        Back home
      </Link>
    </div>
  );
}
