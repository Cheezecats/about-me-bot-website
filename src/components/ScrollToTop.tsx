import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/** Wait for lazy routes and exit transitions before scrolling/focusing a target. */
export default function ScrollToTop() {
  const { pathname, hash, key, state } = useLocation();
  useEffect(() => {
    let frame = 0;
    let disposed = false;
    const main = document.querySelector('main');
    if (!main) return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const reveal = () => {
      if (disposed) return;
      const page = [...main.querySelectorAll<HTMLElement>('[data-page-path]')].find(el => el.dataset.pagePath === pathname);
      if (!page) return;
      let target: HTMLElement | null = null;
      if (hash) {
        let id: string;
        try { id = decodeURIComponent(hash.slice(1)); } catch { id = ''; }
        target = [...page.querySelectorAll<HTMLElement>('[id]')].find(el => el.id === id) ?? null;
      }
      target ??= page.querySelector<HTMLElement>('h1');
      if (!target) return;
      observer.disconnect();
      clearTimeout(timeout);
      frame = requestAnimationFrame(() => {
        if (disposed) return;
        if (hash && target.id) target.scrollIntoView({ block: 'start', behavior: reduced ? 'instant' : 'smooth' });
        else window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
        if (state?.chatNavigation || hash) {
          const heading = target.matches('h1,h2,h3') ? target : target.querySelector<HTMLElement>('h1,h2,h3') ?? target;
          if (!heading.hasAttribute('tabindex')) heading.setAttribute('tabindex', '-1');
          heading.focus({ preventScroll: true });
        }
      });
    };
    const observer = new MutationObserver(reveal);
    observer.observe(main, { childList: true, subtree: true });
    const timeout = window.setTimeout(() => observer.disconnect(), 10000);
    reveal();
    return () => { disposed = true; observer.disconnect(); clearTimeout(timeout); cancelAnimationFrame(frame); };
  }, [pathname, hash, key, state]);
  return null;
}
