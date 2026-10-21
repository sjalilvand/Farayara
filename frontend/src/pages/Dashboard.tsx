import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, faDate } from '../api/client'
import { Loading } from '../components/ui'

const COLORS = ['#0f766e', '#b45309', '#0369a1', '#7c3aed', '#dc2626', '#16a34a']

const STATUS_FA: Record<string, string> = {
  draft: 'پیش‌نویس', published: 'منتشرشده', review: 'در بررسی', retired: 'بازنشسته',
  approved: 'تأییدشده',
}

export default function Dashboard() {
  const [data, setData] = useState<any>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/dashboards/overview').then((r) => setData(r.data)).catch((e) => setErr(String(e?.response?.data?.message || e.message)))
  }, [])

  if (err) return <div className="alert error">{err}</div>
  if (!data) return <Loading />

  const c = data.counts
  const stats = [
    { lbl: 'فرایندها', num: c.processes, sub: `${c.processes_published_versions} نسخه منتشرشده` },
    { lbl: 'فرم‌ها', num: c.forms, sub: `${c.forms_published_versions} نسخه منتشرشده` },
    { lbl: 'فیلدهای فعال', num: c.fields_active, sub: 'کاتالوگ داده' },
    { lbl: 'پاسخ‌های ثبت‌شده', num: c.submissions, sub: 'پاسخ نهایی' },
    { lbl: 'اجرای آزمون', num: c.assessment_administrations, sub: `${c.assessments} آزمون` },
    { lbl: 'قراردادها', num: c.contracts, sub: `${c.contract_templates} الگو` },
    { lbl: 'وظایف باز', num: c.open_tasks, sub: 'در کل سامانه' },
    { lbl: 'وظایف من', num: c.my_open_tasks, sub: 'در کارتابل من' },
  ]

  const pie = data.charts.process_version_status.map((x: any) => ({
    name: STATUS_FA[x.status] || x.status, value: x.count,
  }))

  return (
    <div>
      <div className="page-header">
        <h1>داشبورد عمومی</h1>
        <div className="muted">به‌روزرسانی: {faDate(new Date().toISOString(), true)}</div>
      </div>

      <div className="stat-cards">
        {stats.map((s) => (
          <div className="stat-card" key={s.lbl}>
            <div className="num">{s.num.toLocaleString('fa-IR')}</div>
            <div className="lbl">{s.lbl}</div>
            <div className="muted">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>روند پاسخ‌های ۱۴ روز اخیر</h2>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.charts.submissions_trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" name="پاسخ" fill="#0f766e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h2>وضعیت نسخه‌های فرایند</h2>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85}>
                  {pie.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>پراستفاده‌ترین فیلدهای کاتالوگ (تعداد فرم‌های منطقی متمایز)</h2>
        {data.charts.top_fields.length === 0 && <div className="muted">داده‌ای نیست.</div>}
        <div className="chart-box" style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.charts.top_fields} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="title" width={150} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="forms_count" name="تعداد فرم‌ها" fill="#b45309" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="muted">برای جزئیات هر فیلد به <Link to="/catalog">کاتالوگ داده</Link> مراجعه کنید.</div>
      </div>
    </div>
  )
}
