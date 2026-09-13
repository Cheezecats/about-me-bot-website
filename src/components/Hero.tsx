import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { useRef } from "react";
import { Link } from "react-router-dom";
import { assetPath, bio, heroCaption, heroImage } from "../data/content";

const ease = [0.25, 1, 0.5, 1] as const;

export default function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start start", "end end"] });
  const imageY = useTransform(scrollYProgress, [0, 1], ["0%", "9%"]);
  const imageScale = useTransform(scrollYProgress, [0, 0.8, 1], [1, 1.03, 1.08]);
  const copyY = useTransform(scrollYProgress, [0, 1], ["0%", "-16%"]);
  const copyOpacity = useTransform(scrollYProgress, [0, 0.74, 1], [1, 1, 0]);
  const smallPhotoY = useTransform(scrollYProgress, [0, 1], ["0%", "-18%"]);

  return (
    <section ref={sectionRef} className="relative h-[154svh] min-h-[850px]">
      <div className="sticky top-0 min-h-[680px] overflow-hidden bg-[var(--color-bg)]">
        <div className="absolute inset-0 opacity-80" style={{ background: "radial-gradient(circle at 84% 16%, color-mix(in srgb, var(--color-turquoise) 38%, transparent), transparent 23%), linear-gradient(132deg, var(--color-bg) 0%, color-mix(in srgb, var(--color-sky) 13%, var(--color-bg)) 60%, color-mix(in srgb, var(--color-coral) 14%, var(--color-bg)) 100%)" }} />
        <div className="relative mx-auto grid min-h-[100svh] max-w-[1380px] items-center gap-10 px-5 pb-16 pt-28 sm:px-8 md:grid-cols-[0.92fr_1.08fr] md:gap-14 md:pt-24 lg:px-12">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease }} style={{ y: reduceMotion ? "0%" : copyY, opacity: reduceMotion ? 1 : copyOpacity }} className="relative z-10 max-w-3xl">
            <p className="cinema-kicker mb-6">Shanghai · China</p>
            <h1 className="text-[clamp(4rem,10vw,9.5rem)] font-extrabold leading-[0.76] tracking-[-0.085em] text-[var(--color-sky)]">James<br /><span className="text-[var(--color-fg)]">Sui.</span></h1>
            <p className="mt-8 max-w-md text-[clamp(1.35rem,2.4vw,2.15rem)] font-semibold leading-[1.04] tracking-[-0.04em] text-[var(--color-fg)]">{bio.tagline}</p>
            <p className="mt-5 max-w-md text-[15px] leading-relaxed text-[var(--color-muted)] sm:text-[17px]">A 17-year-old photographer, filmmaker, and technologist exploring where light, motion, and ideas meet.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/photography" className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-sky)] px-5 py-3 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(8,124,250,0.26)] transition hover:-translate-y-0.5 hover:bg-[color-mix(in_srgb,var(--color-sky)_85%,black)]">Enter the archive <Arrow /></Link>
              <a href={`mailto:${bio.email}`} className="inline-flex items-center rounded-xl border border-[var(--color-edge)] bg-[color-mix(in_srgb,var(--color-bg)_70%,transparent)] px-5 py-3 text-[13px] font-semibold text-[var(--color-fg)] transition hover:border-[var(--color-sky)] hover:text-[var(--color-sky)]">Get in touch</a>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.96, y: 30 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={{ duration: 1.1, delay: 0.12, ease }} className="relative mx-auto w-full max-w-[720px] self-end md:self-center">
            <motion.figure style={{ y: reduceMotion ? "0%" : imageY, scale: reduceMotion ? 1 : imageScale }} className="relative ml-auto aspect-[1.1/1] w-[92%] overflow-hidden rounded-[2rem] border-[10px] border-white/75 bg-[var(--color-surface)] shadow-[0_28px_72px_rgba(8,73,135,0.24)]">
              <img src={heroImage} alt={heroCaption} fetchPriority="high" className="h-full w-full object-cover" />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-[#163852]/58 to-transparent" />
              <figcaption className="absolute inset-x-5 bottom-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/85">{heroCaption}</figcaption>
            </motion.figure>
            <motion.figure style={{ y: reduceMotion ? "0%" : smallPhotoY }} className="absolute -bottom-12 left-0 w-[39%] overflow-hidden rounded-[1.35rem] border-[7px] border-[var(--color-bg)] bg-[var(--color-surface)] shadow-[0_18px_46px_rgba(8,73,135,0.2)] sm:-left-5 sm:w-[35%]">
              <img src={assetPath("thumbnails", "DSC_0480.jpg")} alt="Athens, Greece" loading="eager" className="aspect-[4/5] w-full object-cover" />
            </motion.figure>
            <span className="absolute -right-1 top-[12%] h-14 w-14 rounded-full border-[6px] border-[var(--color-bg)] bg-[var(--color-coral)] shadow-[0_8px_25px_rgba(245,141,145,0.32)] sm:right-4 sm:h-20 sm:w-20" aria-hidden="true" />
          </motion.div>
        </div>
        <a href="#showcase" className="absolute bottom-7 left-1/2 z-10 -translate-x-1/2 text-[10px] font-semibold uppercase tracking-[0.27em] text-[var(--color-muted)] transition hover:text-[var(--color-sky)]">Scroll to explore</a>
      </div>
    </section>
  );
}

function Arrow() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
}
