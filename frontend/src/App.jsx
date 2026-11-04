import { Navigate } from "react-router-dom";
import { useAuth } from "./auth";
import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import { Forgot, Login, Register } from "./pages/AuthPages";
import { Book, ProviderPage, ServiceDetail, Services } from "./pages/Catalog";
import CustomerDash from "./pages/CustomerDash";
import ProviderDash from "./pages/ProviderDash";
import TechDash from "./pages/TechDash";
import AdminDash from "./pages/AdminDash";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="grid min-h-screen place-items-center font-display text-3xl">Loading HomeServe…</div>;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`} replace />;
  return children;
}

function Workspace() {
  const { user } = useAuth();
  if (user.role === "admin") return <AdminDash />;
  if (user.role === "provider") return <ProviderDash />;
  if (user.role === "technician") return <TechDash />;
  return <CustomerDash />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot" element={<Forgot />} />
      <Route path="/services" element={<Services />} />
      <Route path="/services/:id" element={<ServiceDetail />} />
      <Route path="/providers/:id" element={<ProviderPage />} />
      <Route path="/book/:offerId" element={<Protected><Book /></Protected>} />
      <Route path="/app" element={<Protected><Workspace /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
