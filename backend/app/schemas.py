"""اسکیماهای ورودی/خروجی Pydantic — مدل‌های اعتبارسنجی درخواست‌ها"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class LoginIn(BaseModel):
    username: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# ---------- Users ----------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6)
    full_name: str
    email: str | None = None
    unit: str | None = None
    role_codes: list[str] = []


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    unit: str | None = None
    is_active: bool | None = None
    role_codes: list[str] | None = None
    password: str | None = None


class RoleIn(BaseModel):
    code: str
    name: str
    description: str | None = None
    permission_codes: list[str] = []


# ---------- Catalog ----------
class FieldCreate(BaseModel):
    tech_name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=100)
    title_fa: str
    description: str | None = None
    data_type: str = "text"
    unit: str | None = None
    validation_rules: dict | None = None
    allowed_values: list | None = None
    category: str | None = None
    aliases: list[str] | None = None
    sensitivity: str = "normal"
    is_identity: bool = False
    is_health: bool = False
    retention_policy: str | None = None


class FieldUpdate(BaseModel):
    title_fa: str | None = None
    description: str | None = None
    data_type: str | None = None
    unit: str | None = None
    validation_rules: dict | None = None
    allowed_values: list | None = None
    category: str | None = None
    aliases: list[str] | None = None
    sensitivity: str | None = None
    is_identity: bool | None = None
    is_health: bool | None = None
    retention_policy: str | None = None


# ---------- Forms ----------
class FormCreate(BaseModel):
    title: str
    description: str | None = None
    purpose: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    confidentiality: str = "internal"
    audience: str | None = None
    retention_policy: str | None = None


class SchemaIn(BaseModel):
    schema_json: dict
    rules_json: dict | None = None
    change_note: str | None = None


class SubmissionIn(BaseModel):
    data: dict
    status: str = "final"  # draft/final
    respondent_name: str | None = None


# ---------- Processes ----------
class ProcessCreate(BaseModel):
    title: str
    description: str | None = None
    purpose: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    unit: str | None = None
    owner_id: str | None = None
    expected_duration_days: int | None = None
    confidentiality: str = "internal"


class DiagramIn(BaseModel):
    bpmn_xml: str
    svg: str | None = None


class BindingsIn(BaseModel):
    bindings: list[dict]


class StartInstanceIn(BaseModel):
    variables: dict | None = None
    title: str | None = None


class CompleteTaskIn(BaseModel):
    data: dict | None = None


# ---------- Assessments ----------
class AssessmentCreate(BaseModel):
    title_fa: str
    title_original: str | None = None
    abbreviation: str | None = None
    domain: str | None = None
    author: str | None = None
    publisher: str | None = None
    rights_holder: str | None = None
    language: str | None = "فارسی"
    target_group: str | None = None
    item_count: int | None = None
    duration_minutes: int | None = None
    answer_mode: str | None = None
    scoring_method: str | None = None
    scientific_references: str | None = None
    norms_notes: str | None = None
    limitations: str | None = None
    license_terms: str | None = None
    license_status: str = "unknown"
    category: str | None = None
    tags: list[str] | None = None


class AssessmentUpdate(BaseModel):
    title_fa: str | None = None
    title_original: str | None = None
    domain: str | None = None
    author: str | None = None
    publisher: str | None = None
    license_terms: str | None = None
    license_status: str | None = None
    norms_notes: str | None = None
    limitations: str | None = None
    scientific_references: str | None = None
    category: str | None = None


class VersionMetaIn(BaseModel):
    year: str | None = None
    language: str | None = None
    note: str | None = None


class AssessmentContentIn(BaseModel):
    items: list[dict] = []
    items_config: dict | None = None
    scoring_rules: dict | None = None
    norm_sets: list | None = None
    report_template: str | None = None
    rules_version_note: str | None = None


class PublishIn(BaseModel):
    approved_scientific_by: str | None = None
    approved_legal_by: str | None = None
    note: str | None = None


class AdministrationIn(BaseModel):
    respondent_name: str | None = None
    respondent_identifier: str | None = None
    assigned_to: str | None = None


class AnswersIn(BaseModel):
    answers: dict


class ValidationCaseIn(BaseModel):
    title: str | None = None
    input_answers: dict
    expected: dict
    note: str | None = None


class DiscoverySearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=200)


class DiscoveryImportIn(BaseModel):
    title_fa: str
    title_original: str | None = None
    domain: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    license_status: str = "unknown"
    license_terms: str | None = None
    note: str | None = None


# ---------- Contracts ----------
class TemplateCreate(BaseModel):
    title: str
    contract_type: str | None = None
    description: str | None = None
    unit: str | None = None


class TemplateBodyIn(BaseModel):
    body_html: str
    header_html: str | None = None
    footer_html: str | None = None
    change_note: str | None = None


class VariablesIn(BaseModel):
    variables: list[dict]


class TemplatePublishIn(BaseModel):
    legal_approver: str | None = None
    valid_from: str | None = None


class PreviewIn(BaseModel):
    data: dict


class ContractCreate(BaseModel):
    template_version_id: str
    data: dict
    title: str | None = None


# ---------- Misc ----------
class SettingIn(BaseModel):
    key: str
    value: Any
    description: str | None = None


class PageOut(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


def paginate(items: list, page: int, page_size: int):
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page, "page_size": page_size}
