/** کلاینت API فرایارا — مدیریت توکن، تازه‌سازی خودکار و خطاها */
import axios from 'axios'

const BASE = '/api/v1'

export const api = axios.create({ baseURL: BASE })

let accessToken = localStorage.getItem('fr_access') || ''
let refreshToken = localStorage.getItem('fr_refresh') || ''
let currentUser: any = null
try {
  const raw = localStorage.getItem('fr_user')
  currentUser = raw ? JSON.parse(raw) : null
} catch {
  currentUser = null
}

export function setSession(access: string, refresh: string, user: any) {
  accessToken = access
  refreshToken = refresh
  currentUser = user
  localStorage.setItem('fr_access', access)
  localStorage.setItem('fr_refresh', refresh)
  localStorage.setItem('fr_user', JSON.stringify(user))
}

export function clearSession() {
  accessToken = ''
  refreshToken = ''
  currentUser = null
  localStorage.removeItem('fr_access')
  localStorage.removeItem('fr_refresh')
  localStorage.removeItem('fr_user')
}

export function getSession() {
  return { accessToken, refreshToken, currentUser, isLoggedIn: !!accessToken }
}

export function hasPermission(code: string): boolean {
  if (!currentUser) return false
  const perms: string[] = currentUser.permissions || []
  return perms.includes('system.admin') || perms.includes(code)
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

let refreshing: Promise<string | null> | null = null

async function tryRefresh(): Promise<string | null> {
  if (!refreshToken) return null
  if (!refreshing) {
    refreshing = axios
      .post(`${BASE}/auth/refresh`, { refresh_token: refreshToken })
      .then((r) => {
        accessToken = r.data.access_token
        refreshToken = r.data.refresh_token
        localStorage.setItem('fr_access', accessToken)
        localStorage.setItem('fr_refresh', refreshToken)
        return accessToken
      })
      .catch(() => null)
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retried) {
      original._retried = true
      const token = await tryRefresh()
      if (token) {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }
      clearSession()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export function errMessage(e: any): string {
  const d = e?.response?.data
  if (!d) return e?.message || 'خطای شبکه'
  if (typeof d === 'string') return d
  if (d.message) {
    if (d.details) {
      const det = d.details
      if (Array.isArray(det)) return det.join('؛ ')
      if (typeof det === 'object' && det.missing) return `${d.message}: ${det.missing.join('، ')}`
      return `${d.message} — ${JSON.stringify(det)}`
    }
    return d.message
  }
  return JSON.stringify(d)
}

/** قالب‌بندی تاریخ شمسی از ISO UTC */
export function faDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  try {
    const date = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
      year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(d)
    if (!withTime) return date
    const time = new Intl.DateTimeFormat('fa-IR', { hour: '2-digit', minute: '2-digit' }).format(d)
    return `${date} - ${time}`
  } catch {
    return d.toLocaleString('fa-IR')
  }
}

export const STATUS_LABELS: Record<string, string> = {
  draft: 'پیش‌نویس', review: 'در حال بررسی', approved: 'تأییدشده',
  published: 'منتشرشده', retired: 'بازنشسته',
  running: 'در حال اجرا', completed: 'تکمیل‌شده', cancelled: 'لغوشده', suspended: 'موقتاً متوقف',
  pending: 'در انتظار', final: 'نهایی',
  active: 'فعال', inactive: 'غیرفعال', archived: 'بایگانی',
  not_started: 'شروع‌نشده', in_progress: 'در حال تکمیل',
  validated: 'اعتبارسنجی‌شده', owned: 'دارای مجوز', licensed: 'مجوز خریداری‌شده',
  public_domain: 'مالکیت عمومی', unknown: 'نامشخص', restricted: 'محدود',
}
