import os
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "career-platform.db"

app = FastAPI(title="Adam Riddick Career Platform")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS person (id INTEGER PRIMARY KEY, full_name TEXT, location_city TEXT, location_state TEXT, location_country TEXT, email TEXT, phone TEXT, career_goal TEXT, summary TEXT, profile_photo_url TEXT);
CREATE TABLE IF NOT EXISTS education (id INTEGER PRIMARY KEY, person_id INTEGER, institution_name TEXT, city TEXT, state TEXT, country TEXT, start_date TEXT, end_date TEXT, degree_name TEXT, field_of_study TEXT, relevant_coursework TEXT);
CREATE TABLE IF NOT EXISTS experience (id INTEGER PRIMARY KEY, person_id INTEGER, company_name TEXT, city TEXT, state TEXT, country TEXT, role_title TEXT, start_date TEXT, end_date TEXT, is_current INTEGER DEFAULT 0, description TEXT, achievements TEXT);
CREATE TABLE IF NOT EXISTS project (id INTEGER PRIMARY KEY, person_id INTEGER, title TEXT, category TEXT, course_name TEXT, description TEXT, technologies_used TEXT, outcome TEXT, project_url TEXT);
CREATE TABLE IF NOT EXISTS skill (id INTEGER PRIMARY KEY, person_id INTEGER, name TEXT, category TEXT, proficiency_level TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS certification (id INTEGER PRIMARY KEY, person_id INTEGER, name TEXT, issuing_organization TEXT, completion_date TEXT, credential_url TEXT);
CREATE TABLE IF NOT EXISTS volunteer_experience (id INTEGER PRIMARY KEY, person_id INTEGER, organization_name TEXT, role_title TEXT, start_date TEXT, end_date TEXT, location TEXT, description TEXT);
CREATE TABLE IF NOT EXISTS link (id INTEGER PRIMARY KEY, person_id INTEGER, label TEXT, url TEXT, category TEXT);
"""

ENTITIES = {
    "education": ("Education", "education", ["institution_name", "city", "state", "country", "start_date", "end_date", "degree_name", "field_of_study", "relevant_coursework"]),
    "experience": ("Experience", "experience", ["company_name", "city", "state", "country", "role_title", "start_date", "end_date", "is_current", "description", "achievements"]),
    "project": ("Projects", "project", ["title", "category", "course_name", "description", "technologies_used", "outcome", "project_url"]),
    "skill": ("Skills", "skill", ["name", "category", "proficiency_level", "notes"]),
    "certification": ("Certifications", "certification", ["name", "issuing_organization", "completion_date", "credential_url"]),
    "volunteer": ("Volunteer experience", "volunteer_experience", ["organization_name", "role_title", "start_date", "end_date", "location", "description"]),
    "link": ("Links", "link", ["label", "category", "url"]),
}
PLURALS = {"education":"educations", "experience":"experiences", "project":"projects", "skill":"skills", "certification":"certifications", "volunteer":"volunteers", "link":"links"}
LABELS = {"full_name":"Full name", "location_city":"City", "location_state":"State", "location_country":"Country", "email":"Email", "phone":"Phone", "career_goal":"Career goal", "summary":"Summary", "profile_photo_url":"Profile photo URL", "institution_name":"Institution", "city":"City", "state":"State", "country":"Country", "start_date":"Start date", "end_date":"End date", "degree_name":"Degree", "field_of_study":"Field of study", "relevant_coursework":"Relevant coursework", "company_name":"Company", "role_title":"Role title", "is_current":"Current role", "description":"Description", "achievements":"Achievements", "title":"Title", "category":"Category", "course_name":"Course name", "technologies_used":"Technologies used", "outcome":"Outcome", "project_url":"Project URL", "name":"Name", "proficiency_level":"Proficiency level", "notes":"Notes", "issuing_organization":"Issuing organization", "completion_date":"Completion date", "credential_url":"Credential URL", "organization_name":"Organization", "location":"Location", "label":"Label", "url":"URL"}

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

def initialize():
    with closing(connect()) as db:
        db.executescript(SCHEMA)
        if db.execute("SELECT COUNT(*) FROM person").fetchone()[0] == 0:
            db.execute("INSERT INTO person VALUES (1,?,?,?,?,?,?,?,?,?)", ("Adam Riddick", "Los Angeles", "CA", "USA", "ariddick@lion.lmu.edu", "(424) 275-5352", "My career goal is to be a senior level logistics analyst or manager", "", ""))
            db.execute("INSERT INTO education (person_id,institution_name,city,state,start_date,end_date,degree_name,field_of_study,relevant_coursework) VALUES (1,?,?,?,?,?,?,?,?)", ("Loyola Marymount University", "Los Angeles", "CA", "2023-08", "2027-05", "B.A.", "Information Systems and Business Analytics", "Analytics in Operations and Supply Chain Management; Programming for Business Applications; Database Management Systems"))
            db.execute("INSERT INTO experience (person_id,company_name,city,state,country,role_title,start_date,end_date,is_current,description,achievements) VALUES (1,?,?,?,?,?,?,?,?,?,?)", ("LMU Distribution Center", "Los Angeles", "CA", "USA", "Shipping and Receiving Assistant", "2024-07", "Present", 1, "Shipping and Receiving Assistant", "Processed 250+ departmental orders weekly across nearly 200 campus departments.\nTrained 6+ student hires on inventory software and delivery protocols."))
            db.execute("INSERT INTO project (person_id,title,category,course_name,description,technologies_used,outcome,project_url) VALUES (1,?,?,?,?,?,?,?)", ("Warehouse Location Optimization Analysis", "Academic / Analytics", "Analytics in Operations and Supply Chain Management", "Built an Excel Solver transportation model comparing two warehouse locations across three factories and four destinations.", "Excel Solver", "Compared options and identified a lower-cost network configuration.", ""))
            for n,c,p,notes in [("Excel & Access","Tools","Strong","PivotTables, Solver, data cleaning, and database queries"),("Supply Chain Analytics","Domain","Strong","Cost, capacity, and volume optimization"),("Python","Programming","Intermediate","Data analysis and visualization"),("MySQL","Database","Intermediate","Queries, joins, and reporting")]: db.execute("INSERT INTO skill (person_id,name,category,proficiency_level,notes) VALUES (1,?,?,?,?)", (n,c,p,notes))
            for n in ["IBM Databases and SQL for Data Science with Python", "IBM Data Visualization and Dashboards with Excel and Cognos", "Microsoft Office Specialist: Excel Associate"]: db.execute("INSERT INTO certification (person_id,name) VALUES (1,?)", (n,))
            db.execute("INSERT INTO link (person_id,label,url,category) VALUES (1,?,?,?)", ("LinkedIn", "https://www.linkedin.com/in/adam-riddick-92750528a", "Professional"))
        db.commit()

initialize()

def profile_data():
    with closing(connect()) as db:
        person = db.execute("SELECT * FROM person ORDER BY id LIMIT 1").fetchone()
        result = {"person": dict(person) if person else None}
        for key, (_, table, _) in ENTITIES.items():
            order = "start_date DESC" if key in ("education", "experience", "volunteer") else "id ASC"
            result[PLURALS[key]] = [dict(row) for row in db.execute(f"SELECT * FROM {table} WHERE person_id=? ORDER BY {order}", (person["id"],))] if person else []
        return result

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context=profile_data())

@app.get("/admin")
def admin(request: Request):
    data = profile_data()
    data["labels"] = LABELS
    data["entities"] = ENTITIES
    return templates.TemplateResponse(request=request, name="admin.html", context=data)

@app.post("/admin/profile")
def save_profile(full_name: str = Form(""), location_city: str = Form(""), location_state: str = Form(""), location_country: str = Form(""), email: str = Form(""), phone: str = Form(""), career_goal: str = Form(""), summary: str = Form(""), profile_photo_url: str = Form("")):
    with closing(connect()) as db:
        db.execute("UPDATE person SET full_name=?,location_city=?,location_state=?,location_country=?,email=?,phone=?,career_goal=?,summary=?,profile_photo_url=? WHERE id=(SELECT id FROM person ORDER BY id LIMIT 1)", tuple(v.strip() for v in [full_name,location_city,location_state,location_country,email,phone,career_goal,summary,profile_photo_url]))
        db.commit()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/add/{entity}")
async def add_item(entity: str, request: Request):
    if entity not in ENTITIES: return RedirectResponse("/admin", status_code=303)
    _, table, fields = ENTITIES[entity]
    values = await request.form()
    row = [1 if f == "is_current" and values.get(f) else 0 if f == "is_current" else str(values.get(f, "")).strip() for f in fields]
    columns = ["person_id", *fields]
    with closing(connect()) as db:
        db.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [1, *row])
        db.commit()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/delete/{entity}/{item_id}")
def delete_item(entity: str, item_id: int):
    if entity in ENTITIES:
        with closing(connect()) as db:
            db.execute(f"DELETE FROM {ENTITIES[entity][1]} WHERE id=?", (item_id,))
            db.commit()
    return RedirectResponse("/admin", status_code=303)
