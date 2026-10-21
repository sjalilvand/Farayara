"""مدل‌های داده فرایارا — مطابق بخش ۱۷ سند طراحی

قواعد عمومی داده:
- شناسه داخلی (UUID) از کد نمایشی (PRC-000001 و ...) جدا است.
- تاریخ‌ها به‌صورت UTC (ISO 8601) ذخیره می‌شوند.
- روابط با کلید خارجی کنترل می‌شوند.
- نسخه‌های منتشرشده تغییرناپذیرند (در لایه API کنترل می‌شود).
- حذف منابع تاریخی به‌صورت منطقی (is_archived / status) انجام می‌شود.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================================================================
# ۱۷.۱ هویت و دسترسی
# =====================================================================

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str | None] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions", lazy="selectin")


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    group: Mapped[str | None] = mapped_column(String(80))


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


# =====================================================================
# ۱۷.۲ فرایندها
# =====================================================================

class Process(Base):
    """شناسنامه فرایند (بخش ۴.۳)"""
    __tablename__ = "processes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # PRC-000125
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    unit: Mapped[str | None] = mapped_column(String(200))
    inputs_desc: Mapped[str | None] = mapped_column(Text)
    outputs_desc: Mapped[str | None] = mapped_column(Text)
    expected_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidentiality: Mapped[str] = mapped_column(String(30), default="internal")  # public/internal/confidential
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)  # active/archived
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class ProcessVersion(Base):
    """نسخه فرایند — XML و مشخصات اجرایی (بخش ۴.۴ و ۴.۵)"""
    __tablename__ = "process_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    process_id: Mapped[str] = mapped_column(ForeignKey("processes.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    bpmn_xml: Mapped[str | None] = mapped_column(Text)
    exec_config: Mapped[dict | None] = mapped_column(JSON, default=dict)
    diagram_svg: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    # draft → review → approved → published → retired
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(36))

    __table_args__ = (UniqueConstraint("process_id", "version_number", name="uq_process_version"),)


class ProcessNodeBinding(Base):
    """اتصال گره‌های فرایند به فرم، نقش و شرایط مسیر (بخش ۴.۴)"""
    __tablename__ = "process_node_bindings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    process_version_id: Mapped[str] = mapped_column(ForeignKey("process_versions.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(120))  # شناسه گره در BPMN XML
    node_type: Mapped[str] = mapped_column(String(60))  # userTask / sequenceFlow / callActivity ...
    node_name: Mapped[str | None] = mapped_column(String(300))
    form_version_id: Mapped[str | None] = mapped_column(ForeignKey("form_versions.id"))
    role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"))
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    condition: Mapped[str | None] = mapped_column(Text)  # شرط مسیر برای sequenceFlowهای خروجی gateway
    config: Mapped[dict | None] = mapped_column(JSON, default=dict)

    __table_args__ = (UniqueConstraint("process_version_id", "node_id", name="uq_node_binding"),)


class ProcessInstance(Base):
    """نمونه اجرای فرایند (بخش ۵)"""
    __tablename__ = "process_instances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    trace_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # کد پیگیری
    process_id: Mapped[str] = mapped_column(ForeignKey("processes.id"), index=True)
    process_version_id: Mapped[str] = mapped_column(ForeignKey("process_versions.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)  # running/completed/cancelled/suspended
    current_node_id: Mapped[str | None] = mapped_column(String(120))
    variables: Mapped[dict | None] = mapped_column(JSON, default=dict)
    started_by: Mapped[str | None] = mapped_column(String(36))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProcessTask(Base):
    """وظایف کاربری در اجرای فرایند"""
    __tablename__ = "process_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instance_id: Mapped[str] = mapped_column(ForeignKey("process_instances.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(120))
    node_name: Mapped[str | None] = mapped_column(String(300))
    form_version_id: Mapped[str | None] = mapped_column(ForeignKey("form_versions.id"))
    role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"))
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending/completed/cancelled
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(36))
    payload: Mapped[dict | None] = mapped_column(JSON, default=dict)

    instance: Mapped["ProcessInstance"] = relationship(foreign_keys=[instance_id])

    __table_args__ = (Index("ix_task_status_assignee", "status", "assignee_id"),)


class ProcessEvent(Base):
    """تاریخچه و رویدادهای اجرا — تمام تغییرات مسیر قابل ممیزی (بخش ۵.۳)"""
    __tablename__ = "process_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instance_id: Mapped[str] = mapped_column(ForeignKey("process_instances.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(60))  # started/task_created/task_completed/flow_taken/completed/cancelled/suspended/error
    node_id: Mapped[str | None] = mapped_column(String(120))
    message: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


# =====================================================================
# ۱۷.۳ فرم و کاتالوگ
# =====================================================================

class FieldDefinition(Base):
    """فیلد مرجع کاتالوگ داده (بخش ۷)"""
    __tablename__ = "field_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # FLD-000481
    tech_name: Mapped[str] = mapped_column(String(100), unique=True)  # mobile_number
    title_fa: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    aliases: Mapped[list | None] = mapped_column(JSON, default=list)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    sensitivity: Mapped[str] = mapped_column(String(30), default="normal")  # normal/sensitive/highly_sensitive
    is_identity: Mapped[bool] = mapped_column(Boolean, default=False)
    is_health: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_policy: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)  # draft/active/inactive
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class FieldDefinitionVersion(Base):
    """نسخه فیلد — نوع و قواعد اعتبارسنجی (تغییر نوع فیلد منتشرشده = نسخه جدید)"""
    __tablename__ = "field_definition_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    field_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    data_type: Mapped[str] = mapped_column(String(40))
    # text/textarea/number/decimal/money/percent/date/time/select/multiselect/yes_no/email/phone/url/national_code/file/repeat_group/computed/hidden
    validation_rules: Mapped[dict | None] = mapped_column(JSON, default=dict)  # {pattern, min, max, required}
    allowed_values: Mapped[list | None] = mapped_column(JSON, default=list)  # دامنه مقادیر مجاز
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    __table_args__ = (UniqueConstraint("field_id", "version_number", name="uq_field_version"),)


class FieldAlias(Base):
    """نام‌های مترادف فیلد مرجع — برای پیشنهاد و جست‌وجو"""
    __tablename__ = "field_aliases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    field_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(300))


class Form(Base):
    """شناسنامه فرم (بخش ۶.۳)"""
    __tablename__ = "forms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # FRM-000235
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    confidentiality: Mapped[str] = mapped_column(String(30), default="internal")
    audience: Mapped[str | None] = mapped_column(String(200))  # مخاطب/تکمیل‌کننده
    language: Mapped[str] = mapped_column(String(10), default="fa")
    retention_policy: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class FormVersion(Base):
    """نسخه فرم — schema/ui/rules (بخش ۶.۴)"""
    __tablename__ = "form_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    form_id: Mapped[str] = mapped_column(ForeignKey("forms.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    schema_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    ui_schema_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    rules_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)  # draft/published/retired
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(36))
    change_note: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (UniqueConstraint("form_id", "version_number", name="uq_form_version"),)


class FormFieldUsage(Base):
    """نمونه استفاده از فیلد مرجع در یک نسخه فرم (بخش ۷.۱ — دو موجودیت جدا)"""
    __tablename__ = "form_field_usages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    form_version_id: Mapped[str] = mapped_column(ForeignKey("form_versions.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("field_definitions.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(120))  # کلید فیلد داخل schema فرم
    label_override: Mapped[str | None] = mapped_column(String(300))  # عنوان نمایشی مخصوص این فرم
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict | None] = mapped_column(JSON, default=dict)

    __table_args__ = (Index("ix_usage_field", "field_id"),)


class FormSubmission(Base):
    """پاسخ فرم — تصویر کامل JSON + کد رهگیری (بخش ۸)"""
    __tablename__ = "form_submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    trace_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    form_version_id: Mapped[str] = mapped_column(ForeignKey("form_versions.id"), index=True)
    submitted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    respondent_name: Mapped[str | None] = mapped_column(String(200))
    process_instance_id: Mapped[str | None] = mapped_column(String(36), index=True)
    process_task_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(30), default="final", index=True)  # draft/final
    data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    rules_version: Mapped[str | None] = mapped_column(String(60))
    consent_id: Mapped[str | None] = mapped_column(String(36))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    ip_address: Mapped[str | None] = mapped_column(String(60))


class SubmissionFieldValue(Base):
    """مقادیر قابل گزارش پاسخ‌ها — برای جست‌وجو، فراوانی و گزارش (بخش ۸)"""
    __tablename__ = "submission_field_values"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("form_submissions.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str | None] = mapped_column(String(36), index=True)
    field_key: Mapped[str] = mapped_column(String(120))
    value_text: Mapped[str | None] = mapped_column(Text)
    value_number: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_date: Mapped[str | None] = mapped_column(String(30))
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_empty: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (Index("ix_sfv_field", "field_id", "is_empty"),)


class SubmissionRevision(Base):
    """اصلاحات پاسخ — پاسخ نهایی بدون سابقه تغییر نمی‌کند (بخش ۸)"""
    __tablename__ = "submission_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("form_submissions.id", ondelete="CASCADE"), index=True)
    revised_by: Mapped[str | None] = mapped_column(String(36))
    reason: Mapped[str | None] = mapped_column(String(500))
    old_data: Mapped[dict | None] = mapped_column(JSON)
    new_data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


# =====================================================================
# ۱۷.۴ آزمون‌ها
# =====================================================================

class Assessment(Base):
    """شناسنامه آزمون (بخش ۹.۱)"""
    __tablename__ = "assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # ASM-000010
    title_fa: Mapped[str] = mapped_column(String(300))
    title_original: Mapped[str | None] = mapped_column(String(300))  # نام اصلی
    abbreviation: Mapped[str | None] = mapped_column(String(60))
    domain: Mapped[str | None] = mapped_column(String(200))  # حوزه کاربرد
    author: Mapped[str | None] = mapped_column(String(200))  # مؤلف
    publisher: Mapped[str | None] = mapped_column(String(200))  # ناشر/دارنده حقوق
    rights_holder: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(60))
    target_group: Mapped[str | None] = mapped_column(String(200))  # گروه سنی/جامعه هدف
    item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answer_mode: Mapped[str | None] = mapped_column(String(60))  # self/other/mixed
    scoring_method: Mapped[str | None] = mapped_column(String(120))
    scientific_references: Mapped[str | None] = mapped_column(Text)  # منابع علمی
    norms_notes: Mapped[str | None] = mapped_column(Text)  # مشخصات هنجارها
    limitations: Mapped[str | None] = mapped_column(Text)  # محدودیت‌ها
    license_terms: Mapped[str | None] = mapped_column(Text)  # شرایط مجوز
    license_status: Mapped[str] = mapped_column(String(40), default="unknown")  # owned/licensed/public_domain/unknown/restricted
    approved_scientific: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_legal: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_scientific_by: Mapped[str | None] = mapped_column(String(200))
    approved_legal_by: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class AssessmentVersion(Base):
    """نسخه آزمون — سؤال‌ها، قواعد نمره‌گذاری، هنجار و گزارش مستقل (بخش ۹.۲)"""
    __tablename__ = "assessment_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    year: Mapped[str | None] = mapped_column(String(20))
    language: Mapped[str | None] = mapped_column(String(60))
    items_config: Mapped[dict | None] = mapped_column(JSON, default=dict)  # {option_values, missing_policy, reverse_items, validity}
    scoring_rules: Mapped[dict | None] = mapped_column(JSON, default=dict)  # {scales:[{code,title,items,expression,interpretations}]}
    norm_sets: Mapped[list | None] = mapped_column(JSON, default=list)  # جداول هنجار
    report_template: Mapped[str | None] = mapped_column(Text)
    rules_version_note: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)  # draft/validated/published/retired
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    validated_by: Mapped[str | None] = mapped_column(String(200))

    __table_args__ = (UniqueConstraint("assessment_id", "version_number", name="uq_assessment_version"),)


class AssessmentItem(Base):
    """سؤال‌های آزمون"""
    __tablename__ = "assessment_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey("assessment_versions.id", ondelete="CASCADE"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(40))  # q1 ...
    text: Mapped[str] = mapped_column(Text)
    item_type: Mapped[str] = mapped_column(String(40), default="likert")  # likert/mcq/number/text
    is_reverse: Mapped[bool] = mapped_column(Boolean, default=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    options: Mapped[list | None] = mapped_column(JSON, default=list)  # [{value,label,score}]
    scale_codes: Mapped[list | None] = mapped_column(JSON, default=list)

    __table_args__ = (UniqueConstraint("version_id", "code", name="uq_item_code"),)


class AssessmentScale(Base):
    """خرده‌مقیاس‌ها"""
    __tablename__ = "assessment_scales"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey("assessment_versions.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    min_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class AssessmentSource(Base):
    """منابع اینترنتی و مستندات آزمون (بخش ۱۰.۳)"""
    __tablename__ = "assessment_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessments.id"), index=True)
    url: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(String(400))
    author: Mapped[str | None] = mapped_column(String(300))
    publisher: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[str | None] = mapped_column(String(30))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    source_type: Mapped[str | None] = mapped_column(String(60))  # official/paper/website/other
    validation_status: Mapped[str] = mapped_column(String(40), default="pending")  # pending/validated/rejected
    usage_terms: Mapped[str | None] = mapped_column(Text)  # شرایط استفاده
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_fingerprint: Mapped[str | None] = mapped_column(String(200))  # اثر انگشت فایل
    approved_by: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)


class AssessmentAdministration(Base):
    """اجرای آزمون (بخش ۱۱)"""
    __tablename__ = "assessment_administrations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey("assessment_versions.id"), index=True)
    respondent_name: Mapped[str | None] = mapped_column(String(200))
    respondent_identifier: Mapped[str | None] = mapped_column(String(120))
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    conducted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="not_started", index=True)  # not_started/in_progress/completed/cancelled
    answers: Mapped[dict | None] = mapped_column(JSON, default=dict)
    public_token: Mapped[str | None] = mapped_column(String(80), unique=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AssessmentScoreRun(Base):
    """اجرای محاسبه نمره — تغییر قواعد نتایج تاریخی را تغییر نمی‌دهد (بخش ۱۱.۳)"""
    __tablename__ = "assessment_score_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    administration_id: Mapped[str] = mapped_column(ForeignKey("assessment_administrations.id", ondelete="CASCADE"), index=True)
    rules_snapshot: Mapped[dict | None] = mapped_column(JSON)  # تصویر قواعد در لحظه محاسبه
    computed: Mapped[dict | None] = mapped_column(JSON)
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AssessmentResult(Base):
    """نتیجه و گزارش آزمون"""
    __tablename__ = "assessment_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    administration_id: Mapped[str] = mapped_column(ForeignKey("assessment_administrations.id", ondelete="CASCADE"), index=True)
    score_run_id: Mapped[str | None] = mapped_column(String(36))
    raw_scores: Mapped[dict | None] = mapped_column(JSON)
    converted_scores: Mapped[dict | None] = mapped_column(JSON)
    interpretations: Mapped[dict | None] = mapped_column(JSON)
    completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    report_text: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AssessmentValidationCase(Base):
    """مثال‌های مرجع اعتبارسنجی نمره‌گذاری (بخش ۱۱.۳)"""
    __tablename__ = "assessment_validation_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey("assessment_versions.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(300))
    input_answers: Mapped[dict | None] = mapped_column(JSON)
    expected: Mapped[dict | None] = mapped_column(JSON)  # {scale_code: expected_score}
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


# =====================================================================
# ۱۷.۵ قراردادها و سامانه
# =====================================================================

class ContractTemplate(Base):
    """الگوی قرارداد (بخش ۱۲)"""
    __tablename__ = "contract_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # CTR-TPL-000042
    title: Mapped[str] = mapped_column(String(300))
    contract_type: Mapped[str | None] = mapped_column(String(120))
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    unit: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class ContractTemplateVersion(Base):
    """نسخه الگو — بدنه HTML، سربرگ و پابرگ"""
    __tablename__ = "contract_template_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    template_id: Mapped[str] = mapped_column(ForeignKey("contract_templates.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    body_html: Mapped[str | None] = mapped_column(Text)
    header_html: Mapped[str | None] = mapped_column(Text)
    footer_html: Mapped[str | None] = mapped_column(Text)
    logo_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)  # draft/published/retired
    legal_approver: Mapped[str | None] = mapped_column(String(200))
    valid_from: Mapped[str | None] = mapped_column(String(30))
    change_note: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("template_id", "version_number", name="uq_template_version"),)


class ContractVariable(Base):
    """متغیرهای قابل جایگذاری در الگو (بخش ۱۲.۳)"""
    __tablename__ = "contract_variables"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    template_id: Mapped[str] = mapped_column(ForeignKey("contract_templates.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(120))  # party_a.full_name
    label: Mapped[str] = mapped_column(String(300))
    data_type: Mapped[str] = mapped_column(String(40), default="text")  # text/number/money/date/duration
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[str | None] = mapped_column(String(500))
    source_form_field_id: Mapped[str | None] = mapped_column(String(36))

    __table_args__ = (UniqueConstraint("template_id", "key", name="uq_template_variable"),)


class Contract(Base):
    """قرارداد واقعی تولیدشده — متن و داده‌ها منجمد می‌شوند (بخش ۱۲.۴)"""
    __tablename__ = "contracts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # CTR-000001
    template_version_id: Mapped[str] = mapped_column(ForeignKey("contract_template_versions.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)  # draft/active/archived/cancelled
    data: Mapped[dict | None] = mapped_column(JSON)  # داده‌های منجمد متغیرها
    body_html: Mapped[str | None] = mapped_column(Text)  # متن منجمد تولیدشده
    file_hash: Mapped[str | None] = mapped_column(String(80))  # SHA-256 سند نهایی
    party_a_name: Mapped[str | None] = mapped_column(String(300))
    party_b_name: Mapped[str | None] = mapped_column(String(300))
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    contract_date: Mapped[str | None] = mapped_column(String(30))
    duration: Mapped[str | None] = mapped_column(String(120))
    generated_by: Mapped[str | None] = mapped_column(String(36))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class ContractRevision(Base):
    """نسخه سند و داده‌های منجمد قرارداد"""
    __tablename__ = "contract_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1)
    body_html: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict | None] = mapped_column(JSON)
    change_note: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class FileObject(Base):
    """مشخصات فایل‌ها — فایل در فضای خصوصی ذخیره و مشخصات در دیتابیس (بخش ۱۷.۶)"""
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    filename: Mapped[str] = mapped_column(String(500))
    stored_path: Mapped[str] = mapped_column(String(1000))
    mime_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String(80))
    related_type: Mapped[str | None] = mapped_column(String(60), index=True)
    related_id: Mapped[str | None] = mapped_column(String(60), index=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AuditLog(Base):
    """لاگ ممیزی — فقط افزودنی؛ در اختیار کاربران عادی برای ویرایش نیست (بخش ۱۹)"""
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_username: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80), index=True)  # login/login_failed/create/update/publish/export/download/...
    entity_type: Mapped[str | None] = mapped_column(String(60), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(60))
    entity_code: Mapped[str | None] = mapped_column(String(60))
    detail: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class BackgroundJob(Base):
    """کارهای پس‌زمینه — وضعیت پایدار، قابل تلاش مجدد و قابل پیگیری (بخش ۱۵.۳)"""
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)  # queued/running/done/failed
    payload: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class Notification(Base):
    """اعلان‌های درون‌برنامه‌ای — وظایف و تأخیرها (بخش ۵.۱)"""
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Consent(Base):
    """رضایت‌نامه (بخش ۱۹)"""
    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject_name: Mapped[str | None] = mapped_column(String(200))
    purpose: Mapped[str | None] = mapped_column(Text)  # هدف جمع‌آوری داده
    body_text: Mapped[str | None] = mapped_column(Text)
    related_type: Mapped[str | None] = mapped_column(String(60))
    related_id: Mapped[str | None] = mapped_column(String(60), index=True)
    given_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(500))


class SystemSetting(Base):
    """تنظیمات سامانه"""
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)
    updated_by: Mapped[str | None] = mapped_column(String(80))


class SequenceCounter(Base):
    """شمارنده کدهای نمایشی (PRC/FRM/FLD/...) — یکتایی در محدوده سامانه"""
    __tablename__ = "sequence_counters"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
