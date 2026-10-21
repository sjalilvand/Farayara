import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMessage, faDate } from '../api/client'
import { Alert, Empty, StatusBadge } from '../components/ui'

export default function MyTasks() {
  const [tasks, setTasks] = useState<any[]>([])
  const [status, setStatus] = useState('pending')
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/tasks/my', { params: { status } }).then((r) => setTasks(r.data)).catch((e) => setErr(errMessage(e)))
  }, [status])

  return (
    <div>
      <div className="page-header">
        <h1>کارتابل من</h1>
        <div className="inline-flex">
          <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="pending">در انتظار انجام</option>
            <option value="completed">تکمیل‌شده</option>
            <option value="cancelled">لغوشده</option>
          </select>
        </div>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      <div className="card">
        {tasks.length === 0 && <Empty text="وظیفه‌ای در کارتابل شما نیست" />}
        {tasks.length > 0 && (
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>وظیفه</th><th>فرایند</th><th>کد پیگیری</th><th>فرم</th><th>ایجاد</th><th></th></tr></thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id}>
                    <td><b>{t.node_name || '—'}</b></td>
                    <td>{t.process_title || '—'}</td>
                    <td className="mono">{t.trace_code || '—'}</td>
                    <td>{t.form_title || 'بدون فرم'}</td>
                    <td>{faDate(t.created_at, true)}</td>
                    <td>
                      {t.status === 'pending' ? (
                        <Link className="btn small" to={`/tasks/${t.id}`}>انجام وظیفه</Link>
                      ) : <StatusBadge status={t.status} />}
                    </td>
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
