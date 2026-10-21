import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Modal, Pager, StatusBadge } from '../components/ui'

const DATA_TYPES = [
  ['text', 'متن کوتاه'], ['textarea', 'متن بلند'], ['number', 'عدد صحیح'],
  ['decimal', 'عدد اعشاری'], ['money', 'مبلغ'], ['percent', 'درصد'],
  ['date', 'تاریخ'], ['time', 'ساعت'], ['select', 'انتخاب تکی'],
  ['multiselect', 'انتخاب چندگانه'], ['yes_no', 'بله/خیر'], ['email', 'ایمیل'],
  ['phone', 'تلفن'], ['url', 'نشانی وب'], ['national_code', 'کد ملی'],
  ['file', 'فایل'], ['repeat_group', 'جدول تکرارشونده'], ['computed', 'محاسباتی'],
]

export default function Catalog() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [similar, setSimilar] = useState<any[]>([])
  const [form, setForm] = useState<any>({
    tech_name: '', title_fa: '', data_type: 'text', category: '', description: '',
    aliases: '', sensitivity: 'normal', is_identity: false, is_health: false,
    validation_rules: '{}',
  })

  const load = () => {
    api.get('/catalog/fields', { params: { query, page, page_size: 15 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total) })
      .catch((e) => setErr(errMessage(e)))
  }
  useEffect(load, [page])

  const search = (e: React.FormEvent) => { e.preventDefault(); setPage(1); load() }

  const checkSimilar = async (title: string) => {
    if (title.trim().length < 2) { setSimilar([]); return }
    try {
      const r = await api.get('/catalog/similar', { params: { name: title } })
      setSimilar(r.data)
    } catch { setSimilar([]) }
  }

  const submit = async () => {
    setErr(''); setOk('')
    try {
      let rules = {}
      try { rules = JSON.parse(form.validation_rules || '{}') } catch { throw new Error('قواعد اعتبارسنجی JSON نامعتبر است') }
      await api.post('/catalog/fields', {
        ...form,
        validation_rules: rules,
        aliases: form.aliases ? form.aliases.split('،').map((x: string) => x.trim()).filter(Boolean) : [],
      })
      setOk('فیلد مرجع با موفقیت ایجاد شد')
      setShowNew(false)
      load()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <div>
      <div className="page-header">
        <h1>کاتالوگ مرکزی داده</h1>
        {hasPermission('catalog.manage') && (
          <button className="btn" onClick={() => setShowNew(true)}>+ فیلد مرجع جدید</button>
        )}
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}

      <div className="card">
        <form onSubmit={search} className="inline-flex" style={{ width: '100%' }}>
          <input className="input" placeholder="جست‌وجو در عنوان، نام فنی یا مترادف‌ها…" value={query}
            onChange={(e) => setQuery(e.target.value)} />
          <button className="btn secondary">جست‌وجو</button>
        </form>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>کد</th><th>عنوان فارسی</th><th>نام فنی</th><th>نوع</th>
                <th>دسته</th><th>حساسیت</th><th>فرم‌ها</th><th>وضعیت</th><th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((f) => (
                <tr key={f.id}>
                  <td className="mono">{f.code}</td>
                  <td><Link to={`/catalog/${f.id}`}>{f.title_fa}</Link></td>
                  <td className="mono">{f.tech_name}</td>
                  <td>{DATA_TYPES.find((d) => d[0] === f.data_type)?.[1] || f.data_type}</td>
                  <td>{f.category || '—'}</td>
                  <td>
                    {f.sensitivity !== 'normal' ? (
                      <span className="badge warn">{f.sensitivity === 'highly_sensitive' ? 'بسیار حساس' : 'حساس'}</span>
                    ) : <span className="badge neutral">عادی</span>}
                    {f.is_identity && <span className="badge published">هویتی</span>}
                    {f.is_health && <span className="badge published">سلامت</span>}
                  </td>
                  <td>{(f.forms_count || 0).toLocaleString('fa-IR')}</td>
                  <td><StatusBadge status={f.status} /></td>
                  <td><Link className="btn small secondary" to={`/catalog/${f.id}`}>جزئیات</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!items.length && <Empty text="فیلدی یافت نشد" />}
        <Pager page={page} pageSize={15} total={total} onPage={setPage} />
      </div>

      {showNew && (
        <Modal title="ایجاد فیلد مرجع جدید" onClose={() => setShowNew(false)}>
          {err && <Alert kind="error">{err}</Alert>}
          {similar.length > 0 && (
            <Alert kind="warn">
              فیلدهای مشابه موجود — قبل از ایجاد، آن‌ها بررسی کنید (سامانه خودکار ادغام نمی‌کند):
              <ul style={{ margin: '6px 18px 0 0' }}>
                {similar.map((s) => <li key={s.id}><b>{s.title_fa}</b> ({s.tech_name}) — امتیاز {Math.round(s.score * 100)}٪</li>)}
              </ul>
            </Alert>
          )}
          <div className="grid-2">
            <div className="field"><label>عنوان فارسی <span className="req">*</span></label>
              <input className="input" value={form.title_fa}
                onChange={(e) => { setForm({ ...form, title_fa: e.target.value }); checkSimilar(e.target.value) }} /></div>
            <div className="field"><label>نام فنی (لاتین) <span className="req">*</span></label>
              <input className="input" dir="ltr" value={form.tech_name}
                onChange={(e) => setForm({ ...form, tech_name: e.target.value })} /></div>
            <div className="field"><label>نوع داده</label>
              <select className="select" value={form.data_type} onChange={(e) => setForm({ ...form, data_type: e.target.value })}>
                {DATA_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></div>
            <div className="field"><label>دسته‌بندی</label>
              <input className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></div>
            <div className="field"><label>مترادف‌ها (با «،» جدا کنید)</label>
              <input className="input" value={form.aliases} onChange={(e) => setForm({ ...form, aliases: e.target.value })} /></div>
            <div className="field"><label>سطح حساسیت</label>
              <select className="select" value={form.sensitivity} onChange={(e) => setForm({ ...form, sensitivity: e.target.value })}>
                <option value="normal">عادی</option>
                <option value="sensitive">حساس</option>
                <option value="highly_sensitive">بسیار حساس</option>
              </select></div>
            <div className="field"><label>قواعد اعتبارسنجی (JSON)</label>
              <input className="input" dir="ltr" placeholder='{"pattern": "^09[0-9]{9}$"}' value={form.validation_rules}
                onChange={(e) => setForm({ ...form, validation_rules: e.target.value })} /></div>
            <div className="field"><label>توضیح</label>
              <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <div className="inline-flex">
            <label className="inline-flex"><input type="checkbox" checked={form.is_identity} style={{ width: 16 }}
              onChange={(e) => setForm({ ...form, is_identity: e.target.checked })} /> اطلاعات هویتی</label>
            <label className="inline-flex"><input type="checkbox" checked={form.is_health} style={{ width: 16 }}
              onChange={(e) => setForm({ ...form, is_health: e.target.checked })} /> اطلاعات سلامت</label>
          </div>
          <div className="modal-actions">
            <button className="btn" onClick={submit}>ایجاد فیلد</button>
            <button className="btn secondary" onClick={() => setShowNew(false)}>انصراف</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
