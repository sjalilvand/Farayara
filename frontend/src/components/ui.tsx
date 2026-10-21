/** اجزای عمومی رابط کاربری */
import { ReactNode } from 'react'
import { STATUS_LABELS } from '../api/client'

export function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return <span className="badge neutral">—</span>
  return <span className={`badge ${status}`}>{STATUS_LABELS[status] || status}</span>
}

export function Modal({
  title, onClose, children, wide,
}: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  )
}

export function Alert({ kind, children }: { kind: 'error' | 'ok' | 'warn' | 'info'; children: ReactNode }) {
  return <div className={`alert ${kind}`}>{children}</div>
}

export function Pager({
  page, pageSize, total, onPage,
}: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  return (
    <div className="pagination">
      <button className="btn small secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        قبلی
      </button>
      <span className="muted">
        صفحه {page.toLocaleString('fa-IR')} از {pages.toLocaleString('fa-IR')} — مجموع{' '}
        {total.toLocaleString('fa-IR')}
      </span>
      <button className="btn small secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        بعدی
      </button>
    </div>
  )
}

export function Empty({ text = 'موردی یافت نشد' }: { text?: string }) {
  return <div className="empty-state">{text}</div>
}

export function Loading() {
  return <div className="empty-state">در حال بارگذاری…</div>
}
