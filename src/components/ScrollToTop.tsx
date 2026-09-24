import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function ScrollToTop() {
  const { pathname, hash, key } = useLocation();
  useEffect(() => {
    if (!hash) {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      return;
    }
    let id: string;
    try { id = decodeURIComponent(hash.slice(1)); } catch { return; }
    let focusTimer = 0;
    const arrive = () => {
      const target = document.getElementById(id);
      if (!target) return false;
      target.scrollIntoView({ behavior: "auto", block: "start" });
      // The chat panel exits after navigation; focus once that exit has finished.
      focusTimer = window.setTimeout(() => {
        document.getElementById(id)?.focus({ preventScroll: true });
      }, 500);
      return true;
    };
    const cancelFocus = () => window.clearTimeout(focusTimer);
    if (arrive()) return cancelFocus;
    const observer = new MutationObserver(() => { if (arrive()) observer.disconnect(); });
    observer.observe(document.body, { childList: true, subtree: true });
    const timeout = window.setTimeout(() => observer.disconnect(), 15000);
    return () => { observer.disconnect(); window.clearTimeout(timeout); cancelFocus(); };
  }, [pathname, hash, key]);
  return null;
}
