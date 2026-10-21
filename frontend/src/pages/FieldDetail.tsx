import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Loading, StatusBadge } from '../components/ui'

export default function FieldDetail() {
  const { id } = useParams()
  const [field, setField] = useState<any>(null)
  const [usage, setUsage] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!id) return
    api.get(`/catalog/fields/${id}`).then((r) => setField(r.data)).catch((e) => setErr(errMessage(e)))
    api.get(`/catalog/fields/${id}/usage`).then((r) => setUsage(r.data)).catch(() => {})
    api.get(`/catalog/fields/${id}/statistics`).then((r) => setStats(r.data)).catch(() => {})
  }, [id])

  if (err) return <Alert kind="error">{err}</Alert>
  if (!field) return <Loading />

  const dist = Object.entries(stats?.value_distribution || {}).map(([k, v]) => ({ value: k, count: v }))

  return (
    <div>
      <div className="page-header">
        <h1>{field.title_fa} <span className="mono muted">({field.code})</span></h1>
        <StatusBadge status={field.status} />
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>شناسنامه فیلد مرجع</h2>
          <dl className="kv">
            <dt>نام فنی</dt><dd className="mono">{field.tech_name}</dd>
            <dt>نوع داده</dt><dd>{field.data_type}</dd>
            <dt>نسخه جاری</dt><dd>v{field.version}</dd>
            <dt>دسته‌بندی</dt><dd>{field.category || '—'}</dd>
            <dt>مترادف‌ها</dt><dd>{field.aliases?.join('، ') || '—'}</dd>
            <dt>قواعد اعتبارسنجی</dt><dd className="mono">{JSON.stringify(field.validation_rules)}</dd>
            <dt>سطح حساسیت</dt><dd>{field.sensitivity}</dd>
            <dt>هویتی / سلامت</dt><dd>{field.is_identity ? 'هویتی' : ''} {field.is_health ? 'سلامت' : '' || 'خیر'}</dd>
            <dt>ایجاد</dt><dd>{faDate(field.created_at)}</dd>
          </dl>
          {hasPermission('catalog.manage') && (
            <div style={{ marginTop: 12 }}>
              {field.status === 'active' ? (
                <button className="btn small danger" onClick={async () => {
                  await api.post(`/catalog/fields/${id}/deactivate`)
                  window.location.reload()
                }}>غیرفعال‌سازی (حذف منطقی)</button>
              ) : (
                <button className="btn small" onClick={async () => {
                  await api.post(`/catalog/fields/${id}/activate`)
                  window.location.reload()
                }}>فعال‌سازی مجدد</button>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <h2>فراوانی فیلد (شاخص‌های مستقل — بخش ۷.۴ سند)</h2>
          {stats && (
            <>
              <dl className="kv">
                <dt>فرم‌های استفاده‌کننده</dt><dd>{stats.forms_count}</dd>
                <dt>نسخه‌های استفاده‌کننده</dt><dd>{stats.versions_count}</dd>
                <dt>تعداد جایگاه‌ها</dt><dd>{stats.places_count}</dd>
                <dt>پاسخ ثبت‌شده</dt><dd>{stats.submissions_count}</dd>
                <dt>مقادیر غیرخالی</dt><dd>{stats.filled_count}</dd>
                <dt>نرخ تکمیل</dt>
                <dd>{stats.fill_rate === null ? '—' : `${Math.round(stats.fill_rate * 100)}٪`}</dd>
              </dl>
              {dist.length > 0 && (
                <>
                  <h3 style={{ marginTop: 14 }}>فراوانی مقادیر</h3>
                  <div className="chart-box" style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={dist}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="value" tick={{ fontSize: 11 }} />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#0f766e" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h2>مسیر استفاده: فیلد ← نسخه فرم</h2>
        {usage.length === 0 && <div className="muted">این فیلد در هیچ فرمی استفاده نشده است.</div>}
        {usage.length > 0 && (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr><th>فرم</th><th>کد فرم</th><th>نسخه</th><th>وضعیت نسخه</th><th>عنوان نمایشی در فرم</th><th>الزامی</th></tr>
              </thead>
              <tbody>
                {usage.map((u) => (
                  <tr key={u.usage_id}>
                    <td><Link to={`/forms/${u.form_id}/submissions`}>{u.form_title}</Link></td>
                    <td className="mono">{u.form_code}</td>
                    <td>v{u.form_version}</td>
                    <td><StatusBadge status={u.form_version_status} /></td>
                    <td>{u.label_override || '—'}</td>
                    <td>{u.required ? 'بله' : 'خیر'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
