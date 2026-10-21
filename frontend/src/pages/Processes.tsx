import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Modal, Pager, StatusBadge } from '../components/ui'

export default function Processes() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [err, setErr] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('')

  const load = () => {
    api.get('/processes', { params: { query, page, page_size: 15 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total) })
      .catch((e) => setErr(errMessage(e)))
  }
  useEffect(load, [page])

  const create = async () => {
    try {
      const r = await api.post('/processes', { title, category: category || null })
      setShowNew(false)
      window.location.href = `/processes/${r.data.id}`
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <div>
      <div className="page-header">
        <h1>فرایندها</h1>
        {hasPermission('process.create') && <button className="btn" onClick={() => setShowNew(true)}>+ فرایند جدید</button>}
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <input className="input" placeholder="جست‌وجوی عنوان یا کد فرایند…" value={query}
          onChange={(e) => { setQuery(e.target.value); setPage(1) }} />
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr><th>کد</th><th>عنوان</th><th>دسته</th><th>مالک</th><th>نسخه جاری</th><th>وضعیت</th><th>ایجاد</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{p.code}</td>
                  <td><Link to={`/processes/${p.id}`}><b>{p.title}</b></Link><div className="muted">{p.description}</div></td>
                  <td>{p.category || '—'}</td>
                  <td>{p.owner?.full_name || '—'}</td>
                  <td>v{p.current_version_number ?? '—'}</td>
                  <td><StatusBadge status={p.current_version_status} /></td>
                  <td>{faDate(p.created_at)}</td>
                  <td><Link className="btn small secondary" to={`/processes/${p.id}`}>مدیریت</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!items.length && <Empty text="فرایندی یافت نشد" />}
        <Pager page={page} pageSize={15} total={total} onPage={setPage} />
      </div>

      {showNew && (
        <Modal title="ایجاد فرایند جدید" onClose={() => setShowNew(false)}>
          <div className="field"><label>عنوان فرایند <span className="req">*</span></label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus /></div>
          <div className="field"><label>دسته‌بندی</label>
            <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} /></div>
          <div className="modal-actions">
            <button className="btn" disabled={!title.trim()} onClick={create}>ایجاد و بازکردن ویرایشگر</button>
            <button className="btn secondary" onClick={() => setShowNew(false)}>انصراف</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
