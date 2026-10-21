import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Modal, Pager, StatusBadge } from '../components/ui'

export default function Forms() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [err, setErr] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('')

  const load = () => {
    api.get('/forms', { params: { query, page, page_size: 15 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total) })
      .catch((e) => setErr(errMessage(e)))
  }
  useEffect(load, [page])

  const createForm = async () => {
    try {
      const r = await api.post('/forms', { title, category: category || null })
      setShowNew(false)
      window.location.href = `/forms/${r.data.id}/edit`
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <div>
      <div className="page-header">
        <h1>فرم‌ها</h1>
        {hasPermission('form.create') && <button className="btn" onClick={() => setShowNew(true)}>+ فرم جدید</button>}
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <div className="inline-flex" style={{ width: '100%' }}>
          <input className="input" placeholder="جست‌وجوی عنوان یا کد فرم…" value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(1) }} />
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr><th>کد</th><th>عنوان</th><th>دسته</th><th>نسخه جاری</th><th>وضعیت نسخه</th><th>ایجاد</th><th>عملیات</th></tr>
            </thead>
            <tbody>
              {items.map((f) => (
                <tr key={f.id}>
                  <td className="mono">{f.code}</td>
                  <td><b>{f.title}</b><div className="muted">{f.description}</div></td>
                  <td>{f.category || '—'}</td>
                  <td>v{f.current_version_number ?? '—'}</td>
                  <td><StatusBadge status={f.current_version_status} /></td>
                  <td>{faDate(f.created_at)}</td>
                  <td className="row-actions">
                    {hasPermission('form.create') && (
                      <Link className="btn small" to={`/forms/${f.id}/edit`}>ویرایشگر</Link>
                    )}
                    {hasPermission('form.submissions.view') && (
                      <Link className="btn small secondary" to={`/forms/${f.id}/submissions`}>پاسخ‌ها</Link>
                    )}
                    {f.current_version_id && f.current_version_status === 'published' && hasPermission('form.submit') && (
                      <Link className="btn small secondary" to={`/fill/${f.current_version_id}`}>تکمیل فرم</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!items.length && <Empty text="فرمی یافت نشد" />}
        <Pager page={page} pageSize={15} total={total} onPage={setPage} />
      </div>

      {showNew && (
        <Modal title="ایجاد فرم جدید" onClose={() => setShowNew(false)}>
          <div className="field"><label>عنوان فرم <span className="req">*</span></label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus /></div>
          <div className="field"><label>دسته‌بندی</label>
            <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} /></div>
          <div className="modal-actions">
            <button className="btn" disabled={!title.trim()} onClick={createForm}>ایجاد و رفتن به فرم‌ساز</button>
            <button className="btn secondary" onClick={() => setShowNew(false)}>انصراف</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
