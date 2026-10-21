/** قراردادهای تولیدشده — تولید از الگو، مشاهده سند منجمد، هش و دریافت (بخش ۱۲.۴) */
import { useEffect, useState } from 'react'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Modal, Pager, StatusBadge } from '../components/ui'

export default function Contracts() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [err, setErr] = useState('')
  const [templates, setTemplates] = useState<any[]>([])
  const [showNew, setShowNew] = useState<any>(null)
  const [values, setValues] = useState<any>({})
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [detail, setDetail] = useState<any>(null)

  const load = () => {
    api.get('/contracts', { params: { page, page_size: 15 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total) })
      .catch((e) => setErr(errMessage(e)))
  }
  useEffect(load, [page])

  const openGenerate = async () => {
    const r = await api.get('/contract-templates', { params: { page_size: 100 } })
    const published = r.data.items.filter((t: any) => t.current_version_status === 'published')
    setTemplates(published)
    if (published.length) {
      const v = await api.get(`/contract-template-versions/${published[0].current_version_id}`)
      setShowNew({ versionId: v.data.id, variables: v.data.variables || [] })
      setValues({})
      setPreviewHtml(null)
    } else {
      setErr('الگوی منتشرشده‌ای موجود نیست')
    }
  }

  const doPreview = async () => {
    try {
      const r = await api.post(`/contract-template-versions/${showNew.versionId}/preview`, { data: values })
      setPreviewHtml(r.data.html)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const generate = async () => {
    setErr('')
    try {
      const r = await api.post('/contracts', { template_version_id: showNew.versionId, data: values })
      setShowNew(null)
      const d = await api.get(`/contracts/${r.data.id}`)
      setDetail(d.data)
      load()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const inputType = (t: string) => (t === 'number' || t === 'money' ? 'number' : t === 'date' ? 'text' : 'text')

  return (
    <div>
      <div className="page-header">
        <h1>قراردادهای تولیدشده</h1>
        {hasPermission('contract.generate') && <button className="btn" onClick={openGenerate}>+ تولید قرارداد از الگو</button>}
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>کد</th><th>عنوان</th><th>طرف اول</th><th>طرف دوم</th><th>مبلغ (ریال)</th><th>تاریخ</th><th>تولید</th><th></th></tr></thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td className="mono">{c.code}</td>
                  <td><b>{c.title}</b></td>
                  <td>{c.party_a_name || '—'}</td>
                  <td>{c.party_b_name || '—'}</td>
                  <td>{c.amount ? c.amount.toLocaleString('fa-IR') : '—'}</td>
                  <td>{c.contract_date || '—'}</td>
                  <td>{faDate(c.generated_at)}</td>
                  <td className="row-actions">
                    <button className="btn small secondary" onClick={async () => {
                      const d = await api.get(`/contracts/${c.id}`); setDetail(d.data)
                    }}>مشاهده</button>
                    {hasPermission('file.download') && (
                      <button className="btn small secondary" onClick={async () => {
                        const r = await api.get(`/contracts/${c.id}/download`, { responseType: 'blob' })
                        const url = URL.createObjectURL(r.data)
                        const a = document.createElement('a')
                        a.href = url; a.download = `${c.code}.html`; a.click()
                        URL.revokeObjectURL(url)
                      }}>دریافت سند</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!items.length && <Empty text="قراردادی تولید نشده است" />}
        <Pager page={page} pageSize={15} total={total} onPage={setPage} />
      </div>

      {showNew && (
        <Modal title="تولید قرارداد از الگو" onClose={() => setShowNew(null)} wide>
          <div className="field"><label>الگوی منتشرشده</label>
            <select className="select" value={showNew.versionId}
              onChange={async (e) => {
                const v = await api.get(`/contract-template-versions/${e.target.value}`)
                setShowNew({ versionId: v.data.id, variables: v.data.variables || [] })
                setValues({}); setPreviewHtml(null)
              }}>
              {templates.map((t) => <option key={t.current_version_id} value={t.current_version_id}>
                {t.title} (v{t.current_version_number})
              </option>)}
            </select></div>
          <Alert kind="info">
            در زمان تولید، متن الگو و داده‌ها منجمد می‌شوند؛ ویرایش آینده الگو قرارداد قبلی را تغییر نمی‌دهد (AC-15).
          </Alert>
          <div className="grid-2">
            {showNew.variables.map((v: any) => (
              <div className="field" key={v.key}>
                <label>{v.label || v.key} {v.required && <span className="req">*</span>}</label>
                <input className="input" type={inputType(v.data_type)} dir={v.data_type === 'date' || v.data_type === 'text' ? 'auto' : 'ltr'}
                  value={values[v.key] ?? ''} onChange={(e) => setValues({ ...values, [v.key]: e.target.value })} />
              </div>
            ))}
          </div>
          <div className="modal-actions">
            <button className="btn secondary" onClick={doPreview}>پیش‌نمایش</button>
            <button className="btn" onClick={generate}>تولید نهایی قرارداد</button>
          </div>
          {previewHtml && (
            <div style={{ marginTop: 14 }}>
              <h3>پیش‌نمایش</h3>
              <div className="contract-view" style={{ maxHeight: 320, overflowY: 'auto' }}
                dangerouslySetInnerHTML={{ __html: previewHtml }} />
            </div>
          )}
        </Modal>
      )}

      {detail && (
        <Modal title={`قرارداد ${detail.code}`} onClose={() => setDetail(null)} wide>
          <div className="kv" style={{ marginBottom: 10 }}>
            <dt>الگو</dt><dd>{detail.template?.title} (v{detail.template?.version_number})</dd>
            <dt>هش سند (SHA-256)</dt><dd className="mono" style={{ wordBreak: 'break-all' }}>{detail.file_hash}</dd>
            <dt>وضعیت</dt><dd><StatusBadge status={detail.status} /></dd>
          </div>
          <div className="contract-view" style={{ maxHeight: 420, overflowY: 'auto' }}
            dangerouslySetInnerHTML={{ __html: detail.body_html || '' }} />
        </Modal>
      )}
    </div>
  )
}
