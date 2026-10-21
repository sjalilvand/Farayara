/** اجرای آزمون — ایجاد اجرا، پاسخ‌دهی، محاسبه و مشاهده نتیجه */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, errMessage } from '../api/client'
import { Alert, Loading } from '../components/ui'

export default function AssessmentRun() {
  const { id } = useParams()
  const nav = useNavigate()
  const [asm, setAsm] = useState<any>(null)
  const [admin, setAdmin] = useState<any>(null)
  const [respondent, setRespondent] = useState('')
  const [identifier, setIdentifier] = useState('')
  const [answers, setAnswers] = useState<any>({})
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!id) return
    api.get('/assessments/' + id).then((r) => setAsm(r.data)).catch((e) => setErr(errMessage(e)))
  }, [id])

  if (err) return <Alert kind="error">{err}</Alert>
  if (!asm) return <Loading />

  const startAdmin = async () => {
    setBusy(true); setErr('')
    try {
      const r = await api.post(`/assessment-versions/${asm.current_version_id}/administrations`, {
        respondent_name: respondent || null, respondent_identifier: identifier || null,
      })
      const detail = await api.get(`/assessment-administrations/${r.data.id}`)
      await api.post(`/assessment-administrations/${r.data.id}/start`)
      setAdmin(detail.data)
    } catch (e: any) { setErr(errMessage(e)) } finally { setBusy(false) }
  }

  const submit = async () => {
    setBusy(true); setErr('')
    try {
      const r = await api.post(`/assessment-administrations/${admin.id}/submit`, { answers })
      nav(`/assessment-administrations/${admin.id}/result`)
    } catch (e: any) { setErr(errMessage(e)) } finally { setBusy(false) }
  }

  if (!admin) {
    return (
      <div>
        <div className="page-header"><h1>اجرای آزمون — {asm.title_fa}</h1></div>
        <div className="card" style={{ maxWidth: 480 }}>
          <Alert kind="info">
            پاسخ‌دهی فقط برای نسخه منتشرشده و تأییدشده فعال است. اطلاعات مراجع برای گزارش‌گیری ثبت می‌شود.
          </Alert>
          <div className="field"><label>نام پاسخ‌دهنده</label>
            <input className="input" value={respondent} onChange={(e) => setRespondent(e.target.value)} /></div>
          <div className="field"><label>شناسه پاسخ‌دهنده (اختیاری)</label>
            <input className="input" value={identifier} onChange={(e) => setIdentifier(e.target.value)} /></div>
          <button className="btn" onClick={startAdmin} disabled={busy}>شروع پاسخ‌دهی</button>
        </div>
      </div>
    )
  }

  const items = admin.items || []

  return (
    <div>
      <div className="page-header">
        <h1>{admin.assessment?.title_fa}</h1>
        <span className="badge">v{admin.version?.version_number}</span>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      <div className="card">
        <p className="muted">پاسخ‌دهنده: {admin.respondent_name || '—'} — به همه سؤال‌ها پاسخ دهید.</p>
        {items.map((it: any, idx: number) => (
          <div key={it.code} className="canvas-field" style={{ cursor: 'default', marginBottom: 12 }}>
            <b>{(idx + 1).toLocaleString('fa-IR')}. {it.text}</b> {it.is_reverse && <span className="badge warn">معکوس</span>}
            <div style={{ marginTop: 8, display: 'flex', gap: 14, flexWrap: 'wrap' }}>
              {(it.options || []).map((o: any) => (
                <label key={o.value} className="inline-flex" style={{ cursor: 'pointer' }}>
                  <input type="radio" name={it.code} value={o.value} style={{ width: 16 }}
                    checked={String(answers[it.code] || '') === String(o.value)}
                    onChange={() => setAnswers({ ...answers, [it.code]: o.value })} />
                  {o.label}
                </label>
              ))}
            </div>
          </div>
        ))}
        <button className="btn" onClick={submit} disabled={busy}>
          {busy ? 'در حال محاسبه…' : 'ثبت پاسخ و محاسبه نمره'}
        </button>
      </div>
    </div>
  )
}
