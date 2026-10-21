/** جزئیات آزمون — شناسنامه، نسخه‌ها، سؤال‌ها، قواعد نمره‌گذاری، منابع، تأیید و انتشار */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Loading, StatusBadge } from '../components/ui'

const EMPTY_ITEM = { code: '', text: '', item_type: 'likert', is_reverse: false, weight: 1, options: [
  { value: '1', label: 'هرگز', score: 1 }, { value: '2', label: 'به‌ندرت', score: 2 },
  { value: '3', label: 'گاهی', score: 3 }, { value: '4', label: 'بیشتر وقت‌ها', score: 4 },
  { value: '5', label: 'همیشه', score: 5 }] }

export default function AssessmentDetail() {
  const { id } = useParams()
  const [asm, setAsm] = useState<any>(null)
  const [ver, setVer] = useState<any>(null)
  const [tab, setTab] = useState('profile')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [cfg, setCfg] = useState<any>({})
  const [scales, setScales] = useState<any[]>([])
  const [validateReport, setValidateReport] = useState<any>(null)

  const load = async () => {
    if (!id) return
    const a = await api.get('/assessments/' + id)
    setAsm(a.data)
    const v = await api.get(`/assessment-versions/${a.data.current_version_id}`)
    setVer(v.data)
    setItems(v.data.items || [])
    setCfg(v.data.items_config || {})
    setScales(v.data.scoring_rules?.scales || [])
  }
  useEffect(() => { load().catch((e) => setErr(errMessage(e))) }, [id])

  if (err && !asm) return <Alert kind="error">{err}</Alert>
  if (!asm || !ver) return <Loading />

  const canEditContent = ver.status !== 'published' && hasPermission('assessment.manage')

  const saveContent = async () => {
    setErr(''); setOk('')
    try {
      await api.put(`/assessment-versions/${ver.id}/content`, {
        items, items_config: cfg, scoring_rules: { scales },
        rules_version_note: 'ویرایش از رابط کاربری',
      })
      setOk('محتوای نسخه ذخیره شد')
      await load()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const validate = async () => {
    setErr(''); setOk(''); setValidateReport(null)
    try {
      const r = await api.post(`/assessment-versions/${ver.id}/validate`)
      setValidateReport(r.data)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const approve = async (kind: 'scientific' | 'legal') => {
    try {
      await api.post(`/assessments/${id}/approve`, { [kind]: true })
      await load()
      setOk(kind === 'scientific' ? 'تأیید علمی ثبت شد' : 'تأیید حقوقی ثبت شد')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const publish = async () => {
    setErr(''); setOk('')
    try {
      await api.post(`/assessment-versions/${ver.id}/publish`, {})
      await load()
      setOk('نسخه آزمون منتشر شد؛ اکنون قابل اجرای رسمی است')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const updateItem = (i: number, patch: any) => {
    setItems(items.map((it, idx) => idx === i ? { ...it, ...patch } : it))
  }

  return (
    <div>
      <div className="page-header">
        <h1>{asm.title_fa} <span className="mono muted">({asm.code})</span></h1>
        <div className="actions inline-flex">
          <span className="badge">v{ver.version_number}</span>
          <StatusBadge status={ver.status} />
          {ver.status === 'published' && hasPermission('assessment.run') && (
            <Link className="btn warn" to={`/assessments/${id}/run`}>اجرای آزمون</Link>
          )}
        </div>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}

      <div className="tabs">
        <button className={tab === 'profile' ? 'active' : ''} onClick={() => setTab('profile')}>شناسنامه</button>
        <button className={tab === 'items' ? 'active' : ''} onClick={() => setTab('items')}>سؤال‌ها و قواعد</button>
        <button className={tab === 'publish' ? 'active' : ''} onClick={() => setTab('publish')}>تأیید و انتشار</button>
        <button className={tab === 'sources' ? 'active' : ''} onClick={() => setTab('sources')}>منابع (بخش ۱۰.۳)</button>
      </div>

      {tab === 'profile' && (
        <div className="grid-2">
          <div className="card">
            <h2>شناسنامه آزمون</h2>
            <dl className="kv">
              <dt>نام اصلی</dt><dd>{asm.title_original || '—'}</dd>
              <dt>نام اختصاری</dt><dd>{asm.abbreviation || '—'}</dd>
              <dt>حوزه کاربرد</dt><dd>{asm.domain || '—'}</dd>
              <dt>مؤلف</dt><dd>{asm.author || '—'}</dd>
              <dt>ناشر/دارنده حقوق</dt><dd>{asm.publisher || '—'}</dd>
              <dt>جامعه هدف</dt><dd>{asm.target_group || '—'}</dd>
              <dt>تعداد سؤال</dt><dd>{asm.item_count ?? '—'}</dd>
              <dt>زمان اجرا</dt><dd>{asm.duration_minutes ? `${asm.duration_minutes} دقیقه` : '—'}</dd>
              <dt>شیوه نمره‌گذاری</dt><dd>{asm.scoring_method || '—'}</dd>
              <dt>محدودیت‌ها</dt><dd>{asm.limitations || '—'}</dd>
              <dt>هنجارها</dt><dd>{asm.norms_notes || '—'}</dd>
            </dl>
          </div>
          <div className="card">
            <h2>وضعیت حقوقی و علمی</h2>
            <dl className="kv">
              <dt>وضعیت مجوز</dt><dd><StatusBadge status={asm.license_status} /></dd>
              <dt>شرایط مجوز</dt><dd>{asm.license_terms || '—'}</dd>
              <dt>تأیید علمی</dt>
              <dd>{asm.approved_scientific ? `✓ (${asm.approved_scientific_by || '—'})` : 'ثبت نشده'}</dd>
              <dt>تأیید حقوقی</dt>
              <dd>{asm.approved_legal ? `✓ (${asm.approved_legal_by || '—'})` : 'ثبت نشده'}</dd>
            </dl>
            <h3 style={{ marginTop: 12 }}>نسخه‌ها</h3>
            {asm.versions.map((v: any) => (
              <div key={v.id} className="inline-flex" style={{ marginBottom: 4 }}>
                <span className="badge">v{v.version_number}</span>
                <StatusBadge status={v.status} />
                <span className="muted">{v.year} — {faDate(v.created_at)}</span>
              </div>
            ))}
            {hasPermission('assessment.manage') && ver.status !== 'published' && (
              <button className="btn small secondary" style={{ marginTop: 8 }}
                onClick={async () => { await api.post(`/assessments/${id}/versions`, {}); await load() }}>
                ایجاد نسخه جدید (از محتوای فعلی)
              </button>
            )}
          </div>
        </div>
      )}

      {tab === 'items' && (
        <div>
          <div className="card">
            <div className="page-header" style={{ marginBottom: 10 }}>
              <h2 className="mb0">سؤال‌ها ({items.length.toLocaleString('fa-IR')})</h2>
              <div className="actions">
                {canEditContent && (
                  <>
                    <button className="btn small secondary" onClick={() => setItems([...items, { ...EMPTY_ITEM, code: `q${items.length + 1}` }])}>+ سؤال</button>
                    <button className="btn small" onClick={saveContent}>ذخیره محتوا</button>
                  </>
                )}
                <button className="btn small warn" onClick={validate}>اعتبارسنجی نمره‌گذاری</button>
              </div>
            </div>
            {items.map((it, i) => (
              <div key={i} className="canvas-field" style={{ cursor: 'default' }}>
                <div className="grid-2">
                  <div className="field"><label>کد</label>
                    <input className="input" dir="ltr" disabled={!canEditContent} value={it.code}
                      onChange={(e) => updateItem(i, { code: e.target.value })} /></div>
                  <div className="field"><label>متن سؤال</label>
                    <input className="input" disabled={!canEditContent} value={it.text}
                      onChange={(e) => updateItem(i, { text: e.target.value })} /></div>
                </div>
                <div className="inline-flex">
                  <label className="inline-flex">
                    <input type="checkbox" disabled={!canEditContent} checked={!!it.is_reverse} style={{ width: 16 }}
                      onChange={(e) => updateItem(i, { is_reverse: e.target.checked })} />
                    سؤال معکوس
                  </label>
                  <span className="muted">گزینه‌ها: {(it.options || []).map((o: any) => o.label).join('، ')}</span>
                  {canEditContent && (
                    <button className="btn small danger" onClick={() => setItems(items.filter((_, idx) => idx !== i))}>حذف</button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="card">
            <h2>قواعد نمره‌گذاری (مقیاس‌ها)</h2>
            {scales.map((s, i) => (
              <div key={i} className="canvas-field" style={{ cursor: 'default' }}>
                <div className="grid-3">
                  <div className="field"><label>کد</label>
                    <input className="input" dir="ltr" disabled={!canEditContent} value={s.code}
                      onChange={(e) => setScales(scales.map((x, idx) => idx === i ? { ...x, code: e.target.value } : x))} /></div>
                  <div className="field"><label>عنوان</label>
                    <input className="input" disabled={!canEditContent} value={s.title || ''}
                      onChange={(e) => setScales(scales.map((x, idx) => idx === i ? { ...x, title: e.target.value } : x))} /></div>
                  <div className="field"><label>سؤال‌ها (با «،»)</label>
                    <input className="input" dir="ltr" disabled={!canEditContent} value={(s.items || []).join(',')}
                      onChange={(e) => setScales(scales.map((x, idx) => idx === i
                        ? { ...x, items: e.target.value.split(',').map((y: string) => y.trim()).filter(Boolean) } : x))} /></div>
                </div>
                {s.expression !== undefined && (
                  <div className="field"><label>عبارت محاسباتی امن (sum/avg/min/max/round)</label>
                    <input className="input" dir="ltr" disabled={!canEditContent} value={s.expression || ''}
                      onChange={(e) => setScales(scales.map((x, idx) => idx === i ? { ...x, expression: e.target.value } : x))} /></div>
                )}
                {s.interpretations && (
                  <div className="muted">
                    بازه‌های تفسیر: {s.interpretations.map((r: any) => `${r.min}–${r.max}: ${r.label}`).join(' | ')}
                  </div>
                )}
              </div>
            ))}
            <div className="grid-2">
              <div className="field"><label>سیاست پاسخ ناقص</label>
                <select className="select" disabled={!canEditContent} value={cfg.missing_policy || 'skip'}
                  onChange={(e) => setCfg({ ...cfg, missing_policy: e.target.value })}>
                  <option value="skip">نادیده‌گرفتن سؤال بی‌پاسخ</option>
                  <option value="zero">نمره صفر</option>
                  <option value="invalidate">بی‌اعتبار کردن نتیجه</option>
                </select></div>
              <div className="field"><label>حداقل نسبت پاسخ داده‌شده برای اعتبار</label>
                <input className="input" type="number" step="0.1" disabled={!canEditContent}
                  value={cfg.validity?.min_answered_ratio ?? 0}
                  onChange={(e) => setCfg({ ...cfg, validity: { min_answered_ratio: +e.target.value } })} /></div>
            </div>
            <Alert kind="info">
              قواعد کاربر با eval اجرا نمی‌شود؛ ارزیاب امن محدود به عملگرهای مجاز و توابع sum/avg/min/max/round است (بخش ۱۱.۲).
            </Alert>
          </div>

          {validateReport && (
            <div className="card">
              <h2>گزارش اعتبارسنجی</h2>
              {validateReport.problems?.length === 0 ? (
                <Alert kind="ok">همه بررسی‌ها موفق بود{validateReport.cases?.all_passed ? ' — مثال‌های مرجع مطابقت دارند ✓' : ''}.</Alert>
              ) : (
                validateReport.problems.map((p: string, i: number) => <Alert key={i} kind="warn">{p}</Alert>)
              )}
              {validateReport.cases?.results?.map((r: any, i: number) => (
                <div key={i} className="inline-flex">
                  <span className={`badge ${r.passed ? 'published' : 'cancelled'}`}>{r.passed ? 'موفق' : 'ناموفق'}</span>
                  <b>{r.case}</b>
                  {r.diffs && <span className="muted mono">{JSON.stringify(r.diffs)}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'publish' && (
        <div className="card">
          <h2>گردش تأیید و انتشار</h2>
          <Alert kind="warn">
            طبق بخش ۱۰.۱ و AC-10 سند: فقط نسخه تأییدشده با مجوز معتبر قابل اجرای رسمی است.
            ورود خودکار قواعد نمره‌گذاری بدون تأیید متخصص ممنوع است.
          </Alert>
          <div className="inline-flex" style={{ marginTop: 12 }}>
            {hasPermission('assessment.approve') && (
              <>
                <button className="btn secondary" disabled={asm.approved_scientific} onClick={() => approve('scientific')}>
                  ثبت تأیید علمی (متخصص)
                </button>
                <button className="btn secondary" disabled={asm.approved_legal} onClick={() => approve('legal')}>
                  ثبت تأیید حقوقی (مجوز استفاده)
                </button>
              </>
            )}
            {hasPermission('assessment.approve') && ver.status !== 'published' && (
              <button className="btn" onClick={publish}>انتشار نسخه</button>
            )}
          </div>
        </div>
      )}

      {tab === 'sources' && (
        <div className="card">
          <h2>منابع آزمون</h2>
          {(asm.sources || []).length === 0 && <div className="muted">منبعی ثبت نشده است.</div>}
          {(asm.sources || []).map((s: any) => (
            <div key={s.id} className="canvas-field" style={{ cursor: 'default' }}>
              <div className="cf-head">
                <a href={s.url} target="_blank" rel="noreferrer"><b>{s.title || s.url}</b></a>
                <span className={`badge ${s.validation_status === 'validated' ? 'published' : 'pending'}`}>
                  {s.validation_status === 'validated' ? 'اعتبارسنجی‌شده' : 'در انتظار بررسی'}
                </span>
              </div>
              <div className="cf-meta">
                {s.author && <>نویسنده: {s.author} — </>}
                تاریخ بازیابی: {faDate(s.retrieved_at)}
                {s.usage_terms && <> — شرایط استفاده: {s.usage_terms}</>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
