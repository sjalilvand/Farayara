import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMessage, hasPermission } from '../api/client'
import { Alert, Empty, Modal, Pager, StatusBadge } from '../components/ui'

export default function Assessments() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [err, setErr] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [showDiscovery, setShowDiscovery] = useState(false)
  const [form, setForm] = useState<any>({ title_fa: '', domain: '', author: '', publisher: '', license_status: 'unknown', license_terms: '', target_group: '' })

  const load = () => {
    api.get('/assessments', { params: { query, page, page_size: 15 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total) })
      .catch((e) => setErr(errMessage(e)))
  }
  useEffect(load, [page])

  const create = async () => {
    try {
      const r = await api.post('/assessments', form)
      setShowNew(false)
      window.location.href = `/assessments/${r.data.id}`
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <div>
      <div className="page-header">
        <h1>بانک آزمون‌ها</h1>
        <div className="actions">
          {hasPermission('assessment.manage') && (
            <>
              <button className="btn secondary" onClick={() => setShowDiscovery(true)}>جست‌وجوی اینترنتی آزمون‌ها</button>
              <button className="btn" onClick={() => setShowNew(true)}>+ آزمون جدید</button>
            </>
          )}
        </div>
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <input className="input" placeholder="جست‌وجو…" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1) }} />
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr><th>کد</th><th>عنوان</th><th>حوزه</th><th>مؤلف/ناشر</th><th>مجوز</th><th>تأیید علمی</th><th>تأیید حقوقی</th><th>نسخه</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td className="mono">{a.code}</td>
                  <td><Link to={`/assessments/${a.id}`}><b>{a.title_fa}</b></Link>
                    {a.title_original && <div className="muted">{a.title_original}</div>}</td>
                  <td>{a.domain || '—'}</td>
                  <td>{a.author || '—'}<div className="muted">{a.publisher || ''}</div></td>
                  <td><StatusBadge status={a.license_status} /></td>
                  <td>{a.approved_scientific ? '✓' : '—'}</td>
                  <td>{a.approved_legal ? '✓' : '—'}</td>
                  <td>v{a.current_version_number ?? '—'} <StatusBadge status={a.current_version_status} /></td>
                  <td className="row-actions">
                    <Link className="btn small secondary" to={`/assessments/${a.id}`}>جزئیات</Link>
                    {a.current_version_status === 'published' && hasPermission('assessment.run') && (
                      <Link className="btn small" to={`/assessments/${a.id}/run`}>اجرا</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!items.length && <Empty text="آزمونی یافت نشد" />}
        <Pager page={page} pageSize={15} total={total} onPage={setPage} />
      </div>

      {showNew && (
        <Modal title="ثبت آزمون جدید در بانک" onClose={() => setShowNew(false)}>
          <div className="grid-2">
            <div className="field"><label>عنوان فارسی <span className="req">*</span></label>
              <input className="input" value={form.title_fa} onChange={(e) => setForm({ ...form, title_fa: e.target.value })} /></div>
            <div className="field"><label>حوزه کاربرد</label>
              <input className="input" value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} /></div>
            <div className="field"><label>مؤلف</label>
              <input className="input" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} /></div>
            <div className="field"><label>ناشر / دارنده حقوق</label>
              <input className="input" value={form.publisher} onChange={(e) => setForm({ ...form, publisher: e.target.value })} /></div>
            <div className="field"><label>وضعیت مجوز</label>
              <select className="select" value={form.license_status} onChange={(e) => setForm({ ...form, license_status: e.target.value })}>
                <option value="unknown">نامشخص</option>
                <option value="owned">ساخته‌شده داخلی (دارای مجوز)</option>
                <option value="licensed">مجوز خریداری‌شده</option>
                <option value="public_domain">مالکیت عمومی</option>
                <option value="restricted">محدود</option>
              </select></div>
            <div className="field"><label>جامعه هدف</label>
              <input className="input" value={form.target_group} onChange={(e) => setForm({ ...form, target_group: e.target.value })} /></div>
          </div>
          <div className="field"><label>شرایط مجوز و ملاحظات حقوقی</label>
            <textarea className="textarea" value={form.license_terms}
              onChange={(e) => setForm({ ...form, license_terms: e.target.value })} /></div>
          <Alert kind="warn">یادآوری سند (بخش ۱۰.۲): ورود محتوای آزمون‌های دارای حق نشر بدون مجوز ممنوع است؛ فقط منابع مجاز وارد شود.</Alert>
          <div className="modal-actions">
            <button className="btn" disabled={!form.title_fa.trim()} onClick={create}>ثبت آزمون</button>
            <button className="btn secondary" onClick={() => setShowNew(false)}>انصراف</button>
          </div>
        </Modal>
      )}

      {showDiscovery && <DiscoveryModal onClose={() => setShowDiscovery(false)} />}
    </div>
  )
}

function DiscoveryModal({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[] | null>(null)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [imported, setImported] = useState('')

  const search = async () => {
    setBusy(true); setErr(''); setResults(null)
    try {
      const r = await api.post('/assessment-discovery/search', { query })
      setResults(r.data.results)
      setNotice(r.data.notice)
      if (r.data.errors?.length) setErr(r.data.errors.join(' | '))
    } catch (e: any) { setErr(errMessage(e)) } finally { setBusy(false) }
  }

  const importDraft = async (r: any) => {
    try {
      const res = await api.post('/assessment-discovery/import', {
        title_fa: r.title || query, source_url: r.url, source_title: r.title,
        license_status: 'unknown',
        license_terms: 'نیازمند بررسی حقوقی — پیش‌نویس از جست‌وجوی اینترنتی',
        note: r.snippet,
      })
      setImported(res.data.notice)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <Modal title="جست‌وجوی اینترنتی آزمون‌ها" onClose={onClose} wide>
      {err && <Alert kind="error">{err}</Alert>}
      {imported && <Alert kind="ok">{imported}</Alert>}
      <Alert kind="warn">
        مرزهای قابلیت (بخش ۱۰.۲ سند): یافتن نام آزمون به معنی مجاز بودن ذخیره یا بازنشر سؤال‌های آن نیست؛
        اطلاعات هویتی مراجع به سرویس جست‌وجو ارسال نمی‌شود.
      </Alert>
      <div className="inline-flex" style={{ width: '100%' }}>
        <input className="input" placeholder="نام آزمون یا موضوع…" value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()} />
        <button className="btn" onClick={search} disabled={busy || query.trim().length < 2}>
          {busy ? 'در حال جست‌وجو…' : 'جست‌وجو'}
        </button>
      </div>
      {results && (
        <div style={{ maxHeight: 380, overflowY: 'auto', marginTop: 12 }}>
          {results.length === 0 && <Empty text="نتیجه‌ای یافت نشد" />}
          {results.map((r, i) => (
            <div key={i} className="canvas-field" style={{ cursor: 'default' }}>
              <div className="cf-head">
                <a href={r.url} target="_blank" rel="noreferrer"><b>{r.title}</b></a>
                <span className="badge neutral">{r.source}</span>
              </div>
              <div className="cf-meta">{r.snippet}</div>
              <div style={{ marginTop: 6 }}>
                <button className="btn small secondary" onClick={() => importDraft(r)}>ورود به‌عنوان پیش‌نویس</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {notice && <Alert kind="info">{notice}</Alert>}
    </Modal>
  )
}
