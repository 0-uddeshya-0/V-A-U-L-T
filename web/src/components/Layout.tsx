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
          <NavLink key={l.to} to={l.to} end={l.to === "/"} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            {l.label}
          </NavLink>
        ))}
        <p className="footer-note">Validated units only reach agents.</p>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
