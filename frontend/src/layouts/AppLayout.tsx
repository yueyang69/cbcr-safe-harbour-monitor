import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import type { UserRole } from '../types'

const roleLabels: Record<UserRole, string> = { hq: 'Group HQ', subsidiary: 'Subsidiary', reviewer: 'Reviewer' }

export function AppLayout() {
  const navigate = useNavigate()
  const [role, setRole] = useState<UserRole>((localStorage.getItem('cbcr-role') as UserRole) || 'hq')

  useEffect(() => { localStorage.setItem('cbcr-role', role) }, [role])

  return <div className="app-shell">
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="brand-lockup"><div className="brand-mark" aria-hidden="true">C</div><div><strong>CbCR / SH</strong><span>Risk warning system</span></div></div>
      <div className="sidebar-section-label">Workspace</div>
      <nav className="nav-list">
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">▦</span>Dashboard</NavLink>
        <NavLink to="/data-entry" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">＋</span>Data entry</NavLink>
      </nav>
      <div className="sidebar-footer"><span className="secure-dot" />API connected<div className="sidebar-caption">Transitional Safe Harbour<br />MVP workspace</div></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div className="mobile-brand"><div className="brand-mark" aria-hidden="true">C</div><strong>CbCR / SH</strong></div><div className="topbar-actions"><label className="role-picker">View as<select value={role} onChange={(event) => { const next = event.target.value as UserRole; setRole(next); navigate(next === 'subsidiary' ? '/data-entry' : '/dashboard') }} aria-label="Current user role">{Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><button className="avatar" aria-label={`Signed in as ${roleLabels[role]}`}>HQ</button></div></header>
      <Outlet />
    </main>
  </div>
}
