"""Explicit sample profile data for local development only."""

from __future__ import annotations

import os

from sqlalchemy import Engine, func, insert, select

import db_schema as schema


class SeedConfigurationError(ValueError):
    """Raised when sample data seeding is requested outside local SQLite."""


def seed_development_data(engine: Engine) -> None:
    if os.getenv("APP_ENV", "development").strip().lower() != "development":
        raise SeedConfigurationError("Development sample data is only available in development mode.")
    if engine.dialect.name != "sqlite":
        raise SeedConfigurationError("Development sample data requires a SQLite database.")

    with engine.begin() as connection:
        existing_people = connection.scalar(select(func.count()).select_from(schema.person))
        if existing_people:
            return

        connection.execute(insert(schema.person).values(
            id=1,
            full_name="Adam Riddick",
            location_city="Los Angeles",
            location_state="CA",
            location_country="USA",
            email="ariddick@lion.lmu.edu",
            phone="(424) 275-5352",
            career_goal="My career goal is to be a senior level logistics analyst or manager",
            summary="",
            profile_photo_url="",
        ))
        connection.execute(insert(schema.education).values(
            person_id=1,
            institution_name="Loyola Marymount University",
            city="Los Angeles",
            state="CA",
            start_date="2023-08",
            end_date="2027-05",
            degree_name="B.A.",
            field_of_study="Information Systems and Business Analytics",
            relevant_coursework="Analytics in Operations and Supply Chain Management; Programming for Business Applications; Database Management Systems",
        ))
        connection.execute(insert(schema.experience).values(
            person_id=1,
            company_name="LMU Distribution Center",
            city="Los Angeles",
            state="CA",
            country="USA",
            role_title="Shipping and Receiving Assistant",
            start_date="2024-07",
            end_date="Present",
            is_current=True,
            description="Shipping and Receiving Assistant",
            achievements="Processed 250+ departmental orders weekly across nearly 200 campus departments.\nTrained 6+ student hires on inventory software and delivery protocols.",
        ))
        connection.execute(insert(schema.project).values(
            person_id=1,
            title="Warehouse Location Optimization Analysis",
            category="Academic / Analytics",
            course_name="Analytics in Operations and Supply Chain Management",
            description="Built an Excel Solver transportation model comparing two warehouse locations across three factories and four destinations.",
            technologies_used="Excel Solver",
            outcome="Compared options and identified a lower-cost network configuration.",
            project_url="",
        ))
        connection.execute(insert(schema.skill), [
            {"person_id": 1, "name": "Excel & Access", "category": "Tools", "proficiency_level": "Strong", "notes": "PivotTables, Solver, data cleaning, and database queries"},
            {"person_id": 1, "name": "Supply Chain Analytics", "category": "Domain", "proficiency_level": "Strong", "notes": "Cost, capacity, and volume optimization"},
            {"person_id": 1, "name": "Python", "category": "Programming", "proficiency_level": "Intermediate", "notes": "Data analysis and visualization"},
            {"person_id": 1, "name": "MySQL", "category": "Database", "proficiency_level": "Intermediate", "notes": "Queries, joins, and reporting"},
        ])
        connection.execute(insert(schema.certification), [
            {"person_id": 1, "name": "IBM Databases and SQL for Data Science with Python"},
            {"person_id": 1, "name": "IBM Data Visualization and Dashboards with Excel and Cognos"},
            {"person_id": 1, "name": "Microsoft Office Specialist: Excel Associate"},
        ])
        connection.execute(insert(schema.link).values(
            person_id=1,
            label="LinkedIn",
            url="https://www.linkedin.com/in/adam-riddick-92750528a",
            category="Professional",
        ))
