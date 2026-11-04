import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, prettyDate } from "../api";
import { BookingPanel } from "../booking";
import { useAuth } from "../auth";
import { ErrorNote, Shell, Stat, StatusPill, btn, field } from "../ui";

const TABS = [
  { id: "jobs", label: "Jobs" },
  { id: "history", label: "History" },
  { id: "profile", label: "Profile" },
];

export default function TechDash() {
  const { user, refresh } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "jobs";
  const focus = params.get("id");
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [passwords, setPasswords] = useState({ old_password: "", new_password: "" });

  async function load() {
    try {
      setStats(await api.get("/api/technician/dashboard"));
      setJobs(await api.get("/api/technician/jobs"));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, [tab]);
  const visible = tab === "history" ? jobs.filter((job) => ["Completed", "Cancelled", "Rejected"].includes(job.status)) : jobs.filter((job) => !["Completed", "Cancelled", "Rejected"].includes(job.status));
  const selected = jobs.find((job) => String(job.id) === String(focus));

  return (
    <Shell title="Your jobs" tabs={TABS} tab={tab} setTab={(next) => setParams({ tab: next })}>
      <ErrorNote error={error} />
      {stats ? <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3"><Stat label="Active" value={stats.active} /><Stat label="Completed" value={stats.completed} /><Stat label="All assigned" value={stats.total} hint={stats.skills} /></div> : null}
      {tab !== "profile" ? (
        <div className="grid gap-3">
          {selected ? <BookingPanel booking={selected} role="technician" onChange={load} /> : null}
          {visible.map((job) => (
            <button key={job.id} onClick={() => setParams({ tab, id: job.id })} className="rounded-3xl border border-line bg-paper px-4 py-3 text-left">
              <div className="flex flex-wrap items-center justify-between gap-2"><strong className="min-w-0 break-words">{job.service_name}</strong><StatusPill status={job.status} /></div>
              <p className="break-words text-sm text-moss">{prettyDate(job.scheduled_date)} {job.scheduled_time} · {job.address}</p>
              <p className="text-sm">{job.customer_name} · {job.customer_phone}</p>
            </button>
          ))}
        </div>
      ) : (
        <div className="grid max-w-lg gap-3">
          <p className="text-sm text-moss">You work with {user?.business_name}. Skills: {user?.skills}</p>
          <input className={field} value={user?.full_name || ""} onChange={() => {}} readOnly />
          <input className={field} type="password" placeholder="Current password" value={passwords.old_password} onChange={(event) => setPasswords({ ...passwords, old_password: event.target.value })} />
          <input className={field} type="password" placeholder="New password" value={passwords.new_password} onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })} />
          <button className={btn} onClick={async () => { await api.post("/api/auth/change-password", passwords); setPasswords({ old_password: "", new_password: "" }); refresh(); }}>Change password</button>
        </div>
      )}
    </Shell>
  );
}
