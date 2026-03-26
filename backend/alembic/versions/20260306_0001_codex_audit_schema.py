"""Add Codex audit and evaluation tables.

Revision ID: 20260306_0001
Revises:
Create Date: 2026-03-06 17:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260306_0001"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    if not _has_table("diagnosis_candidates"):
        op.create_table(
            "diagnosis_candidates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("chart_id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("assertion_id", sa.Integer(), nullable=True),
            sa.Column("candidate_key", sa.String(length=150), nullable=False),
            sa.Column("icd10_code", sa.String(length=20), nullable=True),
            sa.Column("hcc_code", sa.String(length=20), nullable=True),
            sa.Column("source_type", sa.String(length=50), nullable=False),
            sa.Column("lifecycle_state", sa.String(length=40), nullable=False),
            sa.Column("reason_code", sa.String(length=80), nullable=True),
            sa.Column("reason_text", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("provider_name", sa.String(length=255), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("exact_quote", sa.Text(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("review_status", sa.String(length=20), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["assertion_id"], ["assertions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["chart_id"], ["charts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("chart_id", "candidate_key", name="uq_diag_candidate_key"),
        )
        op.create_index("ix_diag_candidates_chart", "diagnosis_candidates", ["chart_id"])
        op.create_index("ix_diag_candidates_patient", "diagnosis_candidates", ["patient_id"])
        op.create_index("ix_diag_candidates_state", "diagnosis_candidates", ["lifecycle_state"])
        op.create_index("ix_diag_candidates_icd", "diagnosis_candidates", ["icd10_code"])
        op.create_index("ix_diag_candidates_hcc", "diagnosis_candidates", ["hcc_code"])
        op.create_index("ix_diag_candidates_review", "diagnosis_candidates", ["review_status"])
        op.create_index("ix_diag_candidates_effective_date", "diagnosis_candidates", ["effective_date"])

    if not _has_table("diagnosis_candidate_evidence"):
        op.create_table(
            "diagnosis_candidate_evidence",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("candidate_id", sa.Integer(), nullable=False),
            sa.Column("chart_id", sa.Integer(), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("char_start", sa.Integer(), nullable=True),
            sa.Column("char_end", sa.Integer(), nullable=True),
            sa.Column("exact_quote", sa.Text(), nullable=True),
            sa.Column("section_name", sa.String(length=100), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["candidate_id"], ["diagnosis_candidates.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["chart_id"], ["charts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_diag_candidate_ev_candidate", "diagnosis_candidate_evidence", ["candidate_id"])
        op.create_index("ix_diag_candidate_ev_chart", "diagnosis_candidate_evidence", ["chart_id"])
        op.create_index("ix_diag_candidate_ev_page", "diagnosis_candidate_evidence", ["page_number"])

    if not _has_table("decision_trace_events"):
        op.create_table(
            "decision_trace_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("chart_id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("entity_key", sa.String(length=150), nullable=False),
            sa.Column("lifecycle_state", sa.String(length=40), nullable=False),
            sa.Column("reason_code", sa.String(length=80), nullable=True),
            sa.Column("reason_text", sa.Text(), nullable=True),
            sa.Column("measure_id", sa.String(length=50), nullable=True),
            sa.Column("icd10_code", sa.String(length=20), nullable=True),
            sa.Column("hcc_code", sa.String(length=20), nullable=True),
            sa.Column("event_date", sa.Date(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["chart_id"], ["charts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_trace_events_chart", "decision_trace_events", ["chart_id"])
        op.create_index("ix_trace_events_patient", "decision_trace_events", ["patient_id"])
        op.create_index("ix_trace_events_entity", "decision_trace_events", ["entity_type", "entity_key"])
        op.create_index("ix_trace_events_measure", "decision_trace_events", ["measure_id"])
        op.create_index("ix_trace_events_icd", "decision_trace_events", ["icd10_code"])
        op.create_index("ix_trace_events_hcc", "decision_trace_events", ["hcc_code"])
        op.create_index("ix_trace_events_date", "decision_trace_events", ["event_date"])

    if not _has_table("evaluation_runs"):
        op.create_table(
            "evaluation_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_label", sa.String(length=120), nullable=False),
            sa.Column("dataset_name", sa.String(length=120), nullable=False),
            sa.Column("scope", sa.String(length=40), nullable=False),
            sa.Column("git_ref", sa.String(length=80), nullable=True),
            sa.Column("metrics", sa.JSON(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("run_label", "dataset_name", name="uq_eval_run_label_dataset"),
        )
        op.create_index("ix_eval_runs_dataset", "evaluation_runs", ["dataset_name"])
        op.create_index("ix_eval_runs_scope", "evaluation_runs", ["scope"])

    if not _has_table("benchmark_datasets"):
        op.create_table(
            "benchmark_datasets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("dataset_name", sa.String(length=120), nullable=False),
            sa.Column("dataset_type", sa.String(length=40), nullable=False),
            sa.Column("version", sa.String(length=40), nullable=True),
            sa.Column("source_path", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dataset_name"),
        )

    if not _has_table("golden_labels"):
        op.create_table(
            "golden_labels",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("dataset_id", sa.Integer(), nullable=False),
            sa.Column("chart_id", sa.Integer(), nullable=True),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("entity_key", sa.String(length=150), nullable=False),
            sa.Column("label_value", sa.String(length=120), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["chart_id"], ["charts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["dataset_id"], ["benchmark_datasets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_golden_labels_dataset", "golden_labels", ["dataset_id"])
        op.create_index("ix_golden_labels_chart", "golden_labels", ["chart_id"])
        op.create_index("ix_golden_labels_patient", "golden_labels", ["patient_id"])
        op.create_index("ix_golden_labels_entity", "golden_labels", ["entity_type", "entity_key"])

    if not _has_table("reviewer_disagreements"):
        op.create_table(
            "reviewer_disagreements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("chart_id", sa.Integer(), nullable=True),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("entity_key", sa.String(length=150), nullable=False),
            sa.Column("reviewer_a", sa.String(length=80), nullable=False),
            sa.Column("reviewer_b", sa.String(length=80), nullable=False),
            sa.Column("label_a", sa.String(length=120), nullable=False),
            sa.Column("label_b", sa.String(length=120), nullable=False),
            sa.Column("resolution", sa.String(length=120), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["chart_id"], ["charts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_reviewer_disagree_chart", "reviewer_disagreements", ["chart_id"])
        op.create_index("ix_reviewer_disagree_patient", "reviewer_disagreements", ["patient_id"])
        op.create_index("ix_reviewer_disagree_entity", "reviewer_disagreements", ["entity_type", "entity_key"])


def downgrade() -> None:
    for index_name, table_name in [
        ("ix_reviewer_disagree_entity", "reviewer_disagreements"),
        ("ix_reviewer_disagree_patient", "reviewer_disagreements"),
        ("ix_reviewer_disagree_chart", "reviewer_disagreements"),
        ("ix_golden_labels_entity", "golden_labels"),
        ("ix_golden_labels_patient", "golden_labels"),
        ("ix_golden_labels_chart", "golden_labels"),
        ("ix_golden_labels_dataset", "golden_labels"),
        ("ix_eval_runs_scope", "evaluation_runs"),
        ("ix_eval_runs_dataset", "evaluation_runs"),
        ("ix_trace_events_date", "decision_trace_events"),
        ("ix_trace_events_hcc", "decision_trace_events"),
        ("ix_trace_events_icd", "decision_trace_events"),
        ("ix_trace_events_measure", "decision_trace_events"),
        ("ix_trace_events_entity", "decision_trace_events"),
        ("ix_trace_events_patient", "decision_trace_events"),
        ("ix_trace_events_chart", "decision_trace_events"),
        ("ix_diag_candidate_ev_page", "diagnosis_candidate_evidence"),
        ("ix_diag_candidate_ev_chart", "diagnosis_candidate_evidence"),
        ("ix_diag_candidate_ev_candidate", "diagnosis_candidate_evidence"),
        ("ix_diag_candidates_effective_date", "diagnosis_candidates"),
        ("ix_diag_candidates_review", "diagnosis_candidates"),
        ("ix_diag_candidates_hcc", "diagnosis_candidates"),
        ("ix_diag_candidates_icd", "diagnosis_candidates"),
        ("ix_diag_candidates_state", "diagnosis_candidates"),
        ("ix_diag_candidates_patient", "diagnosis_candidates"),
        ("ix_diag_candidates_chart", "diagnosis_candidates"),
    ]:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        if inspector.has_table(table_name):
            try:
                op.drop_index(index_name, table_name=table_name)
            except Exception:
                pass

    for table_name in [
        "reviewer_disagreements",
        "golden_labels",
        "benchmark_datasets",
        "evaluation_runs",
        "decision_trace_events",
        "diagnosis_candidate_evidence",
        "diagnosis_candidates",
    ]:
        if _has_table(table_name):
            op.drop_table(table_name)
