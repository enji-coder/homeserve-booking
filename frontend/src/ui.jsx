import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { api } from "./api";
import { useAuth } from "./auth";

const ICONS = {
  bolt: "M13 2 4 14h7l-1 8 9-12h-7l1-8z",
  drop: "M12 3s6 7 6 11a6 6 0 1 1-12 0c0-4 6-11 6-11z",
  snow: "M12 2v20M4.9 6.5l14.2 11M19.1 6.5 4.9 17.5M8 4.5 12 8l4-3.5M8 19.5 12 16l4 3.5",
  spark: "M12 3l1.6 5.2L19 10l-5.4 1.8L12 17l-1.6-5.2L5 10l5.4-1.8L12 3z",
  brush: "M4 20c2-1 3-3 3-5 3 1 6-2 7-5l5-6-3 1-6 6c-2 2-5 3-6 9z",
  hammer: "M14 4l6 6-3 1-4-4-7 8 2 2 8-7 1 3-6 6",
  washer: "M6 3h12v18H6zM8 7h8M12 17a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z",
  bug: "M8 9a4 4 0 0 1 8 0v2a4 4 0 0 1-8 0V9zM4 11h4M16 11h4M5 16l3-1M19 16l-3-1M12 15v5",
};

export function Icon({ name = "bolt", className = "h-6 w-6" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d={ICONS[name] || ICONS.bolt} />
    </svg>
  );
}

export const btn = "inline-flex items-center justify-center rounded-full bg-forest px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-ink disabled:opacity-50";
export const btnClay = "inline-flex items-center justify-center rounded-full bg-clay px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-ink disabled:opacity-50";
export const btnGhost = "inline-flex items-center justify-center rounded-full border border-line bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-forest disabled:opacity-50";
export const field = "w-full rounded-2xl border border-line bg-white px-3.5 py-2.5 text-sm outline-none ring-forest/15 placeholder:text-moss/50 focus:border-forest focus:ring-4";

export function Logo() {
  return (
    <Link to="/" className="flex min-w-0 items-center gap-2 font-display text-xl tracking-tight sm:text-2xl">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-forest text-cream">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor"><path d="M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-8.5z" /></svg>
      </span>
      HomeServe
    </Link>
  );
}

export function TopNav() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  const links = (
    <>
      <a href="/#services" onClick={close}>Services</a>
      <a href="/#how" onClick={close}>How it works</a>
      <Link to="/services" onClick={close}>Book</Link>
      <a href="/docs" onClick={close}>Swagger</a>
    </>
  );
  const actions = user ? (
    <Link to="/app" className={btn} onClick={close}>Open workspace</Link>
  ) : (
    <>
      <Link to="/login" className={btnGhost} onClick={close}>Log in</Link>
      <Link to="/register" className={btnClay} onClick={close}>Get started</Link>
    </>
  );
  return (
    <header className="sticky top-0 z-30 border-b border-line/80 bg-cream/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-5">
        <Logo />
        <nav className="hidden items-center gap-6 text-sm font-medium text-moss lg:flex">{links}</nav>
        <div className="flex shrink-0 items-center gap-2">
          <div className="hidden items-center gap-2 sm:flex">{actions}</div>
          <button type="button" className={`${btnGhost} px-3 lg:hidden`} aria-expanded={open} aria-label="Open menu" onClick={() => setOpen((value) => !value)}>
            {open ? "Close" : "Menu"}
          </button>
        </div>
      </div>
      {open ? (
        <div className="border-t border-line px-4 py-3 lg:hidden">
          <nav className="grid gap-3 text-sm font-medium text-moss">{links}</nav>
          <div className="mt-3 grid gap-2 sm:hidden">{actions}</div>
        </div>
      ) : null}
    </header>
  );
}

export function StatusPill({ status }) {
  const tone = {
    Pending: "bg-amber-100 text-amber-900",
    Confirmed: "bg-leaf text-forest",
    "Provider Assigned": "bg-emerald-100 text-emerald-900",
    "In Progress": "bg-orange-100 text-clay",
    Completed: "bg-forest text-cream",
    Cancelled: "bg-stone-200 text-stone-700",
    Rejected: "bg-red-100 text-red-800",
    Paid: "bg-forest text-cream",
    Partial: "bg-amber-100 text-amber-900",
    Failed: "bg-red-100 text-red-800",
    Refunded: "bg-stone-200 text-stone-700",
    Open: "bg-amber-100 text-amber-900",
    "In Review": "bg-orange-100 text-clay",
    Resolved: "bg-leaf text-forest",
    approved: "bg-leaf text-forest",
    pending: "bg-amber-100 text-amber-900",
    rejected: "bg-red-100 text-red-800",
    active: "bg-leaf text-forest",
    suspended: "bg-stone-200 text-stone-700",
    accrued: "bg-leaf text-forest",
    refunded: "bg-stone-200 text-stone-700",
  }[status] || "bg-white text-ink";
  return <span className={`inline-flex shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{status}</span>;
}

export function Stat({ label, value, hint }) {
  return (
    <div className="rounded-3xl border border-line bg-paper p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-moss">{label}</p>
      <p className="mt-2 break-words font-display text-2xl sm:text-3xl">{value}</p>
      {hint ? <p className="mt-1 text-sm text-moss">{hint}</p> : null}
    </div>
  );
}

export function ErrorNote({ error }) {
  if (!error) return null;
  return <p className="rounded-2xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
}

export function Empty({ title, body, action }) {
  return (
    <div className="rounded-3xl border border-dashed border-line bg-paper px-6 py-10 text-center">
      <h3 className="font-display text-2xl">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-moss">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function Bars({ data, y = "revenue" }) {
  const max = Math.max(...data.map((item) => Number(item[y]) || 0), 1);
  return (
    <div className="flex h-40 items-end gap-2">
      {data.map((item) => (
        <div key={item.month} className="flex h-full flex-1 flex-col justify-end gap-2">
          <div className="rounded-t-xl bg-forest" style={{ height: `${Math.max((Number(item[y]) / max) * 100, 6)}%` }} />
          <span className="truncate text-center text-[10px] font-medium text-moss">{item.month}</span>
        </div>
      ))}
    </div>
  );
}

const FLOW = ["Pending", "Confirmed", "Provider Assigned", "In Progress", "Completed"];

export function Timeline({ status }) {
  if (status === "Cancelled" || status === "Rejected") {
    return <StatusPill status={status} />;
  }
  const index = FLOW.indexOf(status);
  return (
    <ol className="grid gap-2 sm:grid-cols-5">
      {FLOW.map((step, stepIndex) => (
        <li key={step} className={`rounded-2xl px-3 py-2 text-xs font-semibold ${stepIndex <= index ? "bg-forest text-cream" : "bg-white text-moss"}`}>
          {stepIndex + 1}. {step}
        </li>
      ))}
    </ol>
  );
}

export function Shell({ title, tabs, tab, setTab, children }) {
  const { user, logout } = useAuth();
  const [notes, setNotes] = useState([]);
  const [openNotes, setOpenNotes] = useState(false);

  async function loadNotes() {
    try {
      setNotes(await api.get("/api/notifications"));
    } catch {
      setNotes([]);
    }
  }

  useEffect(() => {
    loadNotes();
  }, [tab]);

  const unread = notes.filter((note) => !note.is_read).length;

  async function openBell() {
    setOpenNotes((value) => !value);
    if (!openNotes && unread) {
      await api.post("/api/notifications/read");
      loadNotes();
    }
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="hidden bg-ink text-cream lg:flex lg:min-h-screen lg:flex-col lg:px-4 lg:py-5">
        <Logo />
        <p className="mt-6 px-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/40">{user?.role}</p>
        <nav className="mt-3 flex flex-1 flex-col gap-1">
          {tabs.map((item) => (
            <button key={item.id} onClick={() => setTab(item.id)} className={`rounded-2xl px-3 py-2.5 text-left text-sm ${tab === item.id ? "bg-white/10 font-semibold" : "text-white/70 hover:bg-white/5"}`}>
              {item.label}
            </button>
          ))}
        </nav>
        <button onClick={logout} className="rounded-2xl px-3 py-2 text-left text-sm text-white/70 hover:bg-white/5">Log out</button>
      </aside>
      <div>
        <header className="sticky top-0 z-20 border-b border-line bg-cream/90 px-4 py-3 backdrop-blur lg:px-8">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-[0.16em] text-moss lg:hidden">{user?.role}</p>
              <h1 className="truncate font-display text-xl sm:text-2xl lg:text-3xl">{title}</h1>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button onClick={openBell} className="relative grid h-10 w-10 place-items-center rounded-full border border-line bg-white">
                <span className="text-lg">✉</span>
                {unread > 0 ? <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-clay px-1 text-[10px] font-bold text-white">{unread}</span> : null}
              </button>
              <div className="hidden max-w-[12rem] text-right sm:block">
                <p className="truncate text-sm font-semibold">{user?.full_name}</p>
                <p className="truncate text-xs text-moss">{user?.business_name || user?.email}</p>
              </div>
              <button onClick={logout} className={`${btnGhost} lg:hidden`}>Out</button>
            </div>
          </div>
          <select className="mt-3 w-full rounded-full border border-line bg-white px-3 py-2 text-sm lg:hidden" value={tab} onChange={(event) => setTab(event.target.value)}>
            {tabs.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </header>
        {openNotes ? (
          <div className="border-b border-line bg-paper px-4 py-4 md:px-8">
            <div className="grid gap-3 md:grid-cols-2">
              {notes.length === 0 ? <p className="text-sm text-moss">No notifications yet.</p> : notes.slice(0, 6).map((note) => (
                <article key={note.id} className="rounded-2xl border border-line bg-white px-3 py-2">
                  <p className="text-sm font-semibold">{note.title}</p>
                  <p className="text-sm text-moss">{note.body}</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}
        <main className="px-4 py-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}

export function NavItem() {
  return null;
}

export function ActiveLink({ to, children }) {
  return <NavLink to={to}>{children}</NavLink>;
}
