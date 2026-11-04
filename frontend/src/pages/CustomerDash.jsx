import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, downloadBlob, inr, prettyDate } from "../api";
import { BookingPanel } from "../booking";
import { useAuth } from "../auth";
import { Empty, ErrorNote, Shell, Stat, StatusPill, btn, btnClay, btnGhost, field } from "../ui";

const TABS = [
  ["overview", "Overview"],
  ["bookings", "Bookings"],
  ["addresses", "Addresses"],
  ["favorites", "Favorites"],
  ["payments", "Payments"],
  ["complaints", "Complaints"],
  ["profile", "Profile"],
].map(([id, label]) => ({ id, label }));

export default function CustomerDash() {
  const { user, refresh } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "overview";
  const focus = params.get("id");
  const [dash, setDash] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [addresses, setAddresses] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [payments, setPayments] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [error, setError] = useState("");
  const [address, setAddress] = useState({ label: "Home", line1: "", city: "Ahmedabad", pincode: "", is_default: false });
  const [complaint, setComplaint] = useState({ subject: "", description: "", booking_id: "" });
  const [profile, setProfile] = useState({ full_name: user?.full_name || "", phone: user?.phone || "" });
  const [passwords, setPasswords] = useState({ old_password: "", new_password: "" });

  function setTab(next) {
    setParams(next === "overview" ? {} : { tab: next });
  }

  async function load() {
    setError("");
    try {
      if (tab === "overview") setDash(await api.get("/api/customer/dashboard"));
      if (tab === "bookings" || tab === "overview") setBookings((await api.get("/api/bookings?page_size=50")).items);
      if (tab === "addresses") setAddresses(await api.get("/api/addresses"));
      if (tab === "favorites") setFavorites(await api.get("/api/favorites"));
      if (tab === "payments") setPayments(await api.get("/api/payments"));
      if (tab === "complaints") {
        setComplaints(await api.get("/api/complaints"));
        setBookings((await api.get("/api/bookings?page_size=50")).items);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, [tab]);

  async function saveAddress(event) {
    event.preventDefault();
    await api.post("/api/addresses", address);
    setAddress({ label: "Home", line1: "", city: "Ahmedabad", pincode: "", is_default: false });
    load();
  }

  async function saveComplaint(event) {
    event.preventDefault();
    await api.post("/api/complaints", { ...complaint, booking_id: complaint.booking_id ? Number(complaint.booking_id) : null });
    setComplaint({ subject: "", description: "", booking_id: "" });
    load();
  }

  async function receipt(bookingId, code) {
    const data = await api.get(`/api/bookings/${bookingId}/invoice`);
    const lines = (data.invoices || []).map((row) => `<tr><td>${row.invoice_number}</td><td>${row.issued_on}</td><td>${row.txn_id}</td><td>₹${row.amount}</td></tr>`).join("");
    const html = `<!doctype html><meta charset="utf-8"><title>${code}</title><body style="font-family:Georgia,serif;padding:32px"><h1>HomeServe Technologies</h1><p>Receipt for ${code}</p><p>${data.service_name} · ${data.scheduled_date} ${data.scheduled_time}</p><p>Subtotal ₹${data.subtotal} · Discount ₹${data.discount} · GST ₹${data.gst} · Total ₹${data.total}</p><table cellpadding="8">${lines}</table></body>`;
    downloadBlob(new Blob([html], { type: "text/html" }), `${code}-receipt.html`);
  }

  const selected = bookings.find((item) => String(item.id) === String(focus));

  return (
    <Shell title={user?.full_name?.split(" ")[0] ? `${user.full_name.split(" ")[0]}'s home` : "Your home"} tabs={TABS} tab={tab} setTab={setTab}>
      <ErrorNote error={error} />
      {tab === "overview" && dash ? (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Upcoming" value={dash.upcoming.length} />
            <Stat label="Past visits" value={dash.previous_count} />
            <Stat label="To pay" value={dash.pending_payments} />
            <Stat label="Saved crews" value={dash.favorites} />
          </div>
          <Link to="/services" className={`${btnClay} w-fit`}>Book a service</Link>
          <div className="grid gap-3">
            {dash.recent.map((booking) => (
              <button key={booking.id} onClick={() => setParams({ tab: "bookings", id: booking.id })} className="flex flex-wrap items-center justify-between gap-2 rounded-3xl border border-line bg-paper px-4 py-3 text-left">
                <span className="min-w-0 flex-1 break-words"><strong>{booking.service_name}</strong><br /><span className="text-sm text-moss">{prettyDate(booking.scheduled_date)} · {booking.provider_name}</span></span>
                <StatusPill status={booking.status} />
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {tab === "bookings" ? (
        <div className="grid gap-4">
          {selected ? <BookingPanel booking={selected} role="customer" onChange={load} /> : null}
          {bookings.length === 0 ? <Empty title="No bookings yet" body="Pick a service and a free hour." action={<Link className={btnClay} to="/services">Browse services</Link>} /> : bookings.map((booking) => (
            <button key={booking.id} onClick={() => setParams({ tab: "bookings", id: booking.id })} className="flex flex-wrap items-center justify-between gap-2 rounded-3xl border border-line bg-white px-4 py-3 text-left">
              <span className="min-w-0 flex-1 break-words">{booking.booking_code} · {booking.service_name} · {prettyDate(booking.scheduled_date)} {booking.scheduled_time}</span>
              <StatusPill status={booking.status} />
            </button>
          ))}
        </div>
      ) : null}
      {tab === "addresses" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <form className="grid gap-2 rounded-3xl border border-line bg-paper p-4" onSubmit={saveAddress}>
            <input className={field} placeholder="Label" value={address.label} onChange={(event) => setAddress({ ...address, label: event.target.value })} />
            <input className={field} placeholder="Address" value={address.line1} onChange={(event) => setAddress({ ...address, line1: event.target.value })} required />
            <input className={field} placeholder="City" value={address.city} onChange={(event) => setAddress({ ...address, city: event.target.value })} required />
            <input className={field} placeholder="Pincode" value={address.pincode} onChange={(event) => setAddress({ ...address, pincode: event.target.value })} />
            <label className="text-sm"><input type="checkbox" checked={address.is_default} onChange={(event) => setAddress({ ...address, is_default: event.target.checked })} /> Default</label>
            <button className={btn}>Save address</button>
          </form>
          <div className="grid gap-2">
            {addresses.map((item) => (
              <article key={item.id} className="rounded-3xl border border-line bg-paper p-4">
                <p className="font-semibold">{item.label} {item.is_default ? "· default" : ""}</p>
                <p className="text-sm text-moss">{item.line1}, {item.city} {item.pincode}</p>
                <button className={`${btnGhost} mt-2`} onClick={async () => { await api.del(`/api/addresses/${item.id}`); load(); }}>Remove</button>
              </article>
            ))}
          </div>
        </div>
      ) : null}
      {tab === "favorites" ? (
        <div className="grid gap-3 md:grid-cols-2">
          {favorites.length === 0 ? <Empty title="No saved crews" body="Open a provider and save them for next time." /> : favorites.map((provider) => (
            <Link key={provider.id} to={`/providers/${provider.id}`} className="rounded-3xl border border-line bg-paper p-4">
              <h3 className="font-display text-2xl">{provider.business_name}</h3>
              <p className="text-sm text-moss">{provider.rating_avg} ★ · from {inr(provider.starting_price)}</p>
            </Link>
          ))}
        </div>
      ) : null}
      {tab === "payments" ? (
        <div className="overflow-x-auto rounded-3xl border border-line bg-paper">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-moss"><tr><th className="px-4 py-3">Booking</th><th>Amount</th><th>Status</th><th>Receipt</th></tr></thead>
            <tbody>
              {payments.map((payment) => (
                <tr key={payment.id} className="border-t border-line">
                  <td className="px-4 py-3">{payment.booking_code}</td>
                  <td>{inr(payment.amount)}</td>
                  <td><StatusPill status={payment.status} /></td>
                  <td>{payment.invoice_number ? <button className="font-semibold text-forest" onClick={() => receipt(payment.booking_id, payment.booking_code)}>Download</button> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {tab === "complaints" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <form className="grid gap-2" onSubmit={saveComplaint}>
            <input className={field} placeholder="Subject" value={complaint.subject} onChange={(event) => setComplaint({ ...complaint, subject: event.target.value })} required />
            <textarea className={field} rows="4" placeholder="What happened?" value={complaint.description} onChange={(event) => setComplaint({ ...complaint, description: event.target.value })} />
            <select className={field} value={complaint.booking_id} onChange={(event) => setComplaint({ ...complaint, booking_id: event.target.value })}>
              <option value="">Related booking, optional</option>
              {bookings.map((booking) => <option key={booking.id} value={booking.id}>{booking.booking_code}</option>)}
            </select>
            <button className={btn}>Raise complaint</button>
          </form>
          <div className="grid gap-2">
            {complaints.map((item) => (
              <article key={item.id} className="rounded-3xl border border-line bg-paper p-4">
                <div className="flex flex-wrap items-start justify-between gap-2"><strong className="min-w-0 break-words">{item.subject}</strong><StatusPill status={item.status} /></div>
                <p className="mt-1 text-sm text-moss">{item.description}</p>
                {item.admin_note ? <p className="mt-2 text-sm">Admin: {item.admin_note}</p> : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}
      {tab === "profile" ? (
        <div className="grid max-w-lg gap-3">
          <input className={field} value={profile.full_name} onChange={(event) => setProfile({ ...profile, full_name: event.target.value })} />
          <input className={field} value={profile.phone} onChange={(event) => setProfile({ ...profile, phone: event.target.value })} />
          <button className={btn} onClick={async () => { await api.patch("/api/profile", profile); refresh(); }}>Save profile</button>
          <input className={field} type="password" placeholder="Current password" value={passwords.old_password} onChange={(event) => setPasswords({ ...passwords, old_password: event.target.value })} />
          <input className={field} type="password" placeholder="New password" value={passwords.new_password} onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })} />
          <button className={btnGhost} onClick={async () => { await api.post("/api/auth/change-password", passwords); setPasswords({ old_password: "", new_password: "" }); }}>Change password</button>
        </div>
      ) : null}
    </Shell>
  );
}
