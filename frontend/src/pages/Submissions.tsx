/** پاسخ‌های ثبت‌شده فرم + خروجی CSV/Excel/JSON (بخش ۶.۵ و ۸ سند) */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Modal, Pager } from '../components/ui'

export default function Submissions() {
  const { id } = useParams()
  const [form, setForm] = useState<any>(null)
  const [data, setData] = useState<any>({ items: [], total: 0 })
  const [page, setPage] = useState(1)
  const [err, setErr] = useState('')
  const [selected, setSelected] = useState<any>(null)

  useEffect(() => {
    if (!id) return
    api.get('/forms/' + id).then((r) => setForm(r.data)).catch((e) => setErr(errMessage(e)))
  }, [id])

  useEffect(() => {
    if (!id) return
    api.get(`/forms/${id}/submissions`, { params: { page, page_size: 15 } })
      .then((r) => setData(r.data)).catch((e) => setErr(errMessage(e)))
  }, [id, page])

  const exportFile = (format: string) => {
    window.open(`/api/v1/forms/${id}/submissions/export?format=${format}`, '_blank')
  }

  return (
    <div>
      <div className="page-header">
        <h1>پاسخ‌های ثبت‌شده — {form?.title || '…'}</h1>
        {hasPermission('export.data') && (
          <div className="actions">
            <button className="btn small secondary" onClick={() => exportFile('csv')}>خروجی CSV</button>
            <button className="btn small secondary" onClick={() => exportFile('xlsx')}>خروجی Excel</button>
            <button className="btn small secondary" onClick={() => exportFile('json')}>خروجی JSON</button>
          </div>
        )}
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr><th>کد رهگیری</th><th>نسخه</th><th>پاسخ‌دهنده</th><th>تاریخ ثبت</th><th>وضعیت</th><th></th></tr>
            </thead>
            <tbody>
              {data.items.map((s: any) => (
                <tr key={s.id}>
                  <td className="mono">{s.trace_code}</td>
                  <td>v{s.version_number}</td>
                  <td>{s.respondent_name || '—'}</td>
                  <td>{faDate(s.submitted_at, true)}</td>
                  <td><span className={`badge ${s.status}`}>{s.status === 'final' ? 'نهایی' : 'پیش‌نویس'}</span></td>
                  <td><button className="btn small secondary" onClick={async () => {
                    const r = await api.get(`/submissions/${s.id}`)
                    setSelected(r.data)
                  }}>مشاهده</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!data.items.length && <Empty text="پاسخی ثبت نشده است" />}
        <Pager page={page} pageSize={15} total={data.total} onPage={setPage} />
      </div>

      {selected && (
        <Modal title={`پاسخ ${selected.trace_code}`} onClose={() => setSelected(null)} wide>
          <div className="kv">
            <dt>فرم</dt><dd>{selected.form_title} (v{selected.version_number})</dd>
            <dt>تاریخ ثبت</dt><dd>{faDate(selected.submitted_at, true)}</dd>
          </div>
          <h3 style={{ marginTop: 14 }}>داده‌های پاسخ</h3>
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>فیلد</th><th>مقدار</th></tr></thead>
              <tbody>
                {Object.entries(selected.data || {}).map(([k, v]) => (
                  <tr key={k}><td className="mono">{k}</td><td>{Array.isArray(v) ? v.join('، ') : String(v)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Modal>
      )}
    </div>
  )
}
