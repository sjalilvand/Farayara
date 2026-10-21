/** تکمیل فرم — ثبت پاسخ با کد رهگیری (بخش ۶.۱ و ۸ سند) */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, errMessage } from '../api/client'
import { Alert, Loading } from '../components/ui'
import FormRenderer, { validateAll } from '../components/FormRenderer'

export default function FormFill() {
  const { versionId } = useParams()
  const [version, setVersion] = useState<any>(null)
  const [values, setValues] = useState<any>({})
  const [errors, setErrors] = useState<any>({})
  const [err, setErr] = useState('')
  const [trace, setTrace] = useState<string | null>(null)

  useEffect(() => {
    if (!versionId) return
    api.get(`/form-versions/${versionId}`).then((r) => setVersion(r.data)).catch((e) => setErr(errMessage(e)))
  }, [versionId])

  if (err) return <Alert kind="error">{err}</Alert>
  if (!version) return <Loading />

  const submit = async () => {
    setErr('')
    const errs = validateAll(version.schema_json, values)
    setErrors(errs)
    if (Object.keys(errs).length) return
    try {
      const r = await api.post(`/form-versions/${versionId}/submissions`, { data: values, status: 'final' })
      setTrace(r.data.trace_code)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  if (trace) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 50 }}>
        <h2 style={{ color: 'var(--ok)' }}>پاسخ شما با موفقیت ثبت شد ✓</h2>
        <p>کد رهگیری پاسخ:</p>
        <p className="mono" style={{ fontSize: 22, fontWeight: 700, color: 'var(--primary-dark)' }}>{trace}</p>
        <p className="muted">این کد را برای پیگیری نگهداری کنید.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h1>تکمیل فرم — {version.form_title}</h1>
        <span className="badge">نسخه v{version.version_number}</span>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      <div className="card">
        <FormRenderer schema={version.schema_json} values={values}
          onChange={(k, v) => setValues((p: any) => ({ ...p, [k]: v }))} errors={errors} />
        <button className="btn" onClick={submit}>ثبت نهایی پاسخ</button>
      </div>
    </div>
  )
}
