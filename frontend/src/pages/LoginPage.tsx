import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../api/endpoints'

export function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const result = await login(username.trim(), password)
      // Demo-level session: mark the admin auth flag so the layout recognises
      // a real admin session (as opposed to the demo role picker).
      localStorage.setItem('cbcr-role', result.role)
      localStorage.setItem('cbcr-admin-auth', '1')
      localStorage.removeItem('cbcr-entity')
      navigate('/approvals')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="page-wrap login-page">
    <div className="login-card">
      <div className="login-brand"><div className="brand-mark" aria-hidden="true">C</div><div><strong>CbCR / SH</strong><span>Risk warning system</span></div></div>
      <div className="page-heading login-heading"><div><p className="eyebrow">Administrator access</p><h1>Sign in</h1><p className="heading-copy">Group HQ and subsidiary roles are available via the role switcher on the dashboard — this login grants the admin account.</p></div></div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <form className="login-form" onSubmit={submit}>
        <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" placeholder="admin" required /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" placeholder="••••••••" required /></label>
        <button className="button button-primary" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in as Admin'}</button>
      </form>
      <p className="login-hint">Demo credentials: <code>admin</code> / <code>admin123</code></p>
      <p className="login-back"><Link to="/dashboard" className="back-link">← Back to the demo role switcher</Link></p>
    </div>
  </section>
}
