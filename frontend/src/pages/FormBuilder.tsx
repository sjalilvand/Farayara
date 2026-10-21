/** فرم‌ساز بصری — کشیدن و رهاکردن با dnd-kit (بخش ۶.۱ سند) */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  DndContext, DragEndEvent, PointerSensor, useDraggable, useDroppable, useSensor, useSensors,
} from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { api, errMessage, hasPermission } from '../api/client'
import { Alert, Modal, StatusBadge } from '../components/ui'
import FormRenderer, { FormSchema } from '../components/FormRenderer'

const PALETTE: { type: string; label: string; defaults: any }[] = [
  { type: 'text', label: 'متن کوتاه', defaults: {} },
  { type: 'textarea', label: 'متن بلند', defaults: {} },
  { type: 'number', label: 'عدد', defaults: {} },
  { type: 'money', label: 'مبلغ', defaults: {} },
  { type: 'date', label: 'تاریخ', defaults: {} },
  { type: 'select', label: 'انتخاب تکی', defaults: { validations: { options: ['گزینه ۱', 'گزینه ۲'] } } },
  { type: 'multiselect', label: 'چندگانه', defaults: { validations: { options: ['گزینه ۱', 'گزینه ۲'] } } },
  { type: 'yes_no', label: 'بله / خیر', defaults: {} },
  { type: 'email', label: 'ایمیل', defaults: {} },
  { type: 'phone', label: 'تلفن', defaults: {} },
  { type: 'national_code', label: 'کد ملی', defaults: { validations: { pattern: '^[0-9]{10}$' } } },
  { type: 'url', label: 'نشانی وب', defaults: {} },
  { type: 'percent', label: 'درصد', defaults: {} },
]

function PaletteItem({ item }: { item: (typeof PALETTE)[0] }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: `palette-${item.type}`, data: { source: 'palette', item } })
  return (
    <div ref={setNodeRef} {...attributes} {...listeners} className="palette-item"
      style={{ opacity: isDragging ? 0.4 : 1 }}>
      <span>⠿</span> {item.label}
    </div>
  )
}

function CanvasField({
  field, index, selected, onSelect, onRemove, canEdit,
}: { field: any; index: number; selected: boolean; onSelect: () => void; onRemove: () => void; canEdit: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: field.key })
  return (
    <div ref={setNodeRef} {...attributes} {...listeners} className={`canvas-field ${selected ? 'selected' : ''}`}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1, cursor: 'grab' }}
      onClick={(e) => { e.stopPropagation(); onSelect() }}>
      <div className="cf-head">
        <span className="cf-label">{field.label} {field.required && <span className="req">*</span>}</span>
        <span className="cf-meta">{field.type}</span>
      </div>
      <div className="cf-meta">کلید: {field.key} {field.field_id ? '• متصل به کاتالوگ ✓' : '• بدون اتصال به کاتالوگ'}</div>
      {canEdit && (
        <div style={{ marginTop: 6 }}>
          <button className="btn small danger" onClick={(e) => { e.stopPropagation(); onRemove() }}>حذف</button>
        </div>
      )}
    </div>
  )
}

export default function FormBuilder() {
  const { id } = useParams()
  const [form, setForm] = useState<any>(null)
  const [version, setVersion] = useState<any>(null)
  const [schema, setSchema] = useState<FormSchema>({ fields: [] })
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [preview, setPreview] = useState(false)
  const [previewValues, setPreviewValues] = useState<any>({})
  const [catalogFields, setCatalogFields] = useState<any[]>([])
  const [linkModal, setLinkModal] = useState<{ idx: number; search: string } | null>(null)

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))
  const { setNodeRef: setCanvasRef, isOver } = useDroppable({ id: 'canvas' })

  useEffect(() => {
    if (!id) return
    api.get('/forms/' + id).then((r) => {
      setForm(r.data)
      return api.get(`/form-versions/${r.data.current_version_id}`)
    }).then((r) => {
      if (!r) return
      setVersion(r.data)
      setSchema(r.data.schema_json || { fields: [] })
    }).catch((e) => setErr(errMessage(e)))
    api.get('/catalog/fields', { params: { page_size: 100 } })
      .then((r) => setCatalogFields(r.data.items)).catch(() => {})
  }, [id])

  const canEdit = version?.status !== 'published' && hasPermission('form.create')

  const addField = (item: (typeof PALETTE)[0], at?: number) => {
    const key0 = `field_${Date.now().toString(36)}`
    const nf: any = {
      key: key0, type: item.type, label: item.label, required: false, help: '',
      ...JSON.parse(JSON.stringify(item.defaults)),
    }
    setSchema((s) => {
      const fields = [...s.fields]
      fields.splice(at ?? fields.length, 0, nf)
      return { ...s, fields }
    })
    setSelectedIdx(at ?? (schema.fields.length))
  }

  const updateField = (idx: number, patch: any) => {
    setSchema((s) => {
      const fields = [...s.fields]
      fields[idx] = { ...fields[idx], ...patch }
      return { ...s, fields }
    })
  }

  const removeField = (idx: number) => {
    setSchema((s) => ({ ...s, fields: s.fields.filter((_, i) => i !== idx) }))
    setSelectedIdx(null)
  }

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e
    if (!over) return
    const activeData: any = active.data.current
    if (activeData?.source === 'palette') {
      const overIdx = over.id === 'canvas' ? schema.fields.length : schema.fields.findIndex((f) => f.key === over.id)
      addField(activeData.item, overIdx)
      return
    }
    if (active.id !== over.id && over.id !== 'canvas') {
      const from = schema.fields.findIndex((f) => f.key === active.id)
      const to = schema.fields.findIndex((f) => f.key === over.id)
      if (from >= 0 && to >= 0) {
        setSchema((s) => {
          const fields = [...s.fields]
          const [moved] = fields.splice(from, 1)
          fields.splice(to, 0, moved)
          return { ...s, fields }
        })
      }
    }
  }

  const saveSchema = async () => {
    setErr(''); setOk('')
    try {
      await api.put(`/form-versions/${version.id}/schema`, { schema_json: schema })
      setOk('ساختار فرم ذخیره شد')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const publish = async () => {
    setErr(''); setOk('')
    try {
      await api.put(`/form-versions/${version.id}/schema`, { schema_json: schema })
      await api.post(`/form-versions/${version.id}/publish`)
      setOk('فرم منتشر شد؛ اکنون قابل تکمیل است')
      const r = await api.get(`/form-versions/${version.id}`)
      setVersion(r.data)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const newVersion = async () => {
    try {
      const r = await api.post(`/forms/${id}/versions`, {})
      window.location.href = `/forms/${id}/edit`
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const linkCatalog = async (field: any) => {
    if (!linkModal) return
    updateField(linkModal.idx, {
      field_id: field.id, key: field.tech_name, label: field.title_fa,
      type: field.data_type, validations: field.validation_rules || {},
    })
    setLinkModal(null)
  }

  const selected = selectedIdx !== null ? schema.fields[selectedIdx] : null
  const filteredCatalog = catalogFields.filter((f) =>
    !linkModal?.search || f.title_fa.includes(linkModal.search) || f.tech_name.includes(linkModal.search))

  return (
    <div>
      <div className="page-header">
        <h1>
          فرم‌ساز — {form?.title || '…'}
          {version && <span className="badge" style={{ marginRight: 8 }}>نسخه v{version.version_number}</span>}
          {version && <StatusBadge status={version.status} />}
        </h1>
        <div className="actions">
          {canEdit && <button className="btn secondary" onClick={saveSchema}>ذخیره ساختار</button>}
          {canEdit && <button className="btn" onClick={publish}>انتشار نسخه</button>}
          {!canEdit && hasPermission('form.create') && <button className="btn" onClick={newVersion}>ایجاد نسخه جدید برای ویرایش</button>}
          <button className="btn secondary" onClick={() => setPreview(!preview)}>{preview ? 'بازگشت به طراحی' : 'پیش‌نمایش'}</button>
        </div>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}
      {version?.status === 'published' && (
        <Alert kind="info">این نسخه منتشرشده است و تغییرناپذیر است (بخش ۶.۵ سند). برای ویرایش، نسخه جدید بسازید.</Alert>
      )}

      {preview ? (
        <div className="card">
          <h2>پیش‌نمایش فرم</h2>
          <FormRenderer schema={schema} values={previewValues}
            onChange={(k, v) => setPreviewValues((p: any) => ({ ...p, [k]: v }))} errors={{}} />
        </div>
      ) : (
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <div className="builder">
            <div className="palette">
              <div className="card">
                <h3>جعبه‌ابزار فیلدها</h3>
                {PALETTE.map((p) => <PaletteItem key={p.type} item={p} />)}
                <div className="muted" style={{ marginTop: 8 }}>
                  فیلدها را به بوم بکشید. برای اتصال به کاتالوگ، روی فیلد بزنید.
                </div>
              </div>
            </div>
            <div>
              <div ref={setCanvasRef} className="card" style={{ minHeight: 300, background: isOver ? '#f0fdfa' : '#fff' }}>
                <h3>ساختار فرم ({schema.fields.length.toLocaleString('fa-IR')} فیلد)</h3>
                <SortableContext items={schema.fields.map((f) => f.key)} strategy={verticalListSortingStrategy}>
                  {schema.fields.length === 0 && (
                    <div className="empty-state">فیلدی وجود ندارد — از جعبه‌ابزار بکشید و اینجا رها کنید</div>
                  )}
                  {schema.fields.map((f, i) => (
                    <CanvasField key={f.key} field={f} index={i} canEdit={canEdit}
                      selected={selectedIdx === i}
                      onSelect={() => setSelectedIdx(i)}
                      onRemove={() => removeField(i)} />
                  ))}
                </SortableContext>
              </div>

              {selected && (
                <div className="card">
                  <h3>مشخصات فیلد «{selected.label}»</h3>
                  <div className="grid-2">
                    <div className="field"><label>عنوان نمایشی</label>
                      <input className="input" disabled={!canEdit} value={selected.label}
                        onChange={(e) => updateField(selectedIdx!, { label: e.target.value })} /></div>
                    <div className="field"><label>کلید (نام فنی)</label>
                      <input className="input" dir="ltr" disabled={!canEdit} value={selected.key}
                        onChange={(e) => updateField(selectedIdx!, { key: e.target.value.replace(/[^a-z0-9_]/gi, '_') })} /></div>
                    <div className="field"><label>متن راهنما</label>
                      <input className="input" disabled={!canEdit} value={selected.help || ''}
                        onChange={(e) => updateField(selectedIdx!, { help: e.target.value })} /></div>
                    <div className="field"><label>الزام</label>
                      <label className="inline-flex">
                        <input type="checkbox" disabled={!canEdit} checked={!!selected.required} style={{ width: 16 }}
                          onChange={(e) => updateField(selectedIdx!, { required: e.target.checked })} />
                        فیلد اجباری
                      </label></div>
                  </div>
                  {(selected.type === 'select' || selected.type === 'multiselect') && (
                    <div className="field"><label>گزینه‌ها (با «،» جدا کنید)</label>
                      <input className="input" disabled={!canEdit}
                        value={(selected.validations?.options || []).join('، ')}
                        onChange={(e) => updateField(selectedIdx!, {
                          validations: { ...selected.validations, options: e.target.value.split('،').map((x: string) => x.trim()).filter(Boolean) },
                        })} /></div>
                  )}
                  <div className="grid-2">
                    <div className="field"><label>حداقل مقدار (اختیاری)</label>
                      <input className="input" type="number" disabled={!canEdit} value={selected.validations?.min ?? ''}
                        onChange={(e) => updateField(selectedIdx!, {
                          validations: { ...selected.validations, min: e.target.value === '' ? undefined : +e.target.value },
                        })} /></div>
                    <div className="field"><label>حداکثر مقدار (اختیاری)</label>
                      <input className="input" type="number" disabled={!canEdit} value={selected.validations?.max ?? ''}
                        onChange={(e) => updateField(selectedIdx!, {
                          validations: { ...selected.validations, max: e.target.value === '' ? undefined : +e.target.value },
                        })} /></div>
                  </div>
                  <div className="inline-flex">
                    <button className="btn secondary small" disabled={!canEdit}
                      onClick={() => setLinkModal({ idx: selectedIdx!, search: '' })}>
                      {selected.field_id ? 'تغییر اتصال به کاتالوگ' : 'اتصال به فیلد کاتالوگ'}
                    </button>
                    {selected.field_id && <span className="badge published">متصل به کاتالوگ</span>}
                  </div>
                </div>
              )}
            </div>
          </div>
        </DndContext>
      )}

      {linkModal && (
        <Modal title="اتصال فیلد به کاتالوگ داده" onClose={() => setLinkModal(null)}>
          <Alert kind="info">
            با اتصال به کاتالوگ، این فیلد از فیلد مرجع مشترک استفاده می‌کند و فراوانی استفاده آن قابل رصد است.
          </Alert>
          <input className="input" placeholder="جست‌وجو در کاتالوگ…" value={linkModal.search}
            onChange={(e) => setLinkModal({ ...linkModal, search: e.target.value })} autoFocus />
          <div style={{ maxHeight: 320, overflowY: 'auto', marginTop: 10 }}>
            {filteredCatalog.map((f) => (
              <div key={f.id} className="canvas-field" style={{ cursor: 'pointer' }}
                onClick={() => linkCatalog(f)}>
                <b>{f.title_fa}</b> <span className="mono muted">{f.tech_name}</span> <span className="badge neutral">{f.data_type}</span>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </div>
  )
}
