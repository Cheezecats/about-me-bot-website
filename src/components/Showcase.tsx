import { Link } from "react-router-dom";
import { motion } from "motion/react";
import Reveal from "./Reveal";
import { assetPath } from "../data/content";

const cards = [
  { to: "/photography", title: "Photography", subtitle: "Light, frame, and silence.", image: assetPath("thumbnails", "2-4jpn (17 - 37).jpg"), meta: "34 frames · Nikon Z8", style: "md:col-span-7 md:row-span-2" },
  { to: "/videos", title: "Videos", subtitle: "Film & motion.", image: "https://i.ytimg.com/vi/RUg2hiRTRVM/maxresdefault.jpg", meta: "3 films · 8K / 4K", style: "md:col-span-5" },
  { to: "/hobbies", title: "Hobbies", subtitle: "Sport, play, craft.", image: assetPath("thumbnails", "_T6A6134.jpg"), meta: "Ice hockey · Tennis · More", style: "md:col-span-3" },
  { to: "/essays", title: "Essays", subtitle: "Research & writing.", image: assetPath("pdf", "table_his2.png"), meta: "2 papers · ML & medical imaging", style: "md:col-span-2" },
];

export default function Showcase() {
  return (
    <section id="showcase" className="relative mx-auto max-w-[1320px] px-5 py-28 sm:px-8 sm:py-36">
      <Reveal>
        <div className="mb-14 grid gap-5 border-b border-[var(--color-edge)] pb-9 sm:grid-cols-[1fr_0.7fr] sm:items-end">
          <div><span className="cinema-kicker">Selected scenes</span><h2 className="mt-4 text-[clamp(2.8rem,6vw,6rem)] font-semibold leading-[0.87] tracking-[-0.065em]">Look<br className="sm:hidden" /> closer.</h2></div>
          <p className="max-w-sm text-[15px] leading-relaxed text-[var(--color-muted)] sm:justify-self-end sm:text-right">Four disciplines, held together by an eye for movement, texture, and place.</p>
        </div>
      </Reveal>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-12 md:grid-rows-[minmax(330px,48vh)_minmax(260px,34vh)]">
        {cards.map((card, index) => (
          <Reveal key={card.to} delay={index * 0.07} className={card.style}>
            <Link to={card.to} className="group block h-full">
              <motion.article whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300, damping: 24 }} className={`relative h-full min-h-[300px] overflow-hidden border border-[var(--color-edge)] bg-[var(--color-surface)] p-4 shadow-[0_16px_40px_rgba(8,73,135,0.1)] ${index === 0 ? "rounded-[2rem]" : "rounded-[1.35rem]"}`}>
                <div className={`relative h-full overflow-hidden ${index === 0 ? "rounded-[1.25rem]" : "rounded-xl"}`}>
                  <img src={card.image} alt={card.title} loading="lazy" className="absolute inset-0 h-full w-full object-cover transition-transform duration-[1.1s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-[1.055]" />
                  <div className="absolute inset-x-0 bottom-0 h-[58%] bg-gradient-to-t from-[#0c426e]/85 via-[#0c426e]/26 to-transparent" />
                  <div className="absolute inset-0 flex flex-col justify-between p-5 sm:p-6">
                    <span className="w-fit rounded-lg bg-white/86 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#163852] backdrop-blur-sm">{card.meta}</span>
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/75">{card.subtitle}</p>
                      <div className="mt-2 flex items-end justify-between gap-4"><h3 className="text-[clamp(2rem,4vw,4.7rem)] font-semibold leading-[0.9] tracking-[-0.055em] text-white">{card.title}</h3><span className="mb-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-turquoise)] text-[#163852] transition-transform group-hover:translate-x-1 group-hover:-translate-y-1"><Arrow /></span></div>
                    </div>
                  </div>
                </div>
              </motion.article>
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function Arrow() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
}
