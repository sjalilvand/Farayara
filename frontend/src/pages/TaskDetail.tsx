/** انجام وظیفه کارتابل — تکمیل فرم مرحله و ثبت در فرایند */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errMessage, faDate } from '../api/client'
import { Alert, Loading, StatusBadge } from '../components/ui'
import FormRenderer, { validateAll } from '../components/FormRenderer'

export default function TaskDetail() {
  const { id } = useParams()
  const [task, setTask] = useState<any>(null)
  const [values, setValues] = useState<any>({})
  const [errors, setErrors] = useState<any>({})
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')

  useEffect(() => {
    if (!id) return
    api.get('/tasks/' + id).then((r) => setTask(r.data)).catch((e) => setErr(errMessage(e)))
  }, [id])

  if (err) return <Alert kind="error">{err}</Alert>
  if (!task) return <Loading />

  const submit = async () => {
    setErr(''); setOk('')
    const schema = task.form_version?.schema_json || { fields: [] }
    const errs = validateAll(schema, values)
    setErrors(errs)
    if (Object.keys(errs).length) return
    try {
      const r = await api.post(`/tasks/${id}/complete`, { data: values })
      setOk(`وظیفه تکمیل شد — وضعیت فرایند: ${r.data.instance_status === 'completed' ? 'خاتمه‌یافته' : 'در حال اجرا'} (کد پیگیری: ${r.data.trace_code})`)
      const t = await api.get('/tasks/' + id)
      setTask(t.data)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  return (
    <div>
      <div className="page-header">
        <h1>وظیفه: {task.node_name}</h1>
        <StatusBadge status={task.status} />
      </div>
      {ok && <Alert kind="ok">{ok}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <div className="card">
        <div className="kv" style={{ marginBottom: 14 }}>
          <dt>کد پیگیری فرایند</dt>
          <dd className="mono">{task.instance?.trace_code || '—'}</dd>
          <dt>عنوان نمونه</dt>
          <dd>{task.instance?.title || '—'}</dd>
          <dt>ایجاد</dt>
          <dd>{faDate(task.created_at, true)}</dd>
          <dt>تکمیل</dt>
          <dd>{faDate(task.completed_at, true)}</dd>
        </div>
      </div>

      {task.status === 'pending' && task.form_version && (
        <div className="card">
          <h2>فرم مرحله</h2>
          <FormRenderer schema={task.form_version.schema_json} values={values}
            onChange={(k, v) => setValues((p: any) => ({ ...p, [k]: v }))} errors={errors} />
          <button className="btn" onClick={submit}>ثبت و تکمیل وظیفه</button>
        </div>
      )}
      {task.status === 'pending' && !task.form_version && (
        <div className="card">
          <h2>تکمیل وظیفه (بدون فرم)</h2>
          <Alert kind="info">این مرحله فرمی ندارد؛ می‌توانید یادداشت دلخواه ثبت کنید یا مستقیم تکمیل کنید.</Alert>
          <div className="field"><label>یادداشت (اختیاری)</label>
            <textarea className="textarea" value={values.note || ''}
              onChange={(e) => setValues((p: any) => ({ ...p, note: e.target.value }))} /></div>
          <button className="btn" onClick={submit}>تکمیل وظیفه</button>
        </div>
      )}
      {task.status !== 'pending' && (
        <div className="card">
          <Alert kind="ok">این وظیفه قبلاً تکمیل شده است. <Link to="/tasks">بازگشت به کارتابل</Link></Alert>
          <h3>داده‌های ثبت‌شده</h3>
          <pre className="mono" style={{ whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(task.payload?.data || {}, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
