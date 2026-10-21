import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { setSession } from '../api/client'

const BASE = '/api/v1'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const r = await axios.post(`${BASE}/auth/login`, { username, password })
      setSession(r.data.access_token, r.data.refresh_token, r.data.user)
      nav('/')
    } catch (err: any) {
      if (!err?.response) {
        setError('سرور بک‌اند در دسترس نیست؛ مطمئن شوید uvicorn روی پورت 8000 اجرا شده است (دستور: uvicorn app.main:app --reload از پوشه backend)')
      } else {
        setError(err?.response?.data?.message || 'ورود ناموفق بود')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>فرایارا</h1>
        <div className="sub">سامانه یکپارچه مدیریت فرایندها، فرم‌ها، کاتالوگ داده، آزمون‌ها و قراردادها</div>
        {error && <div className="alert error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>نام کاربری</label>
            <input className="input" dir="ltr" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </div>
          <div className="field">
            <label>رمز عبور</label>
            <input className="input" dir="ltr" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn" style={{ width: '100%', justifyContent: 'center' }} disabled={busy}>
            {busy ? 'در حال ورود…' : 'ورود به سامانه'}
          </button>
        </form>
        <div className="login-hint">
          <b>حساب‌های نمونه:</b><br />
          مدیر سامانه: admin / Admin@1234<br />
          طراح فرم: fdesigner / Form@1234<br />
          متخصص آزمون: assessor / Assess@1234<br />
          کاربر اجرایی: operator / Oper@1234
        </div>
      </div>
    </div>
  )
}
