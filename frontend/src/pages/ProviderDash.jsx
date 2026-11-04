import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, DAYS, downloadBlob, inr, prettyDate } from "../api";
import { BookingPanel } from "../booking";
import { useAuth } from "../auth";
import { Bars, Empty, ErrorNote, Shell, Stat, StatusPill, btn, btnGhost, field } from "../ui";

const TABS = ["Overview", "Bookings", "Services", "Schedule", "Team", "Earnings", "Reviews", "Profile"].map((label) => ({ id: label.toLowerCase(), label }));

export default function ProviderDash() {
  const { user, refresh } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "overview";
  const focus = params.get("id");
  const [error, setError] = useState("");
  const [dash, setDash] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [techs, setTechs] = useState([]);
  const [offers, setOffers] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [hours, setHours] = useState([]);
  const [areas, setAreas] = useState([]);
  const [earnings, setEarnings] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [plans, setPlans] = useState([]);
  const [offer, setOffer] = useState({ service_id: "", price: "", description: "" });
  const [slot, setSlot] = useState({ day_of_week: 0, start_time: "09:00", end_time: "18:00" });
  const [area, setArea] = useState({ city: "Ahmedabad", pincode: "" });
  const [tech, setTech] = useState({ full_name: "", email: "", phone: "", password: "", skills: "" });
  const [reply, setReply] = useState({});
  const [profile, setProfile] = useState({ business_name: user?.business_name || "", bio: user?.bio || "", experience_years: user?.experience_years || 1 });

  function setTab(next) { setParams({ tab: next }); }

  async function load() {
    setError("");
    try {
      await refresh();
      if (tab === "overview") setDash(await api.get("/api/provider/dashboard"));
      if (tab === "bookings" || tab === "overview") {
        setBookings((await api.get("/api/bookings?page_size=50")).items);
        setTechs(await api.get("/api/provider/technicians"));
      }
      if (tab === "services") {
        setOffers(await api.get("/api/provider/services"));
        const services = await api.get("/api/services?page_size=50");
        setCatalog(services.items);
        if (!offer.service_id && services.items[0]) setOffer((current) => ({ ...current, service_id: services.items[0].id }));
      }
      if (tab === "schedule") {
        setHours(await api.get("/api/provider/availability"));
        setAreas(await api.get("/api/provider/areas"));
      }
      if (tab === "team") setTechs(await api.get("/api/provider/technicians"));
      if (tab === "earnings") setEarnings(await api.get("/api/provider/earnings"));
      if (tab === "reviews") setReviews(await api.get("/api/provider/reviews"));
      if (tab === "profile") setPlans(await api.get("/api/plans"));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, [tab]);

  const selected = bookings.find((item) => String(item.id) === String(focus));

  return (
    <Shell title={user?.business_name || "Provider"} tabs={TABS} tab={tab} setTab={setTab}>
      <ErrorNote error={error} />
      {user?.verification_status !== "approved" ? (
        <p className="mb-4 rounded-2xl bg-amber-100 px-4 py-3 text-sm">Verification is <strong>{user?.verification_status}</strong>. {user?.rejection_reason || "Upload an ID in Profile. You appear in search after approval."}</p>
      ) : null}
      {tab === "overview" && dash ? (
        <div className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Bookings" value={dash.total_bookings} />
            <Stat label="Today" value={dash.today} />
            <Stat label="Pending" value={dash.pending} />
            <Stat label="Completed" value={dash.completed} />
            <Stat label="Earnings" value={inr(dash.earnings)} hint={`${dash.rating} ★ · ${dash.rating_count} reviews`} />
          </div>
          <div className="rounded-3xl border border-line bg-paper p-4"><Bars data={dash.monthly} /></div>
        </div>
      ) : null}
      {tab === "bookings" ? (
        <div className="grid gap-3">
          {selected ? <BookingPanel booking={selected} role="provider" techs={techs} onChange={load} /> : null}
          {bookings.length === 0 ? <Empty title="No requests yet" body="Approved providers receive requests here." /> : bookings.map((booking) => (
            <button key={booking.id} onClick={() => setParams({ tab: "bookings", id: booking.id })} className="flex items-center justify-between rounded-3xl border border-line bg-white px-4 py-3 text-left">
              <span>{booking.booking_code} · {booking.service_name} · {prettyDate(booking.scheduled_date)} {booking.scheduled_time}</span>
              <StatusPill status={booking.status} />
            </button>
          ))}
        </div>
      ) : null}
      {tab === "services" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <form className="grid gap-2" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/provider/services", { ...offer, service_id: Number(offer.service_id), price: Number(offer.price) }); load(); }}>
            <select className={field} value={offer.service_id} onChange={(event) => setOffer({ ...offer, service_id: event.target.value })}>
              {catalog.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
            </select>
            <input className={field} type="number" placeholder="Your price" value={offer.price} onChange={(event) => setOffer({ ...offer, price: event.target.value })} required />
            <input className={field} placeholder="Note for customers" value={offer.description} onChange={(event) => setOffer({ ...offer, description: event.target.value })} />
            <button className={btn}>Add service</button>
          </form>
          <div className="grid gap-2">
            {offers.map((item) => (
              <article key={item.id} className="flex items-center justify-between rounded-3xl border border-line bg-paper px-4 py-3">
                <span>{item.name}<br /><span className="text-sm text-moss">{inr(item.price)}</span></span>
                <button className={btnGhost} onClick={async () => { await api.patch(`/api/provider/services/${item.id}`, { status: item.status === "active" ? "inactive" : "active" }); load(); }}>{item.status}</button>
              </article>
            ))}
          </div>
        </div>
      ) : null}
      {tab === "schedule" ? (
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <form className="grid grid-cols-3 gap-2" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/provider/availability", { ...slot, day_of_week: Number(slot.day_of_week) }); load(); }}>
              <select className={field} value={slot.day_of_week} onChange={(event) => setSlot({ ...slot, day_of_week: event.target.value })}>{DAYS.map((day, index) => <option key={day} value={index}>{day}</option>)}</select>
              <input className={field} value={slot.start_time} onChange={(event) => setSlot({ ...slot, start_time: event.target.value })} />
              <input className={field} value={slot.end_time} onChange={(event) => setSlot({ ...slot, end_time: event.target.value })} />
              <button className={`${btn} col-span-3`}>Add hours</button>
            </form>
            <ul className="mt-3 space-y-2 text-sm">
              {hours.map((hour) => <li key={hour.id} className="flex justify-between rounded-2xl bg-paper px-3 py-2">{DAYS[hour.day_of_week]} {hour.start_time}–{hour.end_time} <button onClick={async () => { await api.del(`/api/provider/availability/${hour.id}`); load(); }}>Remove</button></li>)}
            </ul>
          </div>
          <div>
            <form className="grid grid-cols-2 gap-2" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/provider/areas", area); load(); }}>
              <input className={field} value={area.city} onChange={(event) => setArea({ ...area, city: event.target.value })} />
              <input className={field} placeholder="Pincode" value={area.pincode} onChange={(event) => setArea({ ...area, pincode: event.target.value })} />
              <button className={`${btn} col-span-2`}>Add area</button>
            </form>
            <ul className="mt-3 space-y-2 text-sm">
              {areas.map((item) => <li key={item.id} className="flex justify-between rounded-2xl bg-paper px-3 py-2">{item.city} {item.pincode} <button onClick={async () => { await api.del(`/api/provider/areas/${item.id}`); load(); }}>Remove</button></li>)}
            </ul>
          </div>
        </div>
      ) : null}
      {tab === "team" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <form className="grid gap-2" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/provider/technicians", tech); setTech({ full_name: "", email: "", phone: "", password: "", skills: "" }); load(); }}>
            <input className={field} placeholder="Name" value={tech.full_name} onChange={(event) => setTech({ ...tech, full_name: event.target.value })} required />
            <input className={field} placeholder="Email" value={tech.email} onChange={(event) => setTech({ ...tech, email: event.target.value })} required />
            <input className={field} placeholder="Phone" value={tech.phone} onChange={(event) => setTech({ ...tech, phone: event.target.value })} />
            <input className={field} placeholder="Temporary password" value={tech.password} onChange={(event) => setTech({ ...tech, password: event.target.value })} required />
            <input className={field} placeholder="Skills" value={tech.skills} onChange={(event) => setTech({ ...tech, skills: event.target.value })} />
            <button className={btn}>Add technician</button>
          </form>
          <div className="grid gap-2">
            {techs.map((item) => <article key={item.id} className="rounded-3xl border border-line bg-paper p-4"><strong>{item.name}</strong><p className="text-sm text-moss">{item.email} · {item.skills} · {item.completed_jobs} done</p></article>)}
          </div>
        </div>
      ) : null}
      {tab === "earnings" ? (
        <div>
          <button className={`${btnGhost} mb-3`} onClick={async () => downloadBlob(await api.get("/api/provider/earnings.csv"), "earnings.csv")}>Export CSV</button>
          <div className="grid gap-2">
            {earnings.map((item) => <article key={item.id} className="flex justify-between rounded-3xl border border-line bg-paper px-4 py-3 text-sm"><span>{item.booking_code} · gross {inr(item.gross)} · commission {inr(item.commission)}</span><StatusPill status={item.status} /></article>)}
          </div>
        </div>
      ) : null}
      {tab === "reviews" ? (
        <div className="grid gap-3">
          {reviews.map((review) => (
            <article key={review.id} className="rounded-3xl border border-line bg-paper p-4">
              <p className="font-semibold">{review.customer_name} · {review.rating}/5</p>
              <p className="text-sm">{review.comment}</p>
              {review.provider_response ? <p className="mt-2 text-sm text-moss">Your reply: {review.provider_response}</p> : (
                <div className="mt-2 flex gap-2">
                  <input className={field} placeholder="Reply" value={reply[review.id] || ""} onChange={(event) => setReply({ ...reply, [review.id]: event.target.value })} />
                  <button className={btn} onClick={async () => { await api.post(`/api/reviews/${review.id}/respond`, { response: reply[review.id] || "Thank you." }); load(); }}>Reply</button>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : null}
      {tab === "profile" ? (
        <div className="grid max-w-lg gap-3">
          <input className={field} value={profile.business_name} onChange={(event) => setProfile({ ...profile, business_name: event.target.value })} />
          <textarea className={field} rows="4" value={profile.bio} onChange={(event) => setProfile({ ...profile, bio: event.target.value })} />
          <input className={field} type="number" value={profile.experience_years} onChange={(event) => setProfile({ ...profile, experience_years: Number(event.target.value) })} />
          <button className={btn} onClick={async () => { await api.patch("/api/provider/profile", profile); refresh(); }}>Save profile</button>
          <label className="text-sm text-moss">Identity document <input type="file" accept="image/*,.pdf" onChange={async (event) => { const file = event.target.files?.[0]; if (!file) return; const uploaded = await api.upload(file); await api.patch("/api/provider/profile", { document_url: uploaded.url }); refresh(); }} /></label>
          {user?.document_url ? <a className="text-sm font-semibold text-forest" href={user.document_url}>View uploaded document</a> : null}
          <div className="grid gap-2">
            {plans.map((plan) => (
              <button key={plan.id} className={btnGhost} onClick={async () => { await api.post("/api/provider/plan", { plan_id: plan.id }); refresh(); }}>
                {plan.name} · {inr(plan.price)}/mo · {plan.commission_rate}% commission {user?.plan_id === plan.id ? "· current" : ""}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </Shell>
  );
}
