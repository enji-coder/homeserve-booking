import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, inr } from "../api";
import { Icon, TopNav, btn, btnClay, field } from "../ui";

const STEPS = [
  ["Pick the job", "Switchboard, leak, AC gas, a room that needs paint. Search by what is actually wrong."],
  ["Choose a crew", "See the price, the area they cover, and the rating from finished visits."],
  ["Hold a time", "Slots come from the provider's working hours. A taken hour cannot be booked twice."],
  ["Pay and review", "Advance or full payment in Razorpay test mode, then a rating once the job is done."],
];

export default function Landing() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [categories, setCategories] = useState([]);
  const [providers, setProviders] = useState([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.get("/api/public/stats").then(setStats).catch(() => {});
    api.get("/api/categories").then((rows) => setCategories(rows.filter((row) => !row.parent_id))).catch(() => {});
    api.get("/api/providers").then((rows) => setProviders(rows.slice(0, 4))).catch(() => {});
  }, []);

  return (
    <div>
      <TopNav />
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-14 md:grid-cols-[1.1fr_0.9fr] md:pb-28 md:pt-20">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-clay">HomeServe Technologies · Ahmedabad</p>
          <h1 className="mt-4 max-w-xl font-display text-5xl leading-[1.02] md:text-7xl">The right technician, at the hour you actually picked.</h1>
          <p className="mt-5 max-w-lg text-lg text-moss">Electricians, plumbers, AC crews, cleaners and carpenters. Verified by the platform, booked with a real slot, and paid with a receipt.</p>
          <form className="mt-8 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => { event.preventDefault(); navigate(`/services?q=${encodeURIComponent(query)}`); }}>
            <input className={field} placeholder="Try AC service, tap repair, fan…" value={query} onChange={(event) => setQuery(event.target.value)} />
            <button className={btnClay}>Search services</button>
          </form>
          <div className="mt-8 grid grid-cols-3 gap-4 max-w-md">
            <div><p className="font-display text-3xl">{stats?.providers ?? "—"}</p><p className="text-xs uppercase tracking-wider text-moss">Verified crews</p></div>
            <div><p className="font-display text-3xl">{stats?.categories ?? "—"}</p><p className="text-xs uppercase tracking-wider text-moss">Categories</p></div>
            <div><p className="font-display text-3xl">{stats?.bookings ?? "—"}</p><p className="text-xs uppercase tracking-wider text-moss">Bookings</p></div>
          </div>
        </div>
        <div className="relative">
          <div className="rounded-[32px] bg-ink p-6 text-cream shadow-card">
            <div className="flex items-center justify-between text-xs uppercase tracking-[0.16em] text-white/50">
              <span>Today · Satellite</span>
              <span className="rounded-full bg-clay px-3 py-1 text-white">In progress</span>
            </div>
            <h2 className="mt-8 font-display text-4xl">Bedroom AC service</h2>
            <p className="mt-2 text-white/70">CoolBreeze AC · Imran has reached the flat.</p>
            <div className="mt-8 grid grid-cols-3 gap-3 border-t border-white/10 pt-4 text-sm">
              <div><p className="text-white/45">Window</p><p className="mt-1 text-lg">09:00</p></div>
              <div><p className="text-white/45">Code</p><p className="mt-1 text-lg">HS-live</p></div>
              <div><p className="text-white/45">Balance</p><p className="mt-1 text-lg">₹825</p></div>
            </div>
          </div>
          <div className="absolute -bottom-6 -left-3 hidden rounded-3xl border border-line bg-paper px-4 py-3 shadow-card md:block">
            <p className="text-xs uppercase tracking-wider text-moss">Next request</p>
            <p className="font-display text-2xl">Fan installation · 15:00</p>
          </div>
        </div>
      </section>

      <section id="services" className="mx-auto max-w-6xl px-5 py-8">
        <div className="flex items-end justify-between gap-4">
          <h2 className="font-display text-4xl">What the city calls us for</h2>
          <Link to="/services" className="text-sm font-semibold text-forest">All services</Link>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {categories.map((category) => (
            <Link key={category.id} to={`/services?category=${category.id}`} className="rounded-3xl border border-line bg-paper p-4 transition hover:-translate-y-0.5 hover:shadow-card">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-leaf text-forest"><Icon name={category.icon} /></span>
              <h3 className="mt-4 font-display text-2xl">{category.name.replace(" Services", "").replace(" & Maintenance", "")}</h3>
              <p className="mt-1 text-sm text-moss">{category.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section id="how" className="mx-auto grid max-w-6xl gap-8 px-5 py-14 md:grid-cols-[0.8fr_1.2fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">The visit</p>
          <h2 className="mt-2 font-display text-4xl">Four steps, then someone is at the door.</h2>
        </div>
        <ol className="grid gap-3 sm:grid-cols-2">
          {STEPS.map(([title, body], index) => (
            <li key={title} className="rounded-3xl border border-line bg-paper p-4">
              <p className="font-display text-3xl text-clay">0{index + 1}</p>
              <h3 className="mt-2 font-display text-2xl">{title}</h3>
              <p className="mt-1 text-sm text-moss">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-16">
        <h2 className="font-display text-4xl">Crews already on the platform</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {providers.map((provider) => (
            <Link key={provider.id} to={`/providers/${provider.id}`} className="rounded-[28px] border border-line bg-paper p-5 hover:shadow-card">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-3xl">{provider.business_name}</h3>
                  <p className="text-sm text-moss">{provider.contact_name} · {provider.experience_years} years · {provider.city}</p>
                </div>
                <p className="rounded-full bg-leaf px-3 py-1 text-sm font-semibold text-forest">{provider.rating_avg || "New"} ★</p>
              </div>
              <p className="mt-3 text-sm text-moss">{provider.bio}</p>
              <p className="mt-4 text-sm font-semibold">From {inr(provider.starting_price)} · {provider.services.join(", ")}</p>
            </Link>
          ))}
        </div>
        <div className="mt-10 flex flex-wrap items-center justify-between gap-4 rounded-[28px] bg-forest px-6 py-6 text-cream">
          <div>
            <h2 className="font-display text-3xl">Run jobs, or book one.</h2>
            <p className="mt-1 text-white/75">Customers, providers, technicians and the HomeServe admin each have their own workspace.</p>
          </div>
          <Link to="/register" className={btnClay}>Create an account</Link>
        </div>
      </section>
      <footer className="border-t border-line px-5 py-8 text-center text-sm text-moss">HomeServe Technologies · Ahmedabad · Bookings, payments and reviews in one place.</footer>
    </div>
  );
}
