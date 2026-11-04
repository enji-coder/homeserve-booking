import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, downloadBlob, inr, prettyDate } from "../api";
import { BookingPanel } from "../booking";
import { Bars, ErrorNote, Shell, Stat, StatusPill, btn, btnGhost, field } from "../ui";

const TABS = ["Overview", "Customers", "Providers", "Catalog", "Bookings", "Payments", "Coupons", "Complaints", "Plans", "Reports"].map((label) => ({ id: label.toLowerCase(), label }));

export default function AdminDash() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "overview";
  const focus = params.get("id");
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [categories, setCategories] = useState([]);
  const [services, setServices] = useState([]);
  const [listings, setListings] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [payments, setPayments] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [plans, setPlans] = useState([]);
  const [category, setCategory] = useState({ name: "", description: "", icon: "bolt", parent_id: "" });
  const [service, setService] = useState({ category_id: "", name: "", description: "", base_price: "", duration_mins: 60 });
  const [coupon, setCoupon] = useState({ code: "", discount_type: "percent", value: 10, min_amount: 0, expires_on: "2027-12-31", is_active: true });
  const [plan, setPlan] = useState({ name: "", price: 0, commission_rate: 15, description: "", features: "" });
  const [note, setNote] = useState({});
  const [announce, setAnnounce] = useState({ title: "", body: "", audience: "all" });

  function setTab(next) { setParams({ tab: next }); }

  async function load() {
    setError("");
    try {
      if (tab === "overview") setStats(await api.get("/api/admin/stats"));
      if (tab === "customers") setUsers(await api.get("/api/admin/users?role=customer"));
      if (tab === "providers") setUsers(await api.get("/api/admin/users?role=provider"));
      if (tab === "catalog") {
        const cats = await api.get("/api/categories");
        setCategories(cats);
        setServices((await api.get("/api/services?page_size=50")).items);
        setListings(await api.get("/api/admin/listings"));
        if (cats[0]) setService((current) => ({ ...current, category_id: current.category_id || cats[0].id }));
      }
      if (tab === "bookings") setBookings((await api.get("/api/bookings?page_size=50")).items);
      if (tab === "payments") setPayments(await api.get("/api/payments"));
      if (tab === "coupons") setCoupons(await api.get("/api/coupons"));
      if (tab === "complaints") setComplaints(await api.get("/api/complaints"));
      if (tab === "plans") setPlans(await api.get("/api/plans"));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, [tab]);
  const selected = bookings.find((item) => String(item.id) === String(focus));

  return (
    <Shell title="HomeServe desk" tabs={TABS} tab={tab} setTab={setTab}>
      <ErrorNote error={error} />
      {tab === "overview" && stats ? (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Customers" value={stats.customers} />
            <Stat label="Providers" value={stats.providers} />
            <Stat label="Technicians" value={stats.technicians} />
            <Stat label="Bookings" value={stats.bookings} />
            <Stat label="Pending" value={stats.pending} />
            <Stat label="Completed" value={stats.completed} />
            <Stat label="Cancelled" value={stats.cancelled} />
            <Stat label="Revenue" value={inr(stats.revenue)} />
            <Stat label="Commission" value={inr(stats.commission)} hint={`Provider net ${inr(stats.provider_earnings)}`} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-line bg-paper p-4"><p className="mb-3 text-sm font-semibold">Monthly bookings</p><Bars data={stats.monthly} y="bookings" /></div>
            <div className="rounded-3xl border border-line bg-paper p-4"><p className="mb-3 text-sm font-semibold">Monthly revenue</p><Bars data={stats.monthly} /></div>
            <div className="rounded-3xl border border-line bg-paper p-4 md:col-span-2"><p className="mb-3 text-sm font-semibold">Customer growth</p><Bars data={stats.growth} y="customers" /></div>
          </div>
          <div className="rounded-3xl border border-line bg-paper p-4">
            <p className="text-sm font-semibold">Popular categories</p>
            <ul className="mt-2 text-sm">{stats.popular.map((item) => <li key={item.name} className="flex justify-between gap-3 border-t border-line py-2"><span className="min-w-0 break-words">{item.name}</span><span className="shrink-0">{item.count}</span></li>)}</ul>
          </div>
        </div>
      ) : null}
      {tab === "customers" ? (
        <div className="grid gap-2">{users.map((person) => (
          <article key={person.id} className="flex flex-wrap items-center justify-between gap-2 rounded-3xl border border-line bg-paper px-4 py-3">
            <span className="min-w-0 flex-1 break-words">{person.full_name}<br /><span className="text-sm text-moss">{person.email} · {person.phone}</span></span>
            <button className={btnGhost} onClick={async () => { await api.patch(`/api/admin/users/${person.id}`, { status: person.status === "active" ? "suspended" : "active" }); load(); }}>{person.status}</button>
          </article>
        ))}</div>
      ) : null}
      {tab === "providers" ? (
        <div className="grid gap-3">{users.map((person) => (
          <article key={person.id} className="rounded-3xl border border-line bg-paper p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div><strong>{person.business_name}</strong><p className="text-sm text-moss">{person.full_name} · {person.email}</p></div>
              <StatusPill status={person.verification_status} />
            </div>
            {person.document_url ? <a className="mt-2 inline-block text-sm font-semibold text-forest" href={person.document_url}>View document</a> : <p className="mt-2 text-sm text-moss">No document uploaded.</p>}
            <div className="mt-3 flex flex-wrap gap-2">
              <button className={btn} onClick={async () => { await api.post(`/api/admin/providers/${person.provider_id}/verify`, { status: "approved" }); load(); }}>Approve</button>
              <input className={field} placeholder="Rejection reason" value={note[person.id] || ""} onChange={(event) => setNote({ ...note, [person.id]: event.target.value })} />
              <button className={btnGhost} onClick={async () => { await api.post(`/api/admin/providers/${person.provider_id}/verify`, { status: "rejected", reason: note[person.id] || "Documents unclear" }); load(); }}>Reject</button>
            </div>
          </article>
        ))}</div>
      ) : null}
      {tab === "catalog" ? (
        <div className="grid gap-6">
          <form className="grid gap-2 md:grid-cols-4" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/categories", { ...category, parent_id: category.parent_id ? Number(category.parent_id) : null }); load(); }}>
            <input className={field} placeholder="Category" value={category.name} onChange={(event) => setCategory({ ...category, name: event.target.value })} required />
            <input className={field} placeholder="Description" value={category.description} onChange={(event) => setCategory({ ...category, description: event.target.value })} />
            <select className={field} value={category.parent_id} onChange={(event) => setCategory({ ...category, parent_id: event.target.value })}>
              <option value="">Top level</option>
              {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <button className={btn}>Add category</button>
          </form>
          <form className="grid gap-2 md:grid-cols-4" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/services", { ...service, category_id: Number(service.category_id), base_price: Number(service.base_price), duration_mins: Number(service.duration_mins) }); load(); }}>
            <select className={field} value={service.category_id} onChange={(event) => setService({ ...service, category_id: event.target.value })}>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <input className={field} placeholder="Service name" value={service.name} onChange={(event) => setService({ ...service, name: event.target.value })} required />
            <input className={field} type="number" placeholder="Base price" value={service.base_price} onChange={(event) => setService({ ...service, base_price: event.target.value })} required />
            <button className={btn}>Add service</button>
          </form>
          <div className="grid gap-2">{listings.map((item) => (
            <article key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-paper px-3 py-2 text-sm"><span className="min-w-0 flex-1 break-words">{item.provider} · {item.service} · {inr(item.price)}</span><button className="shrink-0" onClick={async () => { await api.patch(`/api/admin/listings/${item.id}`, { status: item.status === "active" ? "inactive" : "active" }); load(); }}>{item.status}</button></article>
          ))}</div>
        </div>
      ) : null}
      {tab === "bookings" ? (
        <div className="grid gap-3">
          {selected ? <BookingPanel booking={selected} role="admin" onChange={load} /> : null}
          {bookings.map((booking) => <button key={booking.id} onClick={() => setParams({ tab: "bookings", id: booking.id })} className="flex flex-wrap items-center justify-between gap-2 rounded-3xl border border-line bg-white px-4 py-3 text-left"><span className="min-w-0 flex-1 break-words">{booking.booking_code} · {booking.customer_name} · {booking.service_name} · {prettyDate(booking.scheduled_date)}</span><StatusPill status={booking.status} /></button>)}
        </div>
      ) : null}
      {tab === "payments" ? <div className="grid gap-2">{payments.map((payment) => <article key={payment.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-paper px-4 py-3 text-sm"><span className="min-w-0 flex-1 break-words">{payment.booking_code} · {inr(payment.amount)} · {payment.txn_id || payment.order_id}</span><StatusPill status={payment.status} /></article>)}</div> : null}
      {tab === "coupons" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <form className="grid gap-2" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/coupons", { ...coupon, value: Number(coupon.value), min_amount: Number(coupon.min_amount) }); load(); }}>
            <input className={field} placeholder="CODE" value={coupon.code} onChange={(event) => setCoupon({ ...coupon, code: event.target.value.toUpperCase() })} required />
            <select className={field} value={coupon.discount_type} onChange={(event) => setCoupon({ ...coupon, discount_type: event.target.value })}><option value="percent">Percent</option><option value="flat">Flat ₹</option></select>
            <input className={field} type="number" value={coupon.value} onChange={(event) => setCoupon({ ...coupon, value: event.target.value })} />
            <input className={field} type="number" placeholder="Minimum amount" value={coupon.min_amount} onChange={(event) => setCoupon({ ...coupon, min_amount: event.target.value })} />
            <button className={btn}>Create coupon</button>
          </form>
          <div className="grid gap-2">{coupons.map((item) => <article key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-paper px-3 py-2 text-sm"><span className="min-w-0 break-words">{item.code} · {item.discount_type} {item.value}</span><button className="shrink-0" onClick={async () => { await api.patch(`/api/coupons/${item.id}`, { ...item, is_active: !item.is_active }); load(); }}>{item.is_active ? "active" : "off"}</button></article>)}</div>
        </div>
      ) : null}
      {tab === "complaints" ? <div className="grid gap-3">{complaints.map((item) => (
        <article key={item.id} className="rounded-3xl border border-line bg-paper p-4">
          <div className="flex flex-wrap items-start justify-between gap-2"><strong className="min-w-0 break-words">{item.subject}</strong><StatusPill status={item.status} /></div>
          <p className="text-sm text-moss">{item.customer_name} · {item.booking_code} · {item.description}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <input className={field} placeholder="Note to the customer" id={`note-${item.id}`} />
            {["Open", "In Review", "Resolved"].map((status) => <button key={status} className={btnGhost} onClick={async () => { const admin_note = document.getElementById(`note-${item.id}`).value; await api.patch(`/api/complaints/${item.id}`, { status, admin_note }); load(); }}>{status}</button>)}
          </div>
        </article>
      ))}</div> : null}
      {tab === "plans" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <form className="grid gap-2" onSubmit={async (event) => { event.preventDefault(); await api.post("/api/plans", { ...plan, price: Number(plan.price), commission_rate: Number(plan.commission_rate) }); load(); }}>
            <input className={field} placeholder="Plan name" value={plan.name} onChange={(event) => setPlan({ ...plan, name: event.target.value })} required />
            <input className={field} type="number" placeholder="Monthly price" value={plan.price} onChange={(event) => setPlan({ ...plan, price: event.target.value })} />
            <input className={field} type="number" placeholder="Commission %" value={plan.commission_rate} onChange={(event) => setPlan({ ...plan, commission_rate: event.target.value })} />
            <button className={btn}>Add plan</button>
          </form>
          <div className="grid gap-2">{plans.map((item) => <article key={item.id} className="rounded-2xl bg-paper px-3 py-2 text-sm"><strong>{item.name}</strong> · {inr(item.price)} · {item.commission_rate}% · {item.description}</article>)}</div>
        </div>
      ) : null}
      {tab === "reports" ? (
        <div className="grid max-w-xl gap-3">
          <div className="flex flex-wrap gap-2">
            <button className={btn} onClick={async () => downloadBlob(await api.get("/api/reports/bookings.csv"), "bookings.csv")}>Bookings CSV</button>
            <button className={btnGhost} onClick={async () => downloadBlob(await api.get("/api/reports/payments.csv"), "payments.csv")}>Payments CSV</button>
            <button className={btnGhost} onClick={async () => downloadBlob(await api.get("/api/reports/customers.csv"), "customers.csv")}>Customers CSV</button>
          </div>
          <input className={field} placeholder="Announcement title" value={announce.title} onChange={(event) => setAnnounce({ ...announce, title: event.target.value })} />
          <textarea className={field} rows="3" placeholder="Message" value={announce.body} onChange={(event) => setAnnounce({ ...announce, body: event.target.value })} />
          <select className={field} value={announce.audience} onChange={(event) => setAnnounce({ ...announce, audience: event.target.value })}>
            <option value="all">Everyone</option>
            <option value="customer">Customers</option>
            <option value="provider">Providers</option>
            <option value="technician">Technicians</option>
          </select>
          <button className={btn} onClick={async () => { const sent = await api.post("/api/admin/announcements", announce); setError(`Sent to ${sent.sent} people.`); }}>Send announcement</button>
        </div>
      ) : null}
    </Shell>
  );
}
