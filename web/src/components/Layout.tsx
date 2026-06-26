import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Overview" },
  { to: "/ingest", label: "Ingest" },
  { to: "/query", label: "Query" },
  { to: "/quarantine", label: "Quarantine" },
  { to: "/gaps", label: "Gaps" },
  { to: "/settings", label: "Settings" },
];

export function Layout() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          V.A.U.L.T
          <span>Knowledge OS</span>
        </div>
        {links.map((l) => (
          <NavLink key={l.to} to={`/app${l.to === "/" ? "" : l.to}`} end={l.to === "/"} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            {l.label}
          </NavLink>
        ))}
        <p className="footer-note">
          <a href="/" style={{ color: "var(--muted)" }}>← Landing</a>
        </p>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
