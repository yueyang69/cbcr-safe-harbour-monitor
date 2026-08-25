import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { listAllCompanies } from '../api/endpoints'
import { SessionContext } from '../session'
import type { Company, UserRole } from '../types'

const roleLabels: Record<UserRole, string> = { hq: 'Group HQ', subsidiary: 'Subsidiary', reviewer: 'Reviewer', admin: 'Admin' }

export function AppLayout() {
  const navigate = useNavigate()
  const [role, setRole] = useState<UserRole>((localStorage.getItem('cbcr-role') as UserRole) || 'hq')
  const [entityId, setEntityId] = useState<string>(localStorage.getItem('cbcr-entity') || '')
  const [entities, setEntities] = useState<Company[]>([])
  const isSubsidiary = role === 'subsidiary'
  // Admin is a real login (POST /auth/login sets this flag); every other role is
  // still switched via the demo role picker. The flag makes "admin" trustworthy
  // enough to gate the demo — it is not a security boundary.
  const isAdminLoggedIn = role === 'admin' && localStorage.getItem('cbcr-admin-auth') === '1'

  useEffect(() => { localStorage.setItem('cbcr-role', role) }, [role])
  useEffect(() => { localStorage.setItem('cbcr-entity', entityId) }, [entityId])

  // If something leaves cbcr-role=admin without a real login (e.g. stale state),
  // route to the sign-in page instead of silently granting admin.
  useEffect(() => {
    if (role === 'admin' && !isAdminLoggedIn) {
      navigate('/login', { replace: true })
    }
  }, [role, isAdminLoggedIn, navigate])

  // The entity picker enumerates all entities with a one-off HQ-override request
  // (demo identity switching). Backend permissions stay strict — a subsidiary can
  // only ever read its own entity.
  useEffect(() => {
    if (!isSubsidiary) { setEntities([]); return }
    listAllCompanies().then(setEntities).catch(() => setEntities([]))
  }, [isSubsidiary])

  const logout = () => {
    localStorage.removeItem('cbcr-role')
    localStorage.removeItem('cbcr-admin-auth')
    localStorage.removeItem('cbcr-entity')
    setRole('hq')
    navigate('/dashboard')
  }

  const changeRole = (value: string) => {
    if (value === 'login') { navigate('/login'); return }
    const next = value as UserRole
    // Write synchronously so pages that read localStorage (e.g. the API client)
    // see the new identity on their very next render.
    localStorage.setItem('cbcr-role', next)
    setRole(next)
    navigate(next === 'subsidiary' ? '/data-entry' : '/dashboard')
  }

  const changeEntity = (value: string) => {
    localStorage.setItem('cbcr-entity', value)
    setEntityId(value)
  }

  return <SessionContext.Provider value={{ role, entityId }}>
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand-lockup"><div className="brand-mark" aria-hidden="true">C</div><div><strong>CbCR / SH</strong><span>Risk warning system</span></div></div>
        <div className="sidebar-section-label">Workspace</div>
        <nav className="nav-list">
          {!isSubsidiary && <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">▦</span>Dashboard</NavLink>}
          <NavLink to="/data-entry" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">＋</span>Data entry</NavLink>
          {(role === 'hq' || role === 'admin') && <NavLink to="/approvals" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span aria-hidden="true">✓</span>Approvals</NavLink>}
        </nav>
        <div className="sidebar-footer"><span className="secure-dot" />API connected<div className="sidebar-caption">Transitional Safe Harbour<br />MVP workspace</div></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div className="mobile-brand"><div className="brand-mark" aria-hidden="true">C</div><strong>CbCR / SH</strong></div><div className="topbar-actions">{isAdminLoggedIn ? <div className="admin-session"><span className="admin-session-label">Signed in as</span><span className="admin-session-user">admin</span><button className="button button-secondary admin-logout" onClick={logout}>Sign out</button></div> : <label className="role-picker">View as<select value={role} onChange={(event) => changeRole(event.target.value)} aria-label="Current user role">{Object.entries(roleLabels).filter(([value]) => value !== 'admin').map(([value, label]) => <option key={value} value={value}>{label}</option>)}<option value="login">Admin (sign in)…</option></select></label>}{isSubsidiary && <label className="role-picker">Entity<select value={entityId} onChange={(event) => changeEntity(event.target.value)} aria-label="Current entity"><option value="">Select entity</option>{entities.map((entity) => <option key={entity.id} value={entity.id}>{entity.name}</option>)}</select></label>}<button className="avatar" aria-label={`Signed in as ${roleLabels[role]}`}>{roleLabels[role]}</button></div></header>
        <Outlet />
      </main>
    </div>
  </SessionContext.Provider>
}
