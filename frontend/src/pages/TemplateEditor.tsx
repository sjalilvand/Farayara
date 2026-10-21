/** ویرایشگر الگوی قرارداد — Tiptap (فارسی RTL)، متغیرها، پیش‌نمایش، انتشار (بخش ۱۲.۱) */
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableHeader from '@tiptap/extension-table-header'
import TableCell from '@tiptap/extension-table-cell'
import { api, errMessage, hasPermission } from '../api/client'
import { Alert, Modal, StatusBadge } from '../components/ui'

const VAR_TYPES = [['text', 'متن'], ['number', 'عدد'], ['money', 'مبلغ'], ['date', 'تاریخ'], ['duration', 'مدت']]

export default function TemplateEditor() {
  const { id } = useParams()
  const [tpl, setTpl] = useState<any>(null)
  const [ver, setVer] = useState<any>(null)
  const [variables, setVariables] = useState<any[]>([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [preview, setPreview] = useState<any>(null)
  const [showStart, setShowStart] = useState(false)
  const [legal, setLegal] = useState('')

  const editor = useEditor({
    extensions: [
      StarterKit, Placeholder.configure({ placeholder: 'متن قرارداد را اینجا بنویسید…' }),
      Table.configure({ resizable: true }), TableRow, TableHeader, TableCell,
    ],
    content: '',
    editable: false,
  })

  useEffect(() => {
    if (!id) return
    api.get('/contract-templates/' + id).then(async (r) => {
      setTpl(r.data)
      const v = await api.get(`/contract-template-versions/${r.data.current_version_id}`)
      setVer(v.data)
      setVariables(r.data.variables || [])
      if (editor && v.data.body_html) editor.commands.setContent(v.data.body_html)
      editor?.setEditable(v.data.status !== 'published')
    }).catch((e) => setErr(errMessage(e)))
  }, [id])

  const canEdit = ver?.status !== 'published' && hasPermission('contract.manage')

  const detectedVars = useMemo(() => {
    const html = editor?.getHTML() || ''
    const found = new Set<string>()
    for (const m of html.matchAll(/\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g)) found.add(m[1])
    return Array.from(found)
  }, [editor?.getHTML()])

  const saveBody = async () => {
    setErr(''); setOk('')
    try {
      const r = await api.put(`/contract-template-versions/${ver.id}/body`, {
        body_html: editor?.getHTML() || '',
      })
      setOk('متن الگو ذخیره شد (پاکسازی HTML انجام شد)')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const saveVariables = async () => {
    setErr(''); setOk('')
    try {
      await api.put(`/contract-template-versions/${ver.id}/variables`, { variables })
      setOk('متغیرها ذخیره شد')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const publish = async () => {
    setErr(''); setOk('')
    try {
      await saveBody()
      await saveVariables()
      await api.post(`/contract-template-versions/${ver.id}/publish`, { legal_approver: legal || null })
      const v = await api.get(`/contract-template-versions/${ver.id}`)
      setVer(v.data)
      setOk('الگو منتشر شد؛ اکنون قابل تولید قرارداد است')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const doPreview = async () => {
    setErr(''); setOk('')
    try {
      await saveBody()
      const r = await api.post(`/contract-template-versions/${ver.id}/preview`, { data: {} })
      setPreview(r.data)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const insertVar = (key: string) => {
    editor?.chain().focus().insertContent(`{{${key}}}`).run()
  }

  const insertIf = (key: string) => {
    editor?.chain().focus().insertContent(`{%if ${key}%}متن مشروط{%endif%}`).run()
  }

  return (
    <div>
      <div className="page-header">
        <h1>{tpl?.title || '…'} <span className="mono muted">({tpl?.code})</span></h1>
        <div className="actions inline-flex">
          <span className="badge">v{ver?.version_number}</span>
          {ver && <StatusBadge status={ver.status} />}
          {canEdit && <button className="btn secondary" onClick={saveBody}>ذخیره متن</button>}
          {canEdit && <button className="btn secondary" onClick={saveVariables}>ذخیره متغیرها</button>}
          <button className="btn secondary" onClick={doPreview}>پیش‌نمایش</button>
          {hasPermission('contract.approve') && canEdit && <button className="btn" onClick={publish}>انتشار الگو</button>}
          {!canEdit && hasPermission('contract.manage') && (
            <button className="btn" onClick={async () => { await api.post(`/contract-templates/${id}/versions`, {}); window.location.reload() }}>
              نسخه جدید
            </button>
          )}
          {ver?.status === 'published' && hasPermission('contract.generate') && (
            <button className="btn warn" onClick={() => setShowStart(true)}>تولید قرارداد از این الگو</button>
          )}
        </div>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}

      <div className="grid-2" style={{ gridTemplateColumns: '1fr 300px', alignItems: 'start' }}>
        <div className="card tiptap-editor">
          <div className="tiptap-toolbar">
            <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()} className={editor?.isActive('bold') ? 'on' : ''}><b>ب</b></button>
            <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()} className={editor?.isActive('italic') ? 'on' : ''}><i>کج</i></button>
            <button type="button" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}>عنوان</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleBulletList().run()}>فهرست</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleOrderedList().run()}>شماره‌دار</button>
            <button type="button" onClick={() => editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}>جدول</button>
          </div>
          <EditorContent editor={editor} />
          <div className="muted" style={{ marginTop: 8 }}>
            متغیرها به‌صورت <code className="inline">{"{{key}}"}</code> در متن جایگذاری می‌شوند؛ بندهای شرطی با <code className="inline">{"{%if key%}…{%endif%}"}</code>.
          </div>
        </div>

        <div>
          <div className="card">
            <h3>متغیرهای الگو</h3>
            {variables.map((v, i) => (
              <div key={i} className="canvas-field" style={{ cursor: 'default', padding: 8 }}>
                <div className="inline-flex">
                  <input className="input" dir="ltr" style={{ width: 130 }} disabled={!canEdit} value={v.key}
                    onChange={(e) => setVariables(variables.map((x, idx) => idx === i ? { ...x, key: e.target.value } : x))} />
                  <input className="input" style={{ width: 100 }} disabled={!canEdit} placeholder="عنوان" value={v.label}
                    onChange={(e) => setVariables(variables.map((x, idx) => idx === i ? { ...x, label: e.target.value } : x))} />
                  <select className="select" style={{ width: 76 }} disabled={!canEdit} value={v.data_type || 'text'}
                    onChange={(e) => setVariables(variables.map((x, idx) => idx === i ? { ...x, data_type: e.target.value } : x))}>
                    {VAR_TYPES.map(([t, l]) => <option key={t} value={t}>{l}</option>)}
                  </select>
                  <label className="inline-flex" title="الزامی">
                    <input type="checkbox" disabled={!canEdit} checked={!!v.required} style={{ width: 15 }}
                      onChange={(e) => setVariables(variables.map((x, idx) => idx === i ? { ...x, required: e.target.checked } : x))} />
                  </label>
                </div>
              </div>
            ))}
            {canEdit && (
              <>
                <button className="btn small secondary" onClick={() => setVariables([...variables, { key: '', label: '', data_type: 'text', required: false }])}>+ متغیر</button>
                <button className="btn small danger" onClick={() => setVariables(variables.slice(0, -1))}>حذف آخرین</button>
              </>
            )}
          </div>

          <div className="card">
            <h3>درج در متن</h3>
            <div className="muted" style={{ marginBottom: 6 }}>متغیرهای شناسایی‌شده در متن:</div>
            {detectedVars.length === 0 && <div className="muted">—</div>}
            {detectedVars.map((k) => (
              <div key={k} className="inline-flex" style={{ marginBottom: 4 }}>
                <span className="fr-var-chip mono">{k}</span>
                <button className="btn small secondary" onClick={() => insertVar(k)}>درج</button>
                <button className="btn small secondary" onClick={() => insertIf(k)}>بند شرطی</button>
              </div>
            ))}
            <div className="muted" style={{ marginTop: 8 }}>
              متغیرهای تعریف‌شده: {variables.filter((v) => v.key).map((v) => v.key).join('، ') || '—'}
            </div>
          </div>
        </div>
      </div>

      {preview && (
        <Modal title="پیش‌نمایش الگو (متغیرهای خالی نشان‌دار هستند)" onClose={() => setPreview(null)} wide>
          {preview.required_missing?.length > 0 && (
            <Alert kind="warn">متغیرهای الزامی خالی: {preview.required_missing.join('، ')} — تولید نهایی مسدود خواهد بود (AC-14).</Alert>
          )}
          <div className="contract-view" dangerouslySetInnerHTML={{ __html: preview.html }} />
        </Modal>
      )}

      {showStart && (
        <Modal title="تولید قرارداد" onClose={() => setShowStart(false)}>
          <Alert kind="info">به صفحه «قراردادهای تولیدشده» بروید و از الگوی منتشرشده قرارداد بسازید.</Alert>
          <div className="modal-actions">
            <button className="btn" onClick={() => { window.location.href = '/contracts' }}>رفتن به تولید قرارداد</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
