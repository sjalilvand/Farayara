import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Modal, Pager, StatusBadge } from '../components/ui'

export default function ContractTemplates() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [err, setErr] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [title, setTitle] = useState('')
  const [type, setType] = useState('')

  const load = () => {
    api.get('/contract-templates', { params: { page, page_size: 15 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total) })
      .catch((e) => setErr(errMessage(e)))
  }
  useEffect(load, [page])

  const create = async () => {
    try {
      const r = await api.post('/contract-templates', { title, contract_type: type || null })
      setShowNew(false)
      window.location.href = `/contract-templates/${r.data.id}/edit`
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <div>
      <div className="page-header">
        <h1>الگوهای قرارداد</h1>
        {hasPermission('contract.manage') && <button className="btn" onClick={() => setShowNew(true)}>+ الگوی جدید</button>}
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>کد</th><th>عنوان</th><th>نوع</th><th>نسخه</th><th>وضعیت</th><th>به‌روزرسانی</th><th></th></tr></thead>
            <tbody>
              {items.map((t) => (
                <tr key={t.id}>
                  <td className="mono">{t.code}</td>
                  <td><b>{t.title}</b><div className="muted">{t.description}</div></td>
                  <td>{t.contract_type || '—'}</td>
                  <td>v{t.current_version_number ?? '—'}</td>
                  <td><StatusBadge status={t.current_version_status} /></td>
                  <td>{faDate(t.updated_at)}</td>
                  <td className="row-actions">
                    <Link className="btn small secondary" to={`/contract-templates/${t.id}/edit`}>ویرایشگر</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!items.length && <Empty text="الگویی یافت نشد" />}
        <Pager page={page} pageSize={15} total={total} onPage={setPage} />
      </div>

      {showNew && (
        <Modal title="ایجاد الگوی قرارداد" onClose={() => setShowNew(false)}>
          <div className="field"><label>عنوان الگو <span className="req">*</span></label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus /></div>
          <div className="field"><label>نوع قرارداد</label>
            <input className="input" value={type} onChange={(e) => setType(e.target.value)} placeholder="خدمات مشاوره، خرید، پیمانکاری…" /></div>
          <div className="modal-actions">
            <button className="btn" disabled={!title.trim()} onClick={create}>ایجاد و بازکردن ویرایشگر</button>
            <button className="btn secondary" onClick={() => setShowNew(false)}>انصراف</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
