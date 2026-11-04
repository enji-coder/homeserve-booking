import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, inr, prettyDate, DAYS } from "../api";
import { useAuth } from "../auth";
import { ErrorNote, Icon, StatusPill, TopNav, btn, btnClay, btnGhost, field } from "../ui";

export function Services() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], total: 0 });
  const [categories, setCategories] = useState([]);
  const q = params.get("q") || "";
  const category = params.get("category") || "";
  const city = params.get("city") || "";
  const page = Math.max(1, Number(params.get("page") || "1"));

  useEffect(() => {
    api.get("/api/categories").then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    const query = new URLSearchParams();
    if (q) query.set("q", q);
    if (category) query.set("category_id", category);
    if (city) query.set("city", city);
    query.set("page", String(page));
    query.set("page_size", "6");
    api.get(`/api/services?${query.toString()}`).then(setData).catch(() => setData({ items: [], total: 0 }));
  }, [q, category, city, page]);

  function update(key, value) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next);
  }

  return (
    <div>
      <TopNav />
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-5 sm:py-10">
        <h1 className="font-display text-4xl sm:text-5xl">Services</h1>
        <p className="mt-2 text-moss">{data.total} live listings from verified crews.</p>
        <div className="mt-6 grid gap-2 md:grid-cols-3">
          <input className={field} placeholder="Search" value={q} onChange={(event) => update("q", event.target.value)} />
          <select className={field} value={category} onChange={(event) => update("category", event.target.value)}>
            <option value="">All categories</option>
            {categories.filter((item) => !item.parent_id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <input className={field} placeholder="City, e.g. Ahmedabad" value={city} onChange={(event) => update("city", event.target.value)} />
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {data.items.map((service) => (
            <Link key={service.id} to={`/services/${service.id}`} className="rounded-[28px] border border-line bg-paper p-5 hover:-translate-y-0.5 hover:shadow-card">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-leaf text-forest"><Icon name={service.icon} /></span>
              <h2 className="mt-4 font-display text-3xl">{service.name}</h2>
              <p className="mt-2 line-clamp-2 text-sm text-moss">{service.description}</p>
              <div className="mt-4 flex flex-wrap items-end justify-between gap-2">
                <p className="font-display text-2xl">{inr(service.min_price)}</p>
                <p className="text-sm text-moss">{service.provider_count} crews · {service.duration_mins} min</p>
              </div>
            </Link>
          ))}
        </div>
        {data.items.length === 0 ? <p className="mt-8 text-moss">Nothing matches that filter yet.</p> : null}
        {data.total > 6 ? (
          <div className="mt-6 flex items-center justify-between">
            <button className={btnGhost} disabled={page <= 1} onClick={() => update("page", String(page - 1))}>Previous</button>
            <p className="text-sm text-moss">Page {page} of {Math.ceil(data.total / 6)}</p>
            <button className={btnGhost} disabled={page >= Math.ceil(data.total / 6)} onClick={() => update("page", String(page + 1))}>Next</button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function ServiceDetail() {
  const { id } = useParams();
  const [service, setService] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/api/services/${id}`).then(setService).catch((err) => setError(err.message));
  }, [id]);

  return (
    <div>
      <TopNav />
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-5 sm:py-10">
        <ErrorNote error={error} />
        {service ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-clay">{service.category}</p>
            <h1 className="mt-2 break-words font-display text-4xl sm:text-5xl">{service.name}</h1>
            <p className="mt-3 max-w-2xl text-moss">{service.description}</p>
            <div className="mt-8 grid gap-4">
              {service.providers?.map((provider) => (
                <article key={provider.offer_id} className="grid gap-4 rounded-[28px] border border-line bg-paper p-5 md:grid-cols-[1fr_auto] md:items-center">
                  <div>
                    <Link to={`/providers/${provider.id}`} className="font-display text-3xl hover:text-forest">{provider.business_name}</Link>
                    <p className="text-sm text-moss">{provider.rating_avg || "New"} ★ · {provider.rating_count} reviews · {provider.experience_years} years · {provider.areas.map((area) => area.pincode).join(", ")}</p>
                    <p className="mt-2 text-sm">{provider.bio}</p>
                  </div>
                  <div className="sm:text-right">
                    <p className="font-display text-3xl">{inr(provider.price)}</p>
                    <Link to={`/book/${provider.offer_id}`} className={`${btnClay} mt-3`}>Book this crew</Link>
                  </div>
                </article>
              ))}
              {service.providers?.length === 0 ? <p className="text-moss">No verified provider is offering this yet. An admin can approve a waiting crew.</p> : null}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

export function ProviderPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [provider, setProvider] = useState(null);
  const [fav, setFav] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/api/providers/${id}`).then(setProvider).catch((err) => setError(err.message));
  }, [id]);

  async function toggle() {
    try {
      const data = await api.post(`/api/favorites/${id}`);
      setFav(data.favorite);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <TopNav />
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-5 sm:py-10">
        <ErrorNote error={error} />
        {provider ? (
          <div className="grid gap-6 md:grid-cols-[1.2fr_0.8fr]">
            <div>
              <h1 className="break-words font-display text-4xl sm:text-5xl">{provider.business_name}</h1>
              <p className="mt-2 text-moss">{provider.contact_name} · {provider.experience_years} years · {provider.rating_avg} ★ from {provider.rating_count} reviews</p>
              <p className="mt-4 max-w-xl">{provider.bio}</p>
              {user?.role === "customer" ? <button className={`${btnGhost} mt-4`} onClick={toggle}>{fav ? "Saved" : "Save provider"}</button> : null}
              <h2 className="mt-8 font-display text-3xl">Services</h2>
              <div className="mt-3 grid gap-3">
                {provider.offers.map((offer) => (
                  <div key={offer.offer_id} className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-line bg-paper px-4 py-3">
                    <div>
                      <p className="font-semibold">{offer.name}</p>
                      <p className="text-sm text-moss">{offer.duration_mins} min</p>
                    </div>
                    <div className="sm:text-right">
                      <p className="font-display text-2xl">{inr(offer.price)}</p>
                      <Link to={`/book/${offer.offer_id}`} className="text-sm font-semibold text-forest">Book</Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <aside className="rounded-[28px] border border-line bg-paper p-5">
              <h2 className="font-display text-2xl">Hours & areas</h2>
              <ul className="mt-3 space-y-1 text-sm">
                {provider.hours.map((hour) => <li key={`${hour.day_of_week}-${hour.start_time}`}>{DAYS[hour.day_of_week]} · {hour.start_time}–{hour.end_time}</li>)}
              </ul>
              <p className="mt-4 text-sm text-moss">{provider.areas.map((area) => `${area.city} ${area.pincode}`).join(" · ")}</p>
              <h2 className="mt-6 font-display text-2xl">Reviews</h2>
              <div className="mt-3 space-y-3">
                {provider.reviews.length === 0 ? <p className="text-sm text-moss">No public reviews yet.</p> : provider.reviews.map((review) => (
                  <article key={review.id} className="rounded-2xl bg-white p-3 text-sm">
                    <p className="font-semibold">{review.customer_name} · {review.rating}/5</p>
                    <p className="mt-1">{review.comment}</p>
                    {review.provider_response ? <p className="mt-1 text-moss">Reply: {review.provider_response}</p> : null}
                  </article>
                ))}
              </div>
            </aside>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function Book() {
  const { offerId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [offer, setOffer] = useState(null);
  const [addresses, setAddresses] = useState([]);
  const [date, setDate] = useState("");
  const [slots, setSlots] = useState([]);
  const [time, setTime] = useState("");
  const [addressId, setAddressId] = useState("");
  const [line1, setLine1] = useState("");
  const [city, setCity] = useState("Ahmedabad");
  const [pincode, setPincode] = useState("380015");
  const [note, setNote] = useState("");
  const [coupon, setCoupon] = useState("");
  const [preview, setPreview] = useState(null);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/api/offers/${offerId}`).then(setOffer).catch((err) => setError(err.message));
    if (user?.role === "customer") {
      api.get("/api/addresses").then((rows) => {
        setAddresses(rows);
        const preferred = rows.find((row) => row.is_default) || rows[0];
        if (preferred) setAddressId(String(preferred.id));
      }).catch(() => {});
    }
  }, [offerId, user]);

  useEffect(() => {
    if (!offer || !date) return;
    api.get(`/api/slots?provider_id=${offer.provider.id}&scheduled_date=${date}`).then(setSlots).catch((err) => setError(err.message));
  }, [offer, date]);

  async function applyCoupon() {
    if (!offer || !coupon) return;
    try {
      setPreview(await api.post("/api/coupons/preview", { code: coupon, amount: offer.price }));
      setError("");
    } catch (err) {
      setPreview(null);
      setError(err.message);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (user?.role !== "customer") {
      setError("Log in as a customer to book.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const booking = await api.post("/api/bookings", {
        provider_service_id: Number(offerId),
        scheduled_date: date,
        scheduled_time: time,
        address_id: addressId ? Number(addressId) : null,
        line1, city, pincode, problem_note: note, coupon_code: coupon,
      });
      if (file) {
        const uploaded = await api.upload(file);
        await api.post(`/api/bookings/${booking.id}/images`, { url: uploaded.url, kind: "problem" });
      }
      navigate(`/app?tab=bookings&id=${booking.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const price = preview?.total || (offer ? Math.round(offer.price * 1.18) : 0);

  return (
    <div>
      <TopNav />
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-5 sm:py-10 md:grid-cols-[1.2fr_0.8fr]">
        <form className="grid gap-3 rounded-[28px] border border-line bg-paper p-5" onSubmit={submit}>
          <h1 className="break-words font-display text-3xl sm:text-4xl">Book {offer?.service.name}</h1>
          <p className="text-sm text-moss">{offer?.provider.business_name} · {inr(offer?.price)} before GST</p>
          <input className={field} type="date" min={new Date().toISOString().slice(0, 10)} value={date} onChange={(event) => { setDate(event.target.value); setTime(""); }} required />
          <div className="flex flex-wrap gap-2">
            {slots.map((slot) => (
              <button type="button" key={slot.time} disabled={!slot.available} onClick={() => setTime(slot.time)} className={`rounded-full px-3 py-2 text-sm font-semibold ${time === slot.time ? "bg-forest text-white" : "bg-white"} ${slot.available ? "" : "cursor-not-allowed opacity-40"}`}>{slot.time}</button>
            ))}
            {date && slots.length === 0 ? <p className="text-sm text-moss">No working hours on this date.</p> : null}
          </div>
          {addresses.length ? (
            <select className={field} value={addressId} onChange={(event) => setAddressId(event.target.value)}>
              <option value="">New address</option>
              {addresses.map((address) => <option key={address.id} value={address.id}>{address.label}: {address.line1}</option>)}
            </select>
          ) : null}
          {!addressId ? (
            <div className="grid gap-2 md:grid-cols-3">
              <input className={`${field} md:col-span-3`} placeholder="Flat, society, area" value={line1} onChange={(event) => setLine1(event.target.value)} />
              <input className={field} placeholder="City" value={city} onChange={(event) => setCity(event.target.value)} />
              <input className={field} placeholder="Pincode" value={pincode} onChange={(event) => setPincode(event.target.value)} />
            </div>
          ) : null}
          <textarea className={field} rows="3" placeholder="What should the technician know?" value={note} onChange={(event) => setNote(event.target.value)} />
          <label className="text-sm text-moss">Problem photo <input type="file" accept="image/*" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input className={field} placeholder="Coupon, try WELCOME10" value={coupon} onChange={(event) => setCoupon(event.target.value.toUpperCase())} />
            <button type="button" className={btnGhost} onClick={applyCoupon}>Apply</button>
          </div>
          <ErrorNote error={error} />
          <button className={btnClay} disabled={busy || !time}>{busy ? "Booking…" : "Confirm booking"}</button>
        </form>
        <aside className="h-fit rounded-[28px] bg-ink p-5 text-cream">
          <p className="text-xs uppercase tracking-[0.16em] text-white/50">Payable</p>
          <p className="mt-3 font-display text-4xl sm:text-5xl">{inr(price)}</p>
          <p className="mt-2 text-sm text-white/70">{preview ? `Discount ${inr(preview.discount)} · GST ${inr(preview.gst)}` : "18% GST is added on the service amount."}</p>
          <p className="mt-6 text-sm text-white/70">{date && time ? `${prettyDate(date)} at ${time}` : "Pick a free slot. Taken hours stay locked."}</p>
          <StatusPill status="Pending" />
        </aside>
      </div>
    </div>
  );
}
