/** رندرکننده مشترک فرم‌ها — بر اساس schema_json + اعتبارسنجی سمت کلاینت */
import { useMemo, useState } from 'react'

export type FormFieldDef = {
  key: string
  field_id?: string | null
  type?: string
  label: string
  required?: boolean
  help?: string
  validations?: { pattern?: string; min?: number; max?: number; options?: string[] }
  options?: string[]
}

export type FormSchema = { fields: FormFieldDef[]; layout?: { columns?: number } }

/** اعتبارسنجی کد ملی (الگوریتمchecksum) */
export function validNationalCode(code: string): boolean {
  if (!/^[0-9]{10}$/.test(code)) return false
  const check = +code[9]
  const sum = code.split('').slice(0, 9).reduce((acc, d, i) => acc + +d * (10 - i), 0) % 11
  return sum < 2 ? check === sum : check === 11 - sum
}

export function validateField(f: FormFieldDef, value: any): string | null {
  const empty = value === undefined || value === null || value === '' ||
    (Array.isArray(value) && value.length === 0)
  if (f.required && empty) return 'این فیلد الزامی است'
  if (empty) return null
  const s = String(value)
  if (f.type === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s)) return 'نشانی ایمیل معتبر نیست'
  if ((f.type === 'phone' || f.type === 'national_code' || f.type === 'mobile') && f.type !== undefined) {
    if (s.includes('ملی') || f.validations?.pattern?.includes('10')) { /* handled by pattern */ }
  }
  if (f.validations?.pattern && !new RegExp(f.validations.pattern).test(s)) return 'قالب مقدار معتبر نیست'
  if (f.validations?.min !== undefined && parseFloat(s) < f.validations.min) return `حداقل ${f.validations.min}`
  if (f.validations?.max !== undefined && parseFloat(s) > f.validations.max) return `حداکثر ${f.validations.max}`
  if (s.length > 0 && f.validations?.pattern === undefined) {
    // کد ملی بدون الگو
  }
  return null
}

export default function FormRenderer({
  schema, values, onChange, errors,
}: {
  schema: FormSchema
  values: Record<string, any>
  onChange: (key: string, value: any) => void
  errors: Record<string, string>
}) {
  const fields = schema?.fields || []
  if (!fields.length) return <div className="empty-state">این فرم هنوز فیلدی ندارد.</div>

  const inputType = (t?: string) => {
    switch (t) {
      case 'number': case 'money': case 'percent': return 'number'
      case 'date': return 'date'
      case 'email': return 'email'
      case 'phone': return 'tel'
      case 'url': return 'url'
      case 'time': return 'time'
      default: return 'text'
    }
  }

  const renderField = (f: FormFieldDef) => {
    const value = values[f.key] ?? ''
    const t = f.type || 'text'
    let control: React.ReactNode

    if (t === 'textarea') {
      control = <textarea className="textarea" value={value} onChange={(e) => onChange(f.key, e.target.value)} />
    } else if (t === 'yes_no') {
      control = (
        <label className="inline-flex">
          <input type="checkbox" checked={value === true || value === 'yes'} style={{ width: 18, height: 18 }}
            onChange={(e) => onChange(f.key, e.target.checked ? 'yes' : 'no')} />
          <span>بله</span>
        </label>
      )
    } else if (t === 'select' || t === 'multiselect') {
      const opts = f.options || f.validations?.options || []
      if (t === 'multiselect') {
        control = (
          <select className="select" multiple value={Array.isArray(value) ? value : []}
            onChange={(e) => onChange(f.key, Array.from(e.target.selectedOptions).map((o) => o.value))}>
            {opts.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        )
      } else {
        control = (
          <select className="select" value={value} onChange={(e) => onChange(f.key, e.target.value)}>
            <option value="">— انتخاب کنید —</option>
            {opts.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        )
      }
    } else if (t === 'national_code') {
      control = (
        <input className="input" dir="ltr" maxLength={10} value={value}
          onChange={(e) => onChange(f.key, e.target.value.replace(/[^0-9]/g, ''))} />
      )
    } else {
      control = (
        <input className="input" type={inputType(t)} value={value} dir={t === 'text' || t === 'textarea' ? 'auto' : 'ltr'}
          onChange={(e) => onChange(f.key, e.target.value)} />
      )
    }

    return (
      <div className="field" key={f.key}>
        <label>
          {f.label} {f.required && <span className="req">*</span>}
        </label>
        {control}
        {f.help && <div className="muted" style={{ marginTop: 3 }}>{f.help}</div>}
        {errors[f.key] && <div className="muted" style={{ color: 'var(--danger)' }}>{errors[f.key]}</div>}
      </div>
    )
  }

  const cols = schema.layout?.columns || 1
  return (
    <div className={cols === 2 ? 'grid-2' : ''}>
      {fields.map(renderField)}
    </div>
  )
}

export function validateAll(schema: FormSchema, values: Record<string, any>): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const f of schema?.fields || []) {
    const msg = validateField(f, values[f.key])
    if (msg) errors[f.key] = msg
  }
  return errors
}
