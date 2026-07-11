import { useEffect, useRef } from "react";
import p5 from "p5";
import { useTheme } from "./ThemeProvider";

type Palette = { bg: string; fg: string };

const PALETTES: Record<"light" | "dark", Palette> = {
  light: { bg: "#f5f5f7", fg: "#1d1d1f" },
  dark: { bg: "#0a0a0c", fg: "#e8e8ec" },
};

type Props = {
  className?: string;
  height?: number;
  seed?: number;
  particleCount?: number;
};

export default function GenerativeCanvas({
  className,
  height = 360,
  seed = 7,
  particleCount = 280,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<p5 | null>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    const palette = PALETTES[theme];

    const sketch = (p: p5) => {
      let w = node.clientWidth;
      let h = node.clientHeight;
      let particles: { x: number; y: number; px: number; py: number }[] = [];
      let t = 0;

      const noiseScale = 0.0022;

      p.setup = () => {
        p.createCanvas(w, h);
        p.randomSeed(seed);
        p.noiseSeed(seed);
        p.background(palette.bg);
        p.strokeCap(p.ROUND);
        resetParticles();
      };

      const resetParticles = () => {
        particles = [];
        for (let i = 0; i < particleCount; i++) {
          const x = p.random(w);
          const y = p.random(h);
          particles.push({ x, y, px: x, py: y });
        }
      };

      p.windowResized = () => {
        w = node.clientWidth;
        h = node.clientHeight;
        p.resizeCanvas(w, h);
        p.background(palette.bg);
        resetParticles();
      };

      p.draw = () => {
        // fade existing trails toward the background
        p.noStroke();
        const bg = p.color(palette.bg);
        bg.setAlpha(prefersReduced ? 255 : 26);
        p.fill(bg);
        p.rect(0, 0, w, h);

        const fg = p.color(palette.fg);
        fg.setAlpha(prefersReduced ? 60 : 38);
        p.stroke(fg);
        p.strokeWeight(0.9);

        for (const pt of particles) {
          const angle =
            p.noise(pt.x * noiseScale, pt.y * noiseScale, t) * p.TWO_PI * 3;
          const step = 1.1;
          pt.px = pt.x;
          pt.py = pt.y;
          pt.x += p.cos(angle) * step;
          pt.y += p.sin(angle) * step;

          if (pt.x < 0 || pt.x > w || pt.y < 0 || pt.y > h) {
            pt.x = p.random(w);
            pt.y = p.random(h);
            pt.px = pt.x;
            pt.py = pt.y;
            continue;
          }

          p.line(pt.px, pt.py, pt.x, pt.y);
        }

        t += 0.0016;
      };

      if (prefersReduced) {
        // render a single static composition
        p.noLoop();
      }
    };

    const instance = new p5(sketch, node);
    instanceRef.current = instance;

    // Pause when offscreen to save CPU/battery
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (prefersReduced) return;
          if (e.isIntersecting) instance.loop();
          else instance.noLoop();
        }
      },
      { threshold: 0.05 }
    );
    io.observe(node);

    return () => {
      io.disconnect();
      instance.remove();
      instanceRef.current = null;
      // p5 leaves a canvas node; clear it defensively
      node.textContent = "";
    };
  }, [theme, seed, particleCount, height]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        width: "100%",
        height,
        background: PALETTES[theme].bg,
      }}
      aria-hidden="true"
    />
  );
}
