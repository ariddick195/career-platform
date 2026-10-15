"""Create the existing career profile schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "person",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.Text()),
        sa.Column("location_city", sa.Text()),
        sa.Column("location_state", sa.Text()),
        sa.Column("location_country", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("career_goal", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("profile_photo_url", sa.Text()),
    )
    op.create_table(
        "education",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer()),
        sa.Column("institution_name", sa.Text()),
        sa.Column("city", sa.Text()),
        sa.Column("state", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("start_date", sa.Text()),
        sa.Column("end_date", sa.Text()),
        sa.Column("degree_name", sa.Text()),
        sa.Column("field_of_study", sa.Text()),
        sa.Column("relevant_coursework", sa.Text()),
    )
    op.create_table(
        "experience",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer()),
        sa.Column("company_name", sa.Text()),
        sa.Column("city", sa.Text()),
        sa.Column("state", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("role_title", sa.Text()),
        sa.Column("start_date", sa.Text()),
        sa.Column("end_date", sa.Text()),
        sa.Column("is_current", sa.Boolean(), server_default=sa.false()),
        sa.Column("description", sa.Text()),
        sa.Column("achievements", sa.Text()),
    )
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer()),
        sa.Column("title", sa.Text()),
        sa.Column("category", sa.Text()),
        sa.Column("course_name", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("technologies_used", sa.Text()),
        sa.Column("outcome", sa.Text()),
        sa.Column("project_url", sa.Text()),
    )
    op.create_table(
        "skill",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer()),
        sa.Column("name", sa.Text()),
        sa.Column("category", sa.Text()),
        sa.Column("proficiency_level", sa.Text()),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "certification",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer()),
        sa.Column("name", sa.Text()),
        sa.Column("issuing_organization", sa.Text()),
        sa.Column("completion_date", sa.Text()),
        sa.Column("credential_url", sa.Text()),
    )
    op.create_table(
        "volunteer_experience",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer()),
        sa.Column("organization_name", sa.Text()),
        sa.Column("role_title", sa.Text()),
        sa.Column("start_date", sa.Text()),
        sa.Column("end_date", sa.Text()),
        sa.Column("location", sa.Text()),
        sa.Column("description", sa.Text()),
    )
    op.create_table(
        "link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer()),
        sa.Column("label", sa.Text()),
        sa.Column("url", sa.Text()),
        sa.Column("category", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("link")
    op.drop_table("volunteer_experience")
    op.drop_table("certification")
    op.drop_table("skill")
    op.drop_table("project")
    op.drop_table("experience")
    op.drop_table("education")
    op.drop_table("person")
