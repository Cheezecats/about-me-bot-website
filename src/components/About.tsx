import { motion } from "motion/react";
import { bio } from "../data/content";

export default function About() {
  return (
    <section className="relative overflow-hidden border-y border-[var(--color-edge)] bg-[var(--color-surface)]">
      <div className="pointer-events-none absolute inset-0 opacity-80" style={{ background: "linear-gradient(120deg, transparent 10%, color-mix(in srgb, white 44%, transparent) 45%, transparent 58%), radial-gradient(circle at 86% 16%, color-mix(in srgb, var(--color-turquoise) 30%, transparent), transparent 24%)" }} />
      <div className="relative mx-auto grid max-w-[1180px] gap-12 px-6 py-24 sm:px-8 sm:py-32 lg:grid-cols-[0.82fr_1.18fr] lg:items-end">
        <motion.figure initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-15%" }} transition={{ duration: 0.9, ease: [0.25, 1, 0.5, 1] }} className="relative mx-auto w-full max-w-sm overflow-hidden rounded-[1.8rem] border-[8px] border-white/75 bg-[var(--color-bg)] shadow-[0_20px_52px_rgba(8,73,135,0.16)] lg:mx-0">
          <img src={bio.profileImage} alt="James Sui" loading="lazy" className="aspect-[4/5] w-full object-cover" />
          <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#163852]/84 to-transparent px-6 pb-6 pt-16"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/70">Based in</p><p className="mt-1 text-xl font-semibold text-white">{bio.location}</p></figcaption>
        </motion.figure>
        <div className="max-w-2xl lg:pb-4"><span className="cinema-kicker">Behind the work</span><h2 className="mt-5 text-[clamp(2.5rem,5.4vw,5.7rem)] font-semibold leading-[0.91] tracking-[-0.06em]">Curiosity gives the image somewhere to go.</h2>
          <div className="mt-9 space-y-5 text-[16px] leading-relaxed text-[var(--color-muted)] sm:text-[17px]">{bio.paragraphs.map((para) => <p key={para}>{para}</p>)}</div>
          <dl className="mt-10 grid grid-cols-3 border-t border-[var(--color-edge)] pt-6"><Stat label="Age" value={String(bio.age)} /><Stat label="Based" value="Shanghai" bordered /><Stat label="Focus" value="Motion" bordered /></dl>
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value, bordered = false }: { label: string; value: string; bordered?: boolean }) {
  return <div className={bordered ? "border-l border-[var(--color-edge)] pl-4 sm:pl-6" : ""}><dt className="cinema-kicker">{label}</dt><dd className="mt-2 text-2xl font-semibold">{value}</dd></div>;
}
