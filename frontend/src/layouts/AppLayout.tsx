import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { listAllCompanies } from '../api/endpoints'
import type { Company, UserRole } from '../types'

const roleLabels: Record<UserRole, string> = { hq: 'Group HQ', subsidiary: 'Subsidiary', reviewer: 'Reviewer', admin: 'Admin' }

export function AppLayout() {
  const navigate = useNavigate()
  const [role, setRole] = useState<UserRole>((localStorage.getItem('cbcr-role') as UserRole) || 'hq')
  const [entityId, setEntityId] = useState<string>(localStorage.getItem('cbcr-entity') || '')
  const [entities, setEntities] = useState<Company[]>([])
  const isSubsidiary = role === 'subsidiary'

  useEffect(() => { localStorage.setItem('cbcr-role', role) }, [role])
  useEffect(() => { localStorage.setItem('cbcr-entity', entityId) }, [entityId])

  // The entity picker enumerates all entities with a one-off HQ-override request
  // (demo identity switching). Backend permissions stay strict — a subsidiary can
  // only ever read its own entity.
  useEffect(() => {
    if (!isSubsidiary) { setEntities([]); return }
    listAllCompanies().then(setEntities).catch(() => setEntities([]))
  }, [isSubsidiary])

  return <div className="app-shell">
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="brand-lockup"><div className="brand-mark" aria-hidden="true">C</div><div><strong>CbCR / SH</strong><span>Risk warning system</span></div></div>
      <div className="sidebar-section-label">Workspace</div>
      <nav className="nav-list">
        {!isSubsidiary && <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">▦</span>Dashboard</NavLink>}
        <NavLink to="/data-entry" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">＋</span>Data entry</NavLink>
        {role !== 'reviewer' && <NavLink to="/csv-upload" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">⇪</span>CSV upload</NavLink>}
        {(role === 'hq' || role === 'admin') && <NavLink to="/approvals" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">✓</span>Approvals</NavLink>}
      </nav>
      <div className="sidebar-footer"><span className="secure-dot" />API connected<div className="sidebar-caption">Transitional Safe Harbour<br />MVP workspace</div></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div className="mobile-brand"><div className="brand-mark" aria-hidden="true">C</div><strong>CbCR / SH</strong></div><div className="topbar-actions"><label className="role-picker">View as<select value={role} onChange={(event) => { const next = event.target.value as UserRole; setRole(next); navigate(next === 'subsidiary' ? '/data-entry' : '/dashboard') }} aria-label="Current user role">{Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>{isSubsidiary && <label className="role-picker">Entity<select value={entityId} onChange={(event) => setEntityId(event.target.value)} aria-label="Current entity"><option value="">Select entity</option>{entities.map((entity) => <option key={entity.id} value={entity.id}>{entity.name}</option>)}</select></label>}<button className="avatar" aria-label={`Signed in as ${roleLabels[role]}`}>{roleLabels[role]}</button></div></header>
      <Outlet />
    </main>
  </div>
}
