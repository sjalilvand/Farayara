/** مدیریت کاربران، نقش‌ها و ماتریس مجوزها */
import { useEffect, useState } from 'react'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Modal } from '../components/ui'

export default function Users() {
  const [tab, setTab] = useState<'users' | 'roles'>('users')
  const [users, setUsers] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [perms, setPerms] = useState<any[]>([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [editUser, setEditUser] = useState<any>(null)
  const [editRole, setEditRole] = useState<any>(null)

  const load = () => {
    api.get('/users', { params: { page_size: 100 } }).then((r) => setUsers(r.data.items)).catch((e) => setErr(errMessage(e)))
    api.get('/roles').then((r) => setRoles(r.data)).catch(() => {})
    api.get('/permissions').then((r) => setPerms(r.data)).catch(() => {})
  }
  useEffect(load, [])

  const groups = Array.from(new Set(perms.map((p) => p.group || 'سایر')))

  const saveUser = async () => {
    setErr(''); setOk('')
    try {
      if (editUser.id) {
        await api.put(`/users/${editUser.id}`, {
          full_name: editUser.full_name, email: editUser.email, unit: editUser.unit,
          is_active: editUser.is_active, role_codes: editUser.role_codes,
          password: editUser.password || undefined,
        })
      } else {
        await api.post('/users', {
          username: editUser.username, password: editUser.password,
          full_name: editUser.full_name, email: editUser.email, unit: editUser.unit,
          role_codes: editUser.role_codes,
        })
      }
      setEditUser(null)
      setOk('ذخیره شد')
      load()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const saveRole = async () => {
    setErr(''); setOk('')
    try {
      if (editRole.id) {
        await api.put(`/roles/${editRole.id}`, editRole)
      } else {
        await api.post('/roles', editRole)
      }
      setEditRole(null)
      setOk('ذخیره شد')
      load()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const togglePerm = (code: string) => {
    const set = new Set(editRole.permission_codes || [])
    if (set.has(code)) set.delete(code)
    else set.add(code)
    setEditRole({ ...editRole, permission_codes: Array.from(set) })
  }

  return (
    <div>
      <div className="page-header">
        <h1>کاربران و نقش‌ها</h1>
        {tab === 'users' && hasPermission('user.manage') && (
          <button className="btn" onClick={() => setEditUser({ username: '', password: '', full_name: '', role_codes: [], is_active: true })}>
            + کاربر جدید
          </button>
        )}
        {tab === 'roles' && hasPermission('role.manage') && (
          <button className="btn" onClick={() => setEditRole({ code: '', name: '', permission_codes: [] })}>
            + نقش جدید
          </button>
        )}
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}

      <div className="tabs">
        <button className={tab === 'users' ? 'active' : ''} onClick={() => setTab('users')}>کاربران</button>
        <button className={tab === 'roles' ? 'active' : ''} onClick={() => setTab('roles')}>نقش‌ها و مجوزها</button>
      </div>

      {tab === 'users' && (
        <div className="card">
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>نام کاربری</th><th>نام کامل</th><th>واحد</th><th>نقش‌ها</th><th>وضعیت</th><th>آخرین ورود</th><th></th></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="mono">{u.username}</td>
                    <td><b>{u.full_name}</b></td>
                    <td>{u.unit || '—'}</td>
                    <td>{u.roles.map((r: any) => <span key={r.code} className="badge neutral" style={{ marginLeft: 4 }}>{r.name}</span>)}</td>
                    <td><span className={`badge ${u.is_active ? 'active' : 'inactive'}`}>{u.is_active ? 'فعال' : 'غیرفعال'}</span></td>
                    <td>{faDate(u.last_login_at, true)}</td>
                    <td>{hasPermission('user.manage') && (
                      <button className="btn small secondary" onClick={() => setEditUser({ ...u, role_codes: u.roles.map((r: any) => r.code), password: '' })}>ویرایش</button>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!users.length && <Empty />}
        </div>
      )}

      {tab === 'roles' && (
        <div className="card">
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>کد</th><th>نام نقش</th><th>تعداد مجوز</th><th>سیستمی</th><th></th></tr></thead>
              <tbody>
                {roles.map((r) => (
                  <tr key={r.id}>
                    <td className="mono">{r.code}</td>
                    <td><b>{r.name}</b></td>
                    <td>{r.permissions.length.toLocaleString('fa-IR')}</td>
                    <td>{r.is_system ? 'بله' : 'خیر'}</td>
                    <td>{hasPermission('role.manage') && (
                      <button className="btn small secondary" onClick={() => setEditRole({ ...r })}>ویرایش مجوزها</button>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {editUser && (
        <Modal title={editUser.id ? 'ویرایش کاربر' : 'ایجاد کاربر'} onClose={() => setEditUser(null)}>
          <div className="grid-2">
            {!editUser.id && (
              <>
                <div className="field"><label>نام کاربری <span className="req">*</span></label>
                  <input className="input" dir="ltr" value={editUser.username}
                    onChange={(e) => setEditUser({ ...editUser, username: e.target.value })} /></div>
                <div className="field"><label>رمز عبور <span className="req">*</span></label>
                  <input className="input" dir="ltr" type="password" value={editUser.password}
                    onChange={(e) => setEditUser({ ...editUser, password: e.target.value })} /></div>
              </>
            )}
            <div className="field"><label>نام کامل</label>
              <input className="input" value={editUser.full_name}
                onChange={(e) => setEditUser({ ...editUser, full_name: e.target.value })} /></div>
            <div className="field"><label>ایمیل</label>
              <input className="input" dir="ltr" value={editUser.email || ''}
                onChange={(e) => setEditUser({ ...editUser, email: e.target.value })} /></div>
            <div className="field"><label>واحد سازمانی</label>
              <input className="input" value={editUser.unit || ''}
                onChange={(e) => setEditUser({ ...editUser, unit: e.target.value })} /></div>
            <div className="field"><label>وضعیت</label>
              <label className="inline-flex"><input type="checkbox" checked={editUser.is_active} style={{ width: 16 }}
                onChange={(e) => setEditUser({ ...editUser, is_active: e.target.checked })} /> فعال</label></div>
          </div>
          <div className="field"><label>نقش‌ها</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {roles.map((r) => (
                <label key={r.code} className="inline-flex" style={{ cursor: 'pointer' }}>
                  <input type="checkbox" style={{ width: 15 }}
                    checked={(editUser.role_codes || []).includes(r.code)}
                    onChange={(e) => {
                      const set = new Set(editUser.role_codes || [])
                      if (e.target.checked) set.add(r.code); else set.delete(r.code)
                      setEditUser({ ...editUser, role_codes: Array.from(set) })
                    }} />
                  {r.name}
                </label>
              ))}
            </div></div>
          <div className="modal-actions">
            <button className="btn" onClick={saveUser}>ذخیره</button>
            <button className="btn secondary" onClick={() => setEditUser(null)}>انصراف</button>
          </div>
        </Modal>
      )}

      {editRole && (
        <Modal title={editRole.id ? `مجوزهای نقش «${editRole.name}»` : 'ایجاد نقش'} onClose={() => setEditRole(null)} wide>
          {!editRole.id && (
            <div className="grid-2">
              <div className="field"><label>کد نقش (لاتین) <span className="req">*</span></label>
                <input className="input" dir="ltr" value={editRole.code}
                  onChange={(e) => setEditRole({ ...editRole, code: e.target.value })} /></div>
              <div className="field"><label>نام نقش <span className="req">*</span></label>
                <input className="input" value={editRole.name}
                  onChange={(e) => setEditRole({ ...editRole, name: e.target.value })} /></div>
            </div>
          )}
          {groups.map((g) => (
            <div key={g} style={{ marginBottom: 12 }}>
              <h3>{g}</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                {perms.filter((p) => (p.group || 'سایر') === g).map((p) => (
                  <label key={p.code} className="inline-flex" style={{ cursor: 'pointer', minWidth: 240 }}
                    title={p.title}>
                    <input type="checkbox" style={{ width: 15 }}
                      checked={(editRole.permission_codes || []).includes(p.code)}
                      onChange={() => togglePerm(p.code)} />
                    {p.title}
                  </label>
                ))}
              </div>
            </div>
          ))}
          <div className="modal-actions">
            <button className="btn" onClick={saveRole}>ذخیره</button>
            <button className="btn secondary" onClick={() => setEditRole(null)}>انصراف</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
