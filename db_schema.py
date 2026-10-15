"""SQLAlchemy Core metadata matching the application's existing SQLite schema."""

import sqlalchemy as sa


metadata = sa.MetaData()


person = sa.Table(
    "person",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("full_name", sa.Text),
    sa.Column("location_city", sa.Text),
    sa.Column("location_state", sa.Text),
    sa.Column("location_country", sa.Text),
    sa.Column("email", sa.Text),
    sa.Column("phone", sa.Text),
    sa.Column("career_goal", sa.Text),
    sa.Column("summary", sa.Text),
    sa.Column("profile_photo_url", sa.Text),
)

education = sa.Table(
    "education",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("person_id", sa.Integer),
    sa.Column("institution_name", sa.Text),
    sa.Column("city", sa.Text),
    sa.Column("state", sa.Text),
    sa.Column("country", sa.Text),
    sa.Column("start_date", sa.Text),
    sa.Column("end_date", sa.Text),
    sa.Column("degree_name", sa.Text),
    sa.Column("field_of_study", sa.Text),
    sa.Column("relevant_coursework", sa.Text),
)

experience = sa.Table(
    "experience",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("person_id", sa.Integer),
    sa.Column("company_name", sa.Text),
    sa.Column("city", sa.Text),
    sa.Column("state", sa.Text),
    sa.Column("country", sa.Text),
    sa.Column("role_title", sa.Text),
    sa.Column("start_date", sa.Text),
    sa.Column("end_date", sa.Text),
    sa.Column("is_current", sa.Boolean, server_default=sa.false()),
    sa.Column("description", sa.Text),
    sa.Column("achievements", sa.Text),
)

project = sa.Table(
    "project",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("person_id", sa.Integer),
    sa.Column("title", sa.Text),
    sa.Column("category", sa.Text),
    sa.Column("course_name", sa.Text),
    sa.Column("description", sa.Text),
    sa.Column("technologies_used", sa.Text),
    sa.Column("outcome", sa.Text),
    sa.Column("project_url", sa.Text),
)

skill = sa.Table(
    "skill",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("person_id", sa.Integer),
    sa.Column("name", sa.Text),
    sa.Column("category", sa.Text),
    sa.Column("proficiency_level", sa.Text),
    sa.Column("notes", sa.Text),
)

certification = sa.Table(
    "certification",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("person_id", sa.Integer),
    sa.Column("name", sa.Text),
    sa.Column("issuing_organization", sa.Text),
    sa.Column("completion_date", sa.Text),
    sa.Column("credential_url", sa.Text),
)

volunteer_experience = sa.Table(
    "volunteer_experience",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("person_id", sa.Integer),
    sa.Column("organization_name", sa.Text),
    sa.Column("role_title", sa.Text),
    sa.Column("start_date", sa.Text),
    sa.Column("end_date", sa.Text),
    sa.Column("location", sa.Text),
    sa.Column("description", sa.Text),
)

link = sa.Table(
    "link",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("person_id", sa.Integer),
    sa.Column("label", sa.Text),
    sa.Column("url", sa.Text),
    sa.Column("category", sa.Text),
)
