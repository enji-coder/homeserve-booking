import { useEffect, useState } from "react";
import { api, inr, prettyDate } from "./api";
import { ErrorNote, StatusPill, Timeline, btn, btnClay, btnGhost, field } from "./ui";

export function BookingPanel({ booking, role, techs = [], onChange }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [remarks, setRemarks] = useState("");
  const [techId, setTechId] = useState(techs[0]?.id || "");
  const [date, setDate] = useState(booking.scheduled_date);
  const [slots, setSlots] = useState([]);
  const [time, setTime] = useState("");
  const [payOpen, setPayOpen] = useState(null);
  const [card, setCard] = useState("4111 1111 1111 1111");
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");

  useEffect(() => {
    setTechId(techs[0]?.id || "");
  }, [techs, booking.id]);

  useEffect(() => {
    if (!date) return;
    api.get(`/api/slots?provider_id=${booking.provider_id}&scheduled_date=${date}`).then(setSlots).catch(() => setSlots([]));
  }, [date, booking.provider_id]);

  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
      if (onChange) await onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function pay(mode) {
    const checkout = await api.post("/api/payments/checkout", { booking_id: booking.id, mode });
    setPayOpen(checkout);
  }

  async function confirmPay() {
    await run(async () => {
      await api.post("/api/payments/verify", {
        booking_id: booking.id,
        order_id: payOpen.order_id,
        outcome: "success",
        test_card: card,
      });
      setPayOpen(null);
    });
  }

  async function attach(kind, file) {
    if (!file) return;
    await run(async () => {
      const uploaded = await api.upload(file);
      await api.post(`/api/bookings/${booking.id}/images`, { url: uploaded.url, kind });
    });
  }

  return (
    <article className="rounded-[28px] border border-line bg-paper p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-moss">{booking.booking_code}</p>
          <h3 className="mt-1 break-words font-display text-2xl sm:text-3xl">{booking.service_name}</h3>
          <p className="mt-1 text-sm text-moss">{prettyDate(booking.scheduled_date)} · {booking.scheduled_time} · {booking.city}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill status={booking.status} />
          <StatusPill status={booking.payment_status} />
        </div>
      </div>
      <div className="mt-4"><Timeline status={booking.status} /></div>
      <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
        <p><span className="text-moss">Customer · </span>{booking.customer_name} · {booking.customer_phone}</p>
        <p><span className="text-moss">Provider · </span>{booking.provider_name} · {booking.provider_phone}</p>
        <p><span className="text-moss">Address · </span>{booking.address}</p>
        <p><span className="text-moss">Technician · </span>{booking.technician_name || "Not assigned"} {booking.technician_phone}</p>
      </div>
      {booking.problem_note ? <p className="mt-3 rounded-2xl bg-white px-3 py-2 text-sm">{booking.problem_note}</p> : null}
      {booking.remarks ? <p className="mt-2 text-sm text-moss">Crew note: {booking.remarks}</p> : null}
      {booking.cancel_reason ? <p className="mt-2 text-sm text-clay">{booking.cancel_reason}</p> : null}
      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        <span>Subtotal {inr(booking.subtotal)}</span>
        <span>Discount {inr(booking.discount)}</span>
        <span>GST {inr(booking.gst)}</span>
        <span className="font-semibold">Total {inr(booking.total)}</span>
        <span>Paid {inr(booking.amount_paid)}</span>
        <span>Balance {inr(booking.balance)}</span>
      </div>
      {booking.images?.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {booking.images.map((image) => (
            <a key={image.id} href={image.url} target="_blank" rel="noreferrer" className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-forest">{image.kind}</a>
          ))}
        </div>
      ) : null}
      {booking.review ? (
        <p className="mt-4 rounded-2xl bg-leaf px-3 py-2 text-sm">{booking.review.rating}/5 · {booking.review.comment} {booking.review.provider_response ? `· Reply: ${booking.review.provider_response}` : ""}</p>
      ) : null}
      <ErrorNote error={error} />

      <div className="mt-4 flex flex-wrap gap-2">
        {role === "customer" && ["Pending", "Confirmed", "Provider Assigned"].includes(booking.status) ? (
          <button className={btnGhost} disabled={busy} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/cancel`, { reason }))}>Cancel</button>
        ) : null}
        {role === "provider" && booking.status === "Pending" ? (
          <>
            <button className={btn} disabled={busy} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/accept`))}>Accept</button>
            <button className={btnGhost} disabled={busy} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/reject`, { reason }))}>Reject</button>
          </>
        ) : null}
        {role === "technician" && booking.status === "Provider Assigned" && !booking.job_accepted ? (
          <button className={btn} disabled={busy} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/accept-job`))}>Accept job</button>
        ) : null}
        {((role === "technician" && booking.job_accepted) || role === "provider") && booking.status === "Provider Assigned" ? (
          <button className={btn} disabled={busy} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/arrive`))}>Mark arrival</button>
        ) : null}
        {(role === "technician" || role === "provider") && booking.status === "In Progress" ? (
          <button className={btnClay} disabled={busy || remarks.trim().length < 3} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/complete`, { remarks }))}>Complete job</button>
        ) : null}
        {role === "customer" && booking.balance > 0 && !["Cancelled", "Rejected"].includes(booking.status) ? (
          <>
            <button className={btnClay} disabled={busy} onClick={() => pay("full")}>Pay {inr(booking.balance)}</button>
            <button className={btnGhost} disabled={busy} onClick={() => pay("advance")}>Pay 30% advance</button>
          </>
        ) : null}
      </div>

      {role === "customer" && ["Pending", "Confirmed", "Provider Assigned"].includes(booking.status) ? (
        <div className="mt-4 grid gap-2 md:grid-cols-[1fr_1fr_auto]">
          <input className={field} type="date" min={new Date().toISOString().slice(0, 10)} value={date} onChange={(event) => setDate(event.target.value)} />
          <select className={field} value={time} onChange={(event) => setTime(event.target.value)}>
            <option value="">New time</option>
            {slots.filter((slot) => slot.available).map((slot) => <option key={slot.time}>{slot.time}</option>)}
          </select>
          <button className={btnGhost} disabled={!time || busy} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/reschedule`, { scheduled_date: date, scheduled_time: time }))}>Reschedule</button>
        </div>
      ) : null}

      {role === "provider" && ["Confirmed", "Provider Assigned"].includes(booking.status) ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <select className={field} value={techId} onChange={(event) => setTechId(event.target.value)}>
            {techs.map((tech) => <option key={tech.id} value={tech.id}>{tech.name} · {tech.skills}</option>)}
          </select>
          <button className={btn} disabled={!techId || busy} onClick={() => run(() => api.post(`/api/bookings/${booking.id}/assign`, { technician_id: Number(techId) }))}>Assign technician</button>
        </div>
      ) : null}

      {(role === "customer" && ["Pending", "Confirmed", "Provider Assigned"].includes(booking.status)) || (role === "provider" && booking.status === "Pending") ? (
        <input className={`${field} mt-3`} placeholder={role === "customer" ? "Cancellation note" : "Reason if you reject"} value={reason} onChange={(event) => setReason(event.target.value)} />
      ) : null}
      {(role === "technician" || role === "provider") && booking.status === "In Progress" ? (
        <textarea className={`${field} mt-3`} rows="2" placeholder="What was done?" value={remarks} onChange={(event) => setRemarks(event.target.value)} />
      ) : null}

      <div className="mt-3 flex flex-col gap-3 text-sm sm:flex-row sm:flex-wrap">
        {role === "customer" ? <label>Problem photo <input type="file" accept="image/*" onChange={(event) => attach("problem", event.target.files?.[0])} /></label> : null}
        {role === "technician" || role === "provider" ? (
          <>
            <label>Before <input type="file" accept="image/*" onChange={(event) => attach("before", event.target.files?.[0])} /></label>
            <label>After <input type="file" accept="image/*" onChange={(event) => attach("after", event.target.files?.[0])} /></label>
          </>
        ) : null}
      </div>

      {role === "customer" && booking.status === "Completed" && !booking.review ? (
        <div className="mt-4 grid gap-2 md:grid-cols-[120px_1fr_auto]">
          <select className={field} value={rating} onChange={(event) => setRating(Number(event.target.value))}>
            {[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>{value} stars</option>)}
          </select>
          <input className={field} placeholder="How was the visit?" value={comment} onChange={(event) => setComment(event.target.value)} />
          <button className={btn} disabled={busy} onClick={() => run(() => api.post("/api/reviews", { booking_id: booking.id, rating, comment }))}>Submit review</button>
        </div>
      ) : null}

      {payOpen ? (
        <div className="mt-4 rounded-3xl bg-ink p-4 text-cream">
          <p className="text-xs uppercase tracking-[0.16em] text-white/50">Razorpay test mode · {payOpen.order_id}</p>
          <p className="mt-2 font-display text-3xl">{inr(payOpen.amount)}</p>
          <p className="mt-1 text-sm text-white/70">Test card 4111 1111 1111 1111 · any future expiry · CVV 123. Card 4000 0000 0000 0002 fails.</p>
          <input className={`${field} mt-3`} value={card} onChange={(event) => setCard(event.target.value)} />
          <div className="mt-3 flex flex-wrap gap-2">
            <button className={btnClay} disabled={busy} onClick={confirmPay}>Pay now</button>
            <button className={btnGhost} onClick={() => setPayOpen(null)}>Close</button>
          </div>
        </div>
      ) : null}
    </article>
  );
}
