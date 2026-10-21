import { useEffect, useState } from 'react'
import { api, errMessage, faDate } from '../api/client'
import { Alert, Empty, Pager } from '../components/ui'

const ACTION_FA: Record<string, string> = {
  login: 'ورود', login_failed: 'ورود ناموفق', logout: 'خروج',
  create: 'ایجاد', update: 'ویرایش', publish: 'انتشار', deactivate: 'غیرفعال‌سازی',
  activate: 'فعال‌سازی', submit: 'ثبت پاسخ', export: 'خروجی داده',
  download_contract: 'دریافت قرارداد', generate_contract: 'تولید قرارداد',
  start_instance: 'شروع اجرا', cancel_instance: 'لغو اجرا', complete_task: 'تکمیل وظیفه',
  save_diagram: 'ذخیره نمودار', update_bindings: 'اتصال گره‌ها',
  create_version: 'ایجاد نسخه', update_schema: 'ذخیره ساختار',
  update_body: 'ویرایش متن', update_variables: 'ویرایش متغیرها',
  create_administration: 'ایجاد اجرای آزمون', submit_assessment: 'ثبت پاسخ آزمون',
  rescore: 'محاسبه مجدد', approve: 'تأیید', backup: 'پشتیبان‌گیری',
  update_setting: 'تغییر تنظیمات', assessment_discovery: 'جست‌وجوی آزمون',
  import_draft: 'ورود پیش‌نویس', revise: 'اصلاح پاسخ', add_validation_case: 'افزودن مثال مرجع',
  update_content: 'ویرایش محتوای آزمون',
}

export default function AuditLogs() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<any>({})
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/audit-logs', { params: { ...filters, page, page_size: 30 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total) })
      .catch((e) => setErr(errMessage(e)))
  }, [page, filters])

  return (
    <div>
      <div className="page-header"><h1>سوابق تغییرات (ممیزی)</h1></div>
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <div className="grid-3">
          <div className="field mb0"><label>کاربر</label>
            <input className="input" value={filters.actor || ''} placeholder="نام کاربری…"
              onChange={(e) => { setFilters({ ...filters, actor: e.target.value || undefined }); setPage(1) }} /></div>
          <div className="field mb0"><label>نوع رویداد</label>
            <select className="select" value={filters.action || ''}
              onChange={(e) => { setFilters({ ...filters, action: e.target.value || undefined }); setPage(1) }}>
              <option value="">همه</option>
              {Object.entries(ACTION_FA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select></div>
          <div className="field mb0"><label>موجودیت</label>
            <select className="select" value={filters.entity_type || ''}
              onChange={(e) => { setFilters({ ...filters, entity_type: e.target.value || undefined }); setPage(1) }}>
              <option value="">همه</option>
              {['user', 'form', 'form_version', 'form_submission', 'process', 'process_version',
                'process_instance', 'process_task', 'field', 'assessment', 'assessment_version',
                'assessment_administration', 'contract', 'contract_template', 'system'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select></div>
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>زمان</th><th>کاربر</th><th>رویداد</th><th>موجودیت</th><th>کد/شناسه</th><th>IP</th><th>جزئیات</th></tr></thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td className="muted" style={{ whiteSpace: 'nowrap' }}>{faDate(a.created_at, true)}</td>
                  <td className="mono">{a.actor_username || '—'}</td>
                  <td><span className="badge neutral">{ACTION_FA[a.action] || a.action}</span></td>
                  <td className="mono">{a.entity_type || '—'}</td>
                  <td className="mono">{a.entity_code || a.entity_id?.slice(0, 8) || '—'}</td>
                  <td className="mono">{a.ip || '—'}</td>
                  <td style={{ maxWidth: 260 }}>
                    {a.detail ? <span className="mono" style={{ fontSize: 10.5, wordBreak: 'break-all' }}>{JSON.stringify(a.detail)}</span> : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!items.length && <Empty text="رویدادی ثبت نشده" />}
        <Pager page={page} pageSize={30} total={total} onPage={setPage} />
      </div>
    </div>
  )
}
