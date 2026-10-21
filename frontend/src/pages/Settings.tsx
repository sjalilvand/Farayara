/** تنظیمات سامانه + پشتیبان‌گیری (بخش ۱۹ و ۲۰ سند) */
import { useEffect, useState } from 'react'
import { api, errMessage, hasPermission } from '../api/client'
import { Alert } from '../components/ui'

export default function Settings() {
  const [settings, setSettings] = useState<any>({})
  const [info, setInfo] = useState<any>(null)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')

  const load = () => {
    api.get('/settings').then((r) => setSettings(r.data)).catch((e) => setErr(errMessage(e)))
    api.get('/system/info').then((r) => setInfo(r.data)).catch(() => {})
  }
  useEffect(load, [])

  const saveSetting = async (key: string, current: any) => {
    setErr(''); setOk('')
    try {
      const val = current.value?.value !== undefined ? current.value.value : current.value
      await api.put('/settings', { key, value: { value: val } })
      setOk(`تنظیم «${key}» ذخیره شد`)
      load()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const backup = async () => {
    setErr(''); setOk('')
    try {
      const r = await api.post('/admin/backup', null, { responseType: 'blob' })
      const url = URL.createObjectURL(r.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `farayara_backup_${new Date().toISOString().slice(0, 10)}.db`
      a.click()
      URL.revokeObjectURL(url)
      setOk('نسخه پشتیبان با سازوکار سازگار SQLite گرفته و دانلود شد')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <div>
      <div className="page-header"><h1>تنظیمات سامانه</h1></div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}

      {info && (
        <div className="card">
          <h2>اطلاعات نسخه</h2>
          <dl className="kv">
            <dt>نام سامانه</dt><dd>{info.app_name} ({info.app_name_en})</dd>
            <dt>نسخه</dt><dd className="mono">{info.version}</dd>
            <dt>پایگاه داده</dt><dd>{info.database}</dd>
            <dt>حداکثر حجم فایل</dt><dd>{info.max_upload_size_mb} مگابایت</dd>
          </dl>
        </div>
      )}

      <div className="card">
        <h2>تنظیمات</h2>
        {Object.entries(settings).map(([key, val]: any) => (
          <div className="inline-flex" key={key} style={{ marginBottom: 8, width: '100%' }}>
            <span className="mono" style={{ minWidth: 180, paddingTop: 8 }}>{key}</span>
            <input className="input" style={{ maxWidth: 320 }} disabled={!hasPermission('system.settings')}
              value={val.value?.value ?? ''}
              onChange={(e) => setSettings({ ...settings, [key]: { ...val, value: { value: e.target.value } } })} />
            <span className="muted" style={{ flex: 1, paddingTop: 10 }}>{val.description}</span>
            {hasPermission('system.settings') && (
              <button className="btn small secondary" onClick={() => saveSetting(key, val)}>ذخیره</button>
            )}
          </div>
        ))}
        {!Object.keys(settings).length && <div className="muted">تنظیمی ثبت نشده است.</div>}
      </div>

      {hasPermission('system.admin') && (
        <div className="card">
          <h2>پشتیبان‌گیری</h2>
          <Alert kind="info">
            پشتیبان شامل دیتابیس است؛ فایل‌های پیوست، تنظیمات و نسخه برنامه نیز باید جداگانه نگهداری شوند (بخش ۲۰ سند).
            کپی ساده فایل دیتابیس در حین فعالیت با WAL روش اصلی پشتیبان‌گیری نیست — این عملیات از SQLite Backup API استفاده می‌کند.
          </Alert>
          <button className="btn" onClick={backup}>گرفتن نسخه پشتیبان و دانلود</button>
        </div>
      )}

      <div className="card">
        <h2>الزامات امنیتی استقرار عملیاتی (یادآوری سند — بخش ۱۹)</h2>
        <ul style={{ lineHeight: 2.2, margin: 0, paddingRight: 20 }}>
          <li>فعال‌سازی HTTPS در استقرار (مثلاً با Nginx/Caddy)</li>
          <li>تنظیم متغیر محیطی <code className="inline">FARAYARA_SECRET_KEY</code> با مقدار تصادفی مستقل</li>
          <li>محدودیت تلاش ورود در لایه وب‌سرور</li>
          <li>رمزگذاری دیسک محل دیتابیس و نسخه‌های پشتیبان</li>
          <li>نگهداری نسخه پشتیبان در محل جداگانه و آزمون دوره‌ای بازیابی</li>
        </ul>
      </div>
    </div>
  )
}
