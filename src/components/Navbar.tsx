import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { navLinks } from "../data/content";
import { useTheme } from "./ThemeProvider";

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2v2.2M12 19.8V22M2 12h2.2M19.8 12H22M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M19.4 4.6l-1.6 1.6M6.2 17.8l-1.6 1.6" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />
    </svg>
  );
}

export default function Navbar() {
  const { theme, toggle } = useTheme();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <motion.header
        initial={{ y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.7, ease: [0.25, 1, 0.5, 1] }}
        className="fixed inset-x-0 top-0 z-[100]"
      >
        <div
          className={`mx-auto flex h-12 max-w-[1180px] items-center justify-between px-5 transition-all duration-500 sm:px-8 ${
            scrolled
              ? "glass mt-2 h-11 rounded-full sm:mt-3"
              : "border-b border-transparent"
          }`}
          style={
            scrolled
              ? undefined
              : { background: "transparent", backdropFilter: "none" }
          }
        >
          <Link
            to="/"
            className="group flex items-center gap-2 text-[15px] font-semibold tracking-tight"
          >
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--color-fg)] transition-transform duration-500 group-hover:scale-125" />
            James Sui
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {navLinks.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === "/"}
                className={({ isActive }) =>
                  `relative rounded-full px-3.5 py-1.5 text-[13.5px] font-medium transition-colors duration-300 ${
                    isActive
                      ? "text-[var(--color-fg)]"
                      : "text-[var(--color-muted)] hover:text-[var(--color-fg)]"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {l.label}
                    {isActive && (
                      <motion.span
                        layoutId="nav-active"
                        className="absolute inset-0 -z-10 rounded-full bg-[var(--color-surface)]"
                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-1.5">
            <button
              onClick={toggle}
              aria-label="Toggle theme"
              className="flex h-9 w-9 items-center justify-center rounded-full text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-fg)]"
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            </button>

            <button
              onClick={() => setOpen((o) => !o)}
              aria-label="Menu"
              aria-expanded={open}
              className="flex h-9 w-9 items-center justify-center rounded-full text-[var(--color-fg)] transition-colors hover:bg-[var(--color-surface)] md:hidden"
            >
              <div className="flex flex-col items-end gap-[5px]">
                <span
                  className={`h-[1.6px] bg-current transition-all duration-300 ${
                    open ? "w-5 translate-y-[6.6px] rotate-45" : "w-5"
                  }`}
                />
                <span
                  className={`h-[1.6px] bg-current transition-all duration-300 ${
                    open ? "opacity-0" : "w-3.5"
                  }`}
                />
                <span
                  className={`h-[1.6px] bg-current transition-all duration-300 ${
                    open ? "w-5 -translate-y-[6.6px] -rotate-45" : "w-4"
                  }`}
                />
              </div>
            </button>
          </div>
        </div>
      </motion.header>

      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-[95] flex flex-col bg-[var(--color-bg)]/95 backdrop-blur-2xl md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="flex flex-1 flex-col justify-center px-8">
              {navLinks.map((l, i) => (
                <motion.div
                  key={l.to}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.06 * i + 0.1, duration: 0.5, ease: [0.25, 1, 0.5, 1] }}
                >
                  <NavLink
                    to={l.to}
                    end={l.to === "/"}
                    className={({ isActive }) =>
                      `block py-4 text-4xl font-bold tracking-tight transition-colors ${
                        isActive
                          ? "text-[var(--color-fg)]"
                          : "text-[var(--color-muted)]"
                      }`
                    }
                  >
                    {l.label}
                  </NavLink>
                </motion.div>
              ))}
            </div>
            <div className="px-8 pb-10 text-sm text-[var(--color-muted)]">
              James Sui — {new Date().getFullYear()}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
