/** نتیجه آزمون — نمرات، نمودار، تفسیر و تاریخچه محاسبات (بخش ۱۱.۴) */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Loading } from '../components/ui'

export default function AssessmentResults() {
  const { id } = useParams()
  const [data, setData] = useState<any>(null)
  const [adm, setAdm] = useState<any>(null)
  const [err, setErr] = useState('')

  const load = () => {
    if (!id) return
    api.get(`/assessment-administrations/${id}/results`).then((r) => setData(r.data)).catch((e) => setErr(errMessage(e)))
    api.get(`/assessment-administrations/${id}`).then((r) => setAdm(r.data)).catch(() => {})
  }
  useEffect(load, [id])

  if (err) return <Alert kind="error">{err}</Alert>
  if (!data) return <Loading />

  const result = data.results?.[data.results.length - 1]
  const chart = result ? Object.entries(result.raw_scores || {}).map(([k, v]) => ({ scale: k, score: Number(v) })) : []

  return (
    <div>
      <div className="page-header">
        <h1>نتیجه آزمون</h1>
        {hasPermission('assessment.manage') && data.status === 'completed' && (
          <button className="btn small secondary" onClick={async () => {
            await api.post(`/assessment-administrations/${id}/rescore`)
            load()
          }}>محاسبه مجدد (اجرای محاسباتی جدید)</button>
        )}
      </div>
      {err && <Alert kind="error">{err}</Alert>}

      {!result && <Alert kind="warn">این اجرا هنوز تکمیل نشده است. <Link to="/assessments">بازگشت</Link></Alert>}

      {result && (
        <>
          <div className="card">
            <div className="inline-flex">
              <span className={`badge ${result.is_valid ? 'published' : 'cancelled'}`}>
                {result.is_valid ? 'نتیجه معتبر' : 'نتیجه نامعتبر'}
              </span>
              <span className="badge">میزان کامل بودن پاسخ‌ها: {Math.round((result.completeness || 0) * 100)}٪</span>
              <span className="muted">{faDate(result.created_at, true)}</span>
            </div>
            {adm && (
              <p className="muted">
                پاسخ‌دهنده: {adm.respondent_name || '—'} — آزمون: {adm.assessment?.title_fa} (v{adm.version?.version_number})
              </p>
            )}
          </div>

          <div className="grid-2">
            <div className="card">
              <h2>نمره خام مقیاس‌ها</h2>
              <div className="chart-box" style={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="scale" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="score" fill="#0f766e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="card">
              <h2>تفسیر</h2>
              {Object.entries(result.interpretations || {}).map(([code, t]: any) => (
                <div key={code} style={{ borderBottom: '1px solid #f1f5f9', padding: '8px 0' }}>
                  <b>{code}</b>: نمره {t.score} — {t.label || '—'}
                  {t.description && <div className="muted">{t.description}</div>}
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2>گزارش</h2>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 2.2 }}>{result.report_text}</pre>
            <Alert kind="warn">
              خروجی سامانه ابزار کمک به متخصص است، نه تشخیص قطعی یا جایگزین ارزیابی بالینی (بخش ۱۱.۴ سند).
            </Alert>
          </div>

          <div className="card">
            <h2>تاریخچه محاسبات ({data.score_runs.length.toLocaleString('fa-IR')} اجرا)</h2>
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr><th>#</th><th>زمان محاسبه</th><th>محاسب</th></tr></thead>
                <tbody>
                  {data.score_runs.map((r: any, i: number) => (
                    <tr key={r.id}><td>{(i + 1).toLocaleString('fa-IR')}</td><td>{faDate(r.created_at, true)}</td><td>{r.created_by || '—'}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="muted">تغییر قواعد آزمون نتایج تاریخی را تغییر نمی‌دهد؛ هر محاسبه مجدد یک ScoreRun جدید است (AC-13).</div>
          </div>
        </>
      )}
    </div>
  )
}
