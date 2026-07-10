import { Link } from "react-router-dom";
import { motion } from "motion/react";
import Reveal from "./Reveal";

type Card = {
  to: string;
  title: string;
  subtitle: string;
  image: string;
  meta: string;
  className: string;
};

const cards: Card[] = [
  {
    to: "/photography",
    title: "Photography",
    subtitle: "Light, frame, and silence.",
    image: "/assets/thumbnails/2-4jpn%20(17%20-%2037).jpg",
    meta: "34 frames · Nikon Z8",
    className: "md:col-span-2 md:row-span-2",
  },
  {
    to: "/videos",
    title: "Videos",
    subtitle: "Film & motion.",
    image: "https://i.ytimg.com/vi/RUg2hiRTRVM/maxresdefault.jpg",
    meta: "3 films · 8K / 4K",
    className: "",
  },
  {
    to: "/hobbies",
    title: "Hobbies",
    subtitle: "Sport, play, craft.",
    image: "/assets/thumbnails/_T6A6134.jpg",
    meta: "Ice hockey · Tennis · More",
    className: "",
  },
  {
    to: "/essays",
    title: "Essays",
    subtitle: "Research & writing.",
    image: "/assets/pdf/table_his2.png",
    meta: "2 papers · ML & medical imaging",
    className: "md:col-span-2",
  },
];

export default function Showcase() {
  return (
    <section id="showcase" className="mx-auto max-w-[1180px] px-6 py-24 sm:px-8 sm:py-32">
      <Reveal>
        <div className="mb-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <span className="eyebrow">The Showcase</span>
            <h2 className="mt-3 text-[clamp(1.8rem,5vw,3.2rem)] font-bold leading-[1.02] tracking-[-0.02em]">
              Explore the work.
            </h2>
          </div>
          <p className="max-w-sm text-[15px] leading-relaxed text-[var(--color-muted)]">
            Four disciplines, one perspective. Each tile opens a deeper look.
          </p>
        </div>
      </Reveal>

      <div className="grid auto-rows-[220px] grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
        {cards.map((card, i) => (
          <Reveal key={card.to} delay={i * 0.08} className={card.className}>
            <Link to={card.to} className="group block h-full w-full">
              <motion.div
                whileHover={{ y: -6 }}
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
                className="relative h-full w-full overflow-hidden rounded-[var(--radius-2xl)] border border-[var(--color-edge)] bg-[var(--color-surface)]"
              >
                <img
                  src={card.image}
                  alt={card.title}
                  loading="lazy"
                  className="absolute inset-0 h-full w-full object-cover transition-transform duration-[1.2s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-[1.06]"
                />
                <div
                  className="absolute inset-0"
                  style={{
                    background:
                      "linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.15) 45%, rgba(0,0,0,0.78) 100%)",
                  }}
                />
                <div className="absolute inset-0 flex flex-col justify-end p-6">
                  <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/55">
                    {card.meta}
                  </span>
                  <h3 className="mt-1.5 text-2xl font-bold tracking-tight text-white">
                    {card.title}
                  </h3>
                  <p className="mt-0.5 text-[14px] text-white/70">
                    {card.subtitle}
                  </p>
                  <span className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-medium text-white/0 transition-all duration-300 group-hover:text-white/90">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-white/15 backdrop-blur-md transition-transform duration-300 group-hover:translate-x-0.5">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M5 12h14M13 6l6 6-6 6" />
                      </svg>
                    </span>
                  </span>
                </div>
              </motion.div>
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
