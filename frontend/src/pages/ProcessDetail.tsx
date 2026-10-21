/** مدیریت فرایند — ویرایشگر BPMN (bpmn-js)، اتصال فرم/نقش به گره‌ها، اعتبارسنجی، انتشار و اجرا */
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import Modeler from 'bpmn-js/lib/Modeler'
import 'bpmn-js/dist/assets/diagram-js.css'
import 'bpmn-js/dist/assets/bpmn-js.css'
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn-embedded.css'
import { api, errMessage, faDate, hasPermission } from '../api/client'
import { Alert, Empty, Loading, Modal, StatusBadge } from '../components/ui'

const EMPTY_BPMN = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Defs_farayara" targetNamespace="http://farayara.local/bpmn">
  <bpmn:process id="Process_new" isExecutable="true">
    <bpmn:startEvent id="Start_1" name="شروع">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Task_1" name="وظیفه اول">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="End_1" name="پایان">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="Diagram_1">
    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Process_new">
      <bpmndi:BPMNShape id="Start_1_di" bpmnElement="Start_1"><dc:Bounds x="182" y="162" width="36" height="36" /></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1"><dc:Bounds x="270" y="140" width="120" height="80" /></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="End_1_di" bpmnElement="End_1"><dc:Bounds x="460" y="162" width="36" height="36" /></bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1"><di:waypoint x="218" y="180" /><di:waypoint x="270" y="180" /></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2"><di:waypoint x="390" y="180" /><di:waypoint x="460" y="180" /></bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`

export default function ProcessDetail() {
  const { id } = useParams()
  const [proc, setProc] = useState<any>(null)
  const [version, setVersion] = useState<any>(null)
  const [tab, setTab] = useState('diagram')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [analysis, setAnalysis] = useState<any>(null)
  const [bindings, setBindings] = useState<any>({})
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [forms, setForms] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [instances, setInstances] = useState<any[]>([])
  const [showStart, setShowStart] = useState(false)
  const [startVars, setStartVars] = useState('{}')
  const [instDetail, setInstDetail] = useState<any>(null)

  const modelerRef = useRef<any>(null)
  const canvasRef = useRef<HTMLDivElement>(null)

  const loadVersion = async (versionId: string) => {
    const r = await api.get(`/process-versions/${versionId}`)
    setVersion(r.data)
    const b: any = {}
    for (const item of r.data.bindings || []) b[item.node_id] = item
    setBindings(b)
    setInstances(r.data)
    return r.data
  }

  useEffect(() => {
    if (!id) return
    api.get('/processes/' + id).then((r) => {
      setProc(r.data)
      setInstances(r.data.recent_instances || [])
      return loadVersion(r.data.current_version_id)
    }).then((ver) => {
      if (!ver) return
      // ویرایشگر BPMN
      if (canvasRef.current && !modelerRef.current) {
        const modeler = new Modeler({ container: canvasRef.current, keyboard: { bindTo: document } })
        modelerRef.current = modeler
        modeler.on('selection.changed', (e: any) => {
          const el = e.newSelection?.[0]
          if (el && (el.type.includes('Task') || el.type.includes('Gateway') || el.type.includes('Event'))) {
            setSelectedNode({ id: el.id, type: el.type.split(':')[1], name: el.businessObject?.name || el.id })
          } else {
            setSelectedNode(null)
          }
        })
      }
      modelerRef.current.importXML(ver.bpmn_xml || EMPTY_BPMN).catch((e: any) => setErr('خطا در بارگذاری نمودار: ' + e.message))
    }).catch((e) => setErr(errMessage(e)))

    api.get('/forms', { params: { page_size: 100 } }).then((r) => setForms(r.data.items.filter((f: any) => f.current_version_status === 'published'))).catch(() => {})
    api.get('/roles').then((r) => setRoles(r.data)).catch(() => {})
    if (hasPermission('user.manage')) api.get('/users', { params: { page_size: 100 } }).then((r) => setUsers(r.data.items)).catch(() => {})
    return () => { if (modelerRef.current) { modelerRef.current.destroy(); modelerRef.current = null } }
  }, [id])

  const refreshInstances = async () => {
    const r = await api.get('/processes/' + id)
    setInstances(r.data.recent_instances || [])
  }

  const saveDiagram = async () => {
    setErr(''); setOk('')
    try {
      const { xml } = await modelerRef.current.saveXML({ format: true })
      let svg = null
      try { svg = (await modelerRef.current.saveSVG()).svg } catch { /* ignore */ }
      await api.put(`/process-versions/${version.id}/diagram`, { bpmn_xml: xml, svg })
      setOk('نمودار ذخیره شد')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const validate = async () => {
    setErr(''); setOk('')
    try {
      const r = await api.post(`/process-versions/${version.id}/validate`)
      setAnalysis(r.data)
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const publish = async () => {
    setErr(''); setOk(''); setAnalysis(null)
    try {
      await saveDiagramSilent()
      const r = await api.post(`/process-versions/${version.id}/publish`)
      setOk(`نسخه v${r.data.version_number} منتشر شد`)
      await loadVersion(version.id)
      const p = await api.get('/processes/' + id)
      setProc(p.data)
    } catch (e: any) {
      const d = e?.response?.data
      if (d?.details?.unsupported) setAnalysis({ unsupported: d.details.unsupported })
      setErr(errMessage(e))
    }
  }

  const saveDiagramSilent = async () => {
    const { xml } = await modelerRef.current.saveXML({ format: true })
    let svg = null
    try { svg = (await modelerRef.current.saveSVG()).svg } catch { /* ignore */ }
    await api.put(`/process-versions/${version.id}/diagram`, { bpmn_xml: xml, svg })
  }

  const newVersion = async () => {
    try {
      await api.post(`/processes/${id}/versions`, {})
      window.location.reload()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const updateBinding = (nodeId: string, patch: any) => {
    setBindings((b: any) => ({ ...b, [nodeId]: { ...(b[nodeId] || {}), node_id: nodeId, ...patch } }))
  }

  const saveBindings = async () => {
    setErr(''); setOk('')
    try {
      const list = Object.values(bindings).filter((b: any) => b && (b.form_version_id || b.role_id || b.assignee_id || b.condition))
      for (const b of list as any[]) {
        if (!b.node_type) {
          b.node_type = selectedNodeTypeGuess(b.node_id)
        }
      }
      await api.put(`/process-versions/${version.id}/bindings`, { bindings: list })
      setOk('اتصال گره‌ها ذخیره شد')
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const selectedNodeTypeGuess = (nodeId: string) => {
    if (nodeId.startsWith('Flow')) return 'sequenceFlow'
    return 'userTask'
  }

  const startInstance = async () => {
    setErr(''); setOk('')
    try {
      const variables = JSON.parse(startVars || '{}')
      const r = await api.post(`/process-versions/${version.id}/instances`, { variables })
      setShowStart(false)
      setOk(`نمونه با کد پیگیری ${r.data.trace_code} آغاز شد`)
      refreshInstances()
    } catch (e: any) { setErr(errMessage(e)) }
  }

  const openInstance = async (instId: string) => {
    const r = await api.get(`/process-instances/${instId}`)
    setInstDetail(r.data)
  }

  const canEdit = version?.status !== 'published' && hasPermission('process.create')
  const nodeBinding = selectedNode ? (bindings[selectedNode.id] || {}) : null
  const isFlow = selectedNode?.type === 'sequenceFlow' || (selectedNode?.id || '').startsWith('Flow')

  return (
    <div>
      <div className="page-header">
        <h1>
          {proc?.title || '…'} <span className="mono muted">({proc?.code})</span>
          {version && <span className="badge" style={{ marginRight: 8 }}>v{version.version_number}</span>}
          {version && <StatusBadge status={version.status} />}
        </h1>
        <div className="actions">
          {canEdit && <button className="btn secondary" onClick={saveDiagram}>ذخیره نمودار</button>}
          <button className="btn secondary" onClick={validate}>اعتبارسنجی</button>
          {hasPermission('process.publish') && canEdit && <button className="btn" onClick={publish}>انتشار نسخه</button>}
          {hasPermission('process.create') && !canEdit && <button className="btn" onClick={newVersion}>نسخه جدید</button>}
          {version?.status === 'published' && hasPermission('process.start') && (
            <button className="btn warn" onClick={() => setShowStart(true)}>شروع اجرا</button>
          )}
        </div>
      </div>
      {err && <Alert kind="error">{err}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}
      {version?.status === 'published' && (
        <Alert kind="info">نسخه منتشرشده تغییرناپذیر است. برای ویرایش، «نسخه جدید» بسازید — اجراهای قبلی تحت تأثیر قرار نمی‌گیرند.</Alert>
      )}

      {analysis && (
        <div className="card">
          <h2>نتیجه اعتبارسنجی</h2>
          {analysis.errors?.length === 0 && analysis.unsupported?.length === 0 && (
            <Alert kind="ok">ساختار نمودار معتبر و در دامنه اجرای موتور است.</Alert>
          )}
          {analysis.errors?.map((e: string, i: number) => <Alert key={i} kind="error">{e}</Alert>)}
          {analysis.warnings?.map((w: string, i: number) => <Alert key={i} kind="warn">{w}</Alert>)}
          {analysis.unsupported?.length > 0 && (
            <Alert kind="warn">
              عناصر خارج از دامنه اجرای موتور (قابل طراحی‌اند ولی اجرای خودکار نمی‌شوند — بخش ۴.۲ سند):
              <ul style={{ margin: '6px 18px 0 0' }}>
                {analysis.unsupported.map((u: any, i: number) => (
                  <li key={i}><b>{u.name || u.node_id}</b>: {u.message}</li>
                ))}
              </ul>
            </Alert>
          )}
        </div>
      )}

      <div className="tabs">
        <button className={tab === 'diagram' ? 'active' : ''} onClick={() => setTab('diagram')}>نمودار BPMN</button>
        <button className={tab === 'profile' ? 'active' : ''} onClick={() => setTab('profile')}>شناسنامه فرایند</button>
        <button className={tab === 'versions' ? 'active' : ''} onClick={() => setTab('versions')}>نسخه‌ها</button>
        <button className={tab === 'instances' ? 'active' : ''} onClick={() => setTab('instances')}>اجراها</button>
      </div>

      {tab === 'diagram' && version && (
        <div className="grid-2" style={{ gridTemplateColumns: '1fr 300px', alignItems: 'start' }}>
          <div>
            <div className="bpmn-toolbar">
              <span className="muted">عناصر را از پالت سمت چپ بکشید؛ با انتخاب هر گره، تنظیمات آن در پنل کنار ظاهر می‌شود.</span>
            </div>
            <div className="bpmn-wrap" ref={canvasRef} />
          </div>
          <div className="card">
            <h3>{selectedNode ? `تنظیمات گره: ${selectedNode.name}` : 'تنظیمات گره'}</h3>
            {!selectedNode && <div className="muted">روی یک گره در نمودار کلیک کنید.</div>}
            {selectedNode && nodeBinding && !isFlow && selectedNode.type === 'userTask' && (
              <>
                <div className="field"><label>فرم مرحله (نسخه منتشرشده)</label>
                  <select className="select" value={nodeBinding.form_version_id || ''}
                    onChange={(e) => updateBinding(selectedNode.id, { form_version_id: e.target.value || null })}>
                    <option value="">— بدون فرم —</option>
                    {forms.map((f) => (
                      <option key={f.current_version_id} value={f.current_version_id}>{f.title} (v{f.current_version_number})</option>
                    ))}
                  </select></div>
                <div className="field"><label>نقش مجری</label>
                  <select className="select" value={nodeBinding.role_id || ''}
                    onChange={(e) => updateBinding(selectedNode.id, { role_id: e.target.value || null })}>
                    <option value="">— بدون نقش —</option>
                    {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select></div>
                {users.length > 0 && (
                  <div className="field"><label>کاربر مجری مشخص</label>
                    <select className="select" value={nodeBinding.assignee_id || ''}
                      onChange={(e) => updateBinding(selectedNode.id, { assignee_id: e.target.value || null })}>
                      <option value="">— انتخاب نشده —</option>
                      {users.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
                    </select></div>
                )}
              </>
            )}
            {selectedNode && (selectedNode.type === 'exclusiveGateway') && (
              <Alert kind="info">
                شرط مسیرهای خروجی این gateway را روی خودِ یال‌ها (خطوط) تنظیم کنید — روی خط کلیک کنید.
              </Alert>
            )}
            {selectedNode && isFlow && (
              <div className="field"><label>شرط مسیر (مثال: review_result == "yes")</label>
                <input className="input" dir="ltr" value={nodeBinding.condition || ''}
                  onChange={(e) => updateBinding(selectedNode.id, { condition: e.target.value })} />
                <div className="muted">در صورتی که شرط در XML تعریف شده باشد، همان استفاده می‌شود.</div>
              </div>
            )}
            {selectedNode && selectedNode.type !== 'userTask' && !isFlow && selectedNode.type !== 'exclusiveGateway' && (
              <Alert kind="info">این نوع گره تنظیم اجرایی خاصی ندارد.</Alert>
            )}
            {canEdit && (selectedNode?.type === 'userTask' || isFlow) && (
              <button className="btn small" onClick={saveBindings}>ذخیره اتصال این گره</button>
            )}
          </div>
        </div>
      )}

      {tab === 'profile' && proc && (
        <div className="card">
          <dl className="kv">
            <dt>کد فرایند</dt><dd className="mono">{proc.code}</dd>
            <dt>هدف</dt><dd>{proc.purpose || '—'}</dd>
            <dt>توضیح</dt><dd>{proc.description || '—'}</dd>
            <dt>دسته‌بندی</dt><dd>{proc.category || '—'}</dd>
            <dt>واحد سازمانی</dt><dd>{proc.unit || '—'}</dd>
            <dt>مالک فرایند</dt><dd>{proc.owner?.full_name || '—'}</dd>
            <dt>مدت مورد انتظار</dt><dd>{proc.expected_duration_days ? `${proc.expected_duration_days} روز` : '—'}</dd>
            <dt>سطح محرمانگی</dt><dd>{proc.confidentiality}</dd>
          </dl>
        </div>
      )}

      {tab === 'versions' && proc && (
        <div className="card">
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>نسخه</th><th>وضعیت</th><th>ایجاد</th><th>انتشار</th><th></th></tr></thead>
              <tbody>
                {proc.versions.map((v: any) => (
                  <tr key={v.id}>
                    <td>v{v.version_number}</td>
                    <td><StatusBadge status={v.status} /></td>
                    <td>{faDate(v.created_at)}</td>
                    <td>{faDate(v.published_at)}</td>
                    <td>{v.id === version?.id ? <span className="badge approved">فعلی</span> :
                      <button className="btn small secondary" onClick={() => loadVersion(v.id)}>مشاهده</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'instances' && (
        <div className="card">
          {instances.length === 0 && <Empty text="اجرایی ثبت نشده است" />}
          {instances.length > 0 && (
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr><th>کد پیگیری</th><th>عنوان</th><th>وضعیت</th><th>شروع</th><th>پایان</th><th></th></tr></thead>
                <tbody>
                  {instances.map((i: any) => (
                    <tr key={i.id}>
                      <td className="mono">{i.trace_code}</td>
                      <td>{i.title || '—'}</td>
                      <td><StatusBadge status={i.status} /></td>
                      <td>{faDate(i.started_at, true)}</td>
                      <td>{faDate(i.ended_at, true)}</td>
                      <td><button className="btn small secondary" onClick={() => openInstance(i.id)}>جزئیات</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showStart && (
        <Modal title="شروع اجرای فرایند" onClose={() => setShowStart(false)}>
          <Alert kind="info">متغیرهای اولیه را به‌صورت JSON وارد کنید (در صورت وجود، از فرم مرحله اول تکمیل می‌شود).</Alert>
          <textarea className="textarea" dir="ltr" rows={5} value={startVars} onChange={(e) => setStartVars(e.target.value)} />
          <div className="modal-actions">
            <button className="btn" onClick={startInstance}>شروع</button>
            <button className="btn secondary" onClick={() => setShowStart(false)}>انصراف</button>
          </div>
        </Modal>
      )}

      {instDetail && (
        <Modal title={`اجرا ${instDetail.trace_code}`} onClose={() => setInstDetail(null)} wide>
          <div className="grid-2">
            <div>
              <h3>وظایف</h3>
              {instDetail.tasks.map((t: any) => (
                <div key={t.id} className="canvas-field" style={{ cursor: 'default' }}>
                  <div className="cf-head">
                    <b>{t.node_name || t.node_id}</b>
                    <StatusBadge status={t.status} />
                  </div>
                  <div className="cf-meta">ایجاد: {faDate(t.created_at, true)}</div>
                </div>
              ))}
            </div>
            <div>
              <h3>تاریخچه رویدادها</h3>
              <div className="timeline">
                {instDetail.events.map((e: any, i: number) => (
                  <div className="tl-item" key={i}>
                    <b style={{ fontSize: 13 }}>{e.message}</b>
                    <div className="tl-time">{faDate(e.created_at, true)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
