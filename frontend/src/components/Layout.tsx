/** چیدمان اصلی — منوی مطابق بخش ۱۴ سند با فیلتر مجوزها */
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api, hasPermission } from '../api/client'
import { useAuth } from '../auth/AuthContext'

type MenuItem = { to: string; label: string; perm?: string }

const MENU: { group: string; items: MenuItem[] }[] = [
  {
    group: 'اصلی',
    items: [
      { to: '/', label: 'داشبورد', perm: 'dashboard.view' },
      { to: '/tasks', label: 'کارتابل من' },
    ],
  },
  {
    group: 'فرم و کاتالوگ',
    items: [
      { to: '/forms', label: 'فرم‌ها' },
      { to: '/processes', label: 'فرایندها' },
      { to: '/catalog', label: 'کاتالوگ داده' },
    ],
  },
  {
    group: 'آزمون و قرارداد',
    items: [
      { to: '/assessments', label: 'آزمون‌ها' },
      { to: '/contract-templates', label: 'الگوهای قرارداد' },
      { to: '/contracts', label: 'قراردادهای تولیدشده' },
    ],
  },
  {
    group: 'مدیریت',
    items: [
      { to: '/users', label: 'کاربران و نقش‌ها', perm: 'user.manage' },
      { to: '/audit', label: 'سوابق تغییرات', perm: 'audit.view' },
      { to: '/settings', label: 'تنظیمات', perm: 'system.settings' },
    ],
  },
]

export default function Layout() {
  const { currentUser, logout } = useAuth()
  const nav = useNavigate()
  const [notifications, setNotifications] = useState<any[]>([])
  const [openNotif, setOpenNotif] = useState(false)

  useEffect(() => {
    const t = setInterval(() => {
      api.get('/notifications').then((r) => setNotifications(r.data)).catch(() => {})
    }, 30000)
    api.get('/notifications').then((r) => setNotifications(r.data)).catch(() => {})
    return () => clearInterval(t)
  }, [])

  const unread = notifications.filter((n) => !n.is_read).length

  const doLogout = async () => {
    try {
      await api.post('/auth/logout')
    } catch { /* ignore */ }
    logout()
    nav('/login')
  }

  const initial = (currentUser?.full_name || currentUser?.username || '؟').trim().charAt(0)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>فرایارا</h1>
          <span>سامانه یکپارچه فرایند و فرم</span>
        </div>
        <nav>
          {MENU.map((g) => {
            const visible = g.items.filter((it) => !it.perm || hasPermission(it.perm))
            if (!visible.length) return null
            return (
              <div key={g.group}>
                <div className="nav-group">{g.group}</div>
                {visible.map((it) => (
                  <NavLink key={it.to} to={it.to} end={it.to === '/'}
                    className={({ isActive }) => (isActive ? 'active' : '')}>
                    {it.label}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <div className="user-info">
            <div className="avatar">{initial}</div>
            <div>
              <div style={{ fontWeight: 600 }}>{currentUser?.full_name}</div>
              <div className="muted">
                {currentUser?.roles?.map((r: any) => r.name).join('، ') || '—'}
              </div>
            </div>
          </div>
          <div className="inline-flex">
            <button className="btn small secondary" onClick={() => setOpenNotif(!openNotif)}>
              اعلان‌ها {unread > 0 && <span className="badge warn">{unread}</span>}
            </button>
            <button className="btn small secondary" onClick={doLogout}>خروج</button>
          </div>
        </header>
        {openNotif && (
          <div className="page" style={{ paddingBottom: 0 }}>
            <div className="card">
              <h2>اعلان‌ها</h2>
              {notifications.length === 0 && <div className="muted">اعلانی وجود ندارد.</div>}
              {notifications.slice(0, 8).map((n) => (
                <div key={n.id} style={{ borderBottom: '1px solid #f1f5f9', padding: '8px 0' }}>
                  <b style={{ fontSize: 13 }}>{n.title}</b> {n.is_read ? '' : <span className="badge warn">جدید</span>}
                  <div className="muted">{n.body}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        <main className="page">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
