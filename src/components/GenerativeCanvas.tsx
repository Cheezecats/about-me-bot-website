import { useEffect, useRef } from "react";
import type p5 from "p5";
import { useReducedMotion } from "motion/react";
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
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const prefersReduced = reducedMotion ?? false;
    let disposed = false;
    let visible = false;
    let starting = false;
    let instance: p5 | null = null;
    const palette = PALETTES[theme];

    const sketch = (p: p5) => {
      let w = node.clientWidth;
      let h = node.clientHeight;
      let particles: { x: number; y: number; px: number; py: number }[] = [];
      let t = 0;

      const noiseScale = 0.0022;

      p.setup = () => {
        p.pixelDensity(Math.min(window.devicePixelRatio || 1, 2));
        p.frameRate(30);
        p.createCanvas(w, h);
        p.randomSeed(seed);
        p.noiseSeed(seed);
        p.background(palette.bg);
        p.strokeCap(p.ROUND);
        resetParticles();
        if (prefersReduced || !visible || document.hidden) p.noLoop();
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

    const syncPlayback = () => {
      if (!instance) return;
      if (visible && !document.hidden && !prefersReduced) instance.loop();
      else instance.noLoop();
    };
    // Load the existing artwork only when its section approaches the viewport.
    // The home page and JamChat no longer wait on the p5 bundle.
    const start = async () => {
      if (starting || disposed) return;
      starting = true;
      try {
        const { default: P5 } = await import("p5");
        if (disposed) return;
        instance = new P5(sketch, node);
        instanceRef.current = instance;
        syncPlayback();
      } catch {
        // Decorative artwork is optional; preserve the section's content.
        starting = false;
      }
    };
    const io = new IntersectionObserver(entries => {
      visible = entries.some(entry => entry.isIntersecting);
      if (visible) void start();
      syncPlayback();
    }, { rootMargin: "160px", threshold: 0 });
    io.observe(node);
    document.addEventListener("visibilitychange", syncPlayback);

    return () => {
      disposed = true;
      io.disconnect();
      document.removeEventListener("visibilitychange", syncPlayback);
      instance?.remove();
      instanceRef.current = null;
      // p5 leaves a canvas node; clear it defensively
      node.textContent = "";
    };
  }, [theme, seed, particleCount, height, reducedMotion]);

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
