"""Initial schema — all 11 tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS extension first — required by the geom column in parcels.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. users — no FK dependencies
    op.create_table(
        "users",
        sa.Column("username", sa.String, primary_key=True, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("jurisdiction", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    # 2. parcels — no FK dependencies (base layer; all other tables FK into this)
    op.create_table(
        "parcels",
        sa.Column("ulpin", sa.String, primary_key=True, nullable=False),
        sa.Column("state_code", sa.String, nullable=False),
        sa.Column("district", sa.String, nullable=False),
        sa.Column("tehsil", sa.String, nullable=True),
        sa.Column("village_or_city", sa.String, nullable=False),
        # geometry(POLYGON,4326) is enforced by the SQLAlchemy/GeoAlchemy2 model;
        # the migration stores the column as a plain Text so this file remains
        # portable across environments that may not have PostGIS installed yet.
        sa.Column("geom", sa.Text, nullable=True),
        sa.Column("area_sqm", sa.Float, nullable=False),
        sa.Column("survey_or_khasra_no", sa.String, nullable=False),
        sa.Column("source_system", sa.String, nullable=False),
        sa.Column("last_synced_at", sa.DateTime, nullable=True),
    )

    # 3. ror — ulpin PK + FK → parcels (one record per parcel)
    op.create_table(
        "ror",
        sa.Column(
            "ulpin",
            sa.String,
            sa.ForeignKey("parcels.ulpin"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("owner_name", sa.String, nullable=False),
        sa.Column("tenure_type", sa.String, nullable=False),
        sa.Column("khatauni_no", sa.String, nullable=False),
        sa.Column("land_use_type", sa.String, nullable=False),
        sa.Column("mutation_status", sa.String, nullable=False),
        sa.Column("last_updated", sa.Date, nullable=False),
    )

    # 4. registrations — many per parcel
    op.create_table(
        "registrations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "ulpin", sa.String, sa.ForeignKey("parcels.ulpin"), nullable=False
        ),
        sa.Column("deed_no", sa.String, nullable=False),
        sa.Column("deed_type", sa.String, nullable=False),
        sa.Column("registration_date", sa.Date, nullable=False),
        sa.Column("sro_office", sa.String, nullable=False),
        sa.Column("buyer", sa.String, nullable=False),
        sa.Column("seller", sa.String, nullable=False),
        sa.Column("transaction_value", sa.Integer, nullable=False),
        sa.Column(
            "stamp_duty_paid",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 5. encumbrances — many per parcel
    op.create_table(
        "encumbrances",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "ulpin", sa.String, sa.ForeignKey("parcels.ulpin"), nullable=False
        ),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("institution", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
    )

    # 6. zoning — ulpin PK + FK → parcels (one record per parcel)
    op.create_table(
        "zoning",
        sa.Column(
            "ulpin",
            sa.String,
            sa.ForeignKey("parcels.ulpin"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("master_plan_zone", sa.String, nullable=False),
        sa.Column("permissible_use", sa.String, nullable=False),
        sa.Column("far_permitted", sa.Float, nullable=False),
        sa.Column(
            "far_existing",
            sa.Float,
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "violation_flag",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 7. building_permissions — many per parcel
    op.create_table(
        "building_permissions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "ulpin", sa.String, sa.ForeignKey("parcels.ulpin"), nullable=False
        ),
        sa.Column("approval_no", sa.String, nullable=False),
        sa.Column("approved_built_up_area", sa.Float, nullable=False),
        sa.Column("approval_date", sa.Date, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("architect_ref", sa.String, nullable=True),
    )

    # 8. tax — ulpin PK + FK → parcels (one record per parcel)
    op.create_table(
        "tax",
        sa.Column(
            "ulpin",
            sa.String,
            sa.ForeignKey("parcels.ulpin"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("assessment_id", sa.String, nullable=False),
        sa.Column("annual_tax", sa.Integer, nullable=False),
        sa.Column("last_paid_date", sa.Date, nullable=True),
        sa.Column("payment_status", sa.String, nullable=False),
        sa.Column("arrears", sa.Integer, nullable=False, server_default=sa.text("0")),
    )

    # 9. audit_logs — no FK (resource_id is a logical reference, not a DB FK)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("actor_user", sa.String, nullable=False),
        sa.Column("actor_role", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=False),
        sa.Column("resource_id", sa.String, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
    )

    # 10. workflow_tasks — ulpin FK → parcels
    op.create_table(
        "workflow_tasks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "ulpin", sa.String, sa.ForeignKey("parcels.ulpin"), nullable=False
        ),
        sa.Column("task_type", sa.String, nullable=False),
        sa.Column("assigned_role", sa.String, nullable=False),
        sa.Column(
            "status",
            sa.String,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("comment", sa.String, nullable=True),
    )

    # 11. citizen_service_requests — ulpin FK → parcels, citizen_username FK → users
    op.create_table(
        "citizen_service_requests",
        sa.Column("id", sa.String, primary_key=True, nullable=False),
        sa.Column(
            "ulpin", sa.String, sa.ForeignKey("parcels.ulpin"), nullable=False
        ),
        sa.Column(
            "citizen_username",
            sa.String,
            sa.ForeignKey("users.username"),
            nullable=False,
        ),
        sa.Column("service_type", sa.String, nullable=False),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column(
            "status",
            sa.String,
            nullable=False,
            server_default=sa.text("'submitted'"),
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # 12. state_adapter_configs — no FK dependencies; indexed on state_code
    op.create_table(
        "state_adapter_configs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("state_code", sa.String, nullable=False),
        sa.Column("source_field_name", sa.String, nullable=False),
        sa.Column("canonical_field_name", sa.String, nullable=False),
        sa.Column(
            "unit_conversion_factor",
            sa.Float,
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "language_code",
            sa.String,
            nullable=False,
            server_default=sa.text("'en'"),
        ),
    )
    op.create_index(
        "ix_state_adapter_configs_state_code",
        "state_adapter_configs",
        ["state_code"],
    )


def downgrade() -> None:
    # Drop in reverse creation order to satisfy FK constraints.
    op.drop_index("ix_state_adapter_configs_state_code", table_name="state_adapter_configs")
    op.drop_table("state_adapter_configs")
    op.drop_table("citizen_service_requests")
    op.drop_table("workflow_tasks")
    op.drop_table("audit_logs")
    op.drop_table("tax")
    op.drop_table("building_permissions")
    op.drop_table("zoning")
    op.drop_table("encumbrances")
    op.drop_table("registrations")
    op.drop_table("ror")
    op.drop_table("parcels")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS postgis;")
