from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentFindingOut(_StrictModel):
    """One thing worth an administrator's attention, why, and what to do about it."""

    rule_id: str
    priority: str  # CRITICAL | HIGH | MEDIUM | LOW
    title: str
    summary: str
    evidence: list[str]
    recommended_action: str
    file_id: UUID | None = None


class AgentRuleOut(_StrictModel):
    rule_id: str
    name: str
    watches: str
    threshold: str
    findings: int = Field(ge=0)


class AgentCountsOut(_StrictModel):
    critical: int = Field(ge=0)
    high: int = Field(ge=0)
    medium: int = Field(ge=0)
    low: int = Field(ge=0)


class AgentInputSummaryOut(_StrictModel):
    """What the agent read, as counts, so a quiet report can be told from a blind one."""

    audit_events_read: int = Field(ge=0)
    files_checkable: int = Field(ge=0)
    files_never_checked: int = Field(ge=0)
    audit_chain_entries_verified: int = Field(ge=0)
    last_scan_at: datetime | None = None


class AgentReportOut(_StrictModel):
    generated_at: datetime
    window_hours: int = Field(ge=1)
    counts: AgentCountsOut
    findings: list[AgentFindingOut]
    rules: list[AgentRuleOut]
    inputs: AgentInputSummaryOut
    boundaries: list[str]
