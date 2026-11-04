import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { ErrorNote, Logo, btn, btnClay, btnGhost, field } from "../ui";

const DEMOS = [
  ["priya@homeserve.test", "Customer · Priya"],
  ["kiran@homeserve.test", "Provider · Kiran"],
  ["amit@homeserve.test", "Technician · Amit"],
  ["admin@homeserve.test", "Admin · Ananya"],
];

function Frame({ title, lede, children }) {
  return (
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-8 px-4 py-8 sm:px-5 md:grid-cols-2 md:gap-10 md:py-10">
      <div>
        <Logo />
        <h1 className="mt-6 font-display text-4xl leading-tight sm:mt-8 sm:text-5xl">{title}</h1>
        <p className="mt-4 max-w-md text-moss">{lede}</p>
      </div>
      <div className="rounded-[28px] border border-line bg-paper p-4 shadow-card sm:rounded-[32px] sm:p-6">{children}</div>
    </div>
  );
}

export function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("priya@homeserve.test");
  const [password, setPassword] = useState("Demo@1234");
  const [error, setError] = useState("");
  const next = params.get("next") || "/app";

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate(next);
    } catch (err) {
      setError(err.message);
    }
  }

  async function enter(event, nextEmail) {
    setEmail(nextEmail);
    setPassword("Demo@1234");
    setError("");
    try {
      await login(nextEmail, "Demo@1234");
      navigate(next);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (user) navigate(next);
  }, [user]);

  return (
    <Frame title="Welcome back." lede="Same password for every demo account: Demo@1234. Pick a role and the workspace opens.">
      <form className="grid gap-3" onSubmit={submit}>
        <input className={field} type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" required />
        <input className={field} type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" required />
        <ErrorNote error={error} />
        <button className={btnClay}>Log in</button>
      </form>
      <div className="mt-4 grid gap-2">
        {DEMOS.map(([mail, label]) => (
          <button key={mail} className={btnGhost} onClick={(event) => enter(event, mail)}>{label}</button>
        ))}
      </div>
      <p className="mt-4 text-sm text-moss">New here? <Link className="font-semibold text-forest" to="/register">Create an account</Link> · <Link className="font-semibold text-forest" to="/forgot">Forgot password</Link></p>
    </Frame>
  );
}

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [providers, setProviders] = useState([]);
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "", role: "customer", business_name: "", bio: "", city: "Ahmedabad", pincode: "380015", provider_id: "", skills: "" });
  const [error, setError] = useState("");

  function set(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function loadProviders() {
    const rows = await api.get("/api/providers");
    setProviders(rows);
    if (rows[0]) set("provider_id", rows[0].id);
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const payload = { ...form, provider_id: form.provider_id ? Number(form.provider_id) : null, experience_years: 1 };
      await register(payload);
      navigate("/app");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Frame title="Create your login." lede="Customers book. Providers list services after admin verification. Technicians join an approved crew.">
      <form className="grid gap-3" onSubmit={submit}>
        <div className="grid grid-cols-1 gap-2 min-[420px]:grid-cols-3">
          {["customer", "provider", "technician"].map((role) => (
            <button type="button" key={role} className={form.role === role ? btn : btnGhost} onClick={() => { set("role", role); if (role === "technician" && providers.length === 0) loadProviders(); }}>{role}</button>
          ))}
        </div>
        <input className={field} placeholder="Full name" value={form.full_name} onChange={(event) => set("full_name", event.target.value)} required />
        <input className={field} type="email" placeholder="Email" value={form.email} onChange={(event) => set("email", event.target.value)} required />
        <input className={field} placeholder="10-digit mobile" value={form.phone} onChange={(event) => set("phone", event.target.value)} />
        <input className={field} type="password" placeholder="Password, 8+ with a letter and number" value={form.password} onChange={(event) => set("password", event.target.value)} required />
        {form.role === "provider" ? (
          <>
            <input className={field} placeholder="Business name" value={form.business_name} onChange={(event) => set("business_name", event.target.value)} required />
            <textarea className={field} rows="3" placeholder="Short bio" value={form.bio} onChange={(event) => set("bio", event.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <input className={field} placeholder="City" value={form.city} onChange={(event) => set("city", event.target.value)} />
              <input className={field} placeholder="Pincode" value={form.pincode} onChange={(event) => set("pincode", event.target.value)} />
            </div>
          </>
        ) : null}
        {form.role === "technician" ? (
          <>
            <select className={field} value={form.provider_id} onChange={(event) => set("provider_id", event.target.value)}>
              {providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.business_name}</option>)}
            </select>
            <input className={field} placeholder="Skills" value={form.skills} onChange={(event) => set("skills", event.target.value)} />
          </>
        ) : null}
        <ErrorNote error={error} />
        <button className={btnClay}>Create account</button>
      </form>
      <p className="mt-4 text-sm text-moss">Already registered? <Link className="font-semibold text-forest" to="/login">Log in</Link></p>
    </Frame>
  );
}

export function Forgot() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [demo, setDemo] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function ask(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api.post("/api/auth/forgot", { email });
      setMessage(data.message);
      setDemo(data.demo_reset_code || "");
    } catch (err) {
      setError(err.message);
    }
  }

  async function reset(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api.post("/api/auth/reset", { email, code: code || demo, password });
      setMessage(data.message);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Frame title="Reset the password." lede="Email delivery is optional in this build. In demo mode the reset code is shown here, valid for 15 minutes.">
      <form className="grid gap-3" onSubmit={ask}>
        <input className={field} type="email" placeholder="Account email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <button className={btn}>Send reset code</button>
      </form>
      {demo ? <p className="mt-3 rounded-2xl bg-leaf px-3 py-2 text-sm">Demo code: <strong>{demo}</strong></p> : null}
      <form className="mt-4 grid gap-3" onSubmit={reset}>
        <input className={field} placeholder="Reset code" value={code || demo} onChange={(event) => setCode(event.target.value)} />
        <input className={field} type="password" placeholder="New password" value={password} onChange={(event) => setPassword(event.target.value)} />
        <button className={btnClay}>Update password</button>
      </form>
      <ErrorNote error={error} />
      {message ? <p className="mt-3 text-sm text-forest">{message}</p> : null}
      <p className="mt-4 text-sm"><Link className="font-semibold text-forest" to="/login">Back to login</Link></p>
    </Frame>
  );
}
