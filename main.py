import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from fastapi.templating import Jinja2Templates

from database import database_url_from_env, get_engine
from forwarded_headers import ForwardedOriginMiddleware, normalize_origin

ROOT = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Validate configuration at startup without connecting, migrating, or seeding.
    database_url_from_env()
    get_engine()
    yield


app = FastAPI(title="Adam Riddick Career Platform", lifespan=lifespan)
# Railway's forwarded headers are not trusted until an independent ingress
# boundary is verified. Production writes use an explicit Origin allowlist.
app.add_middleware(ForwardedOriginMiddleware, trust_proxy=lambda scope: False)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))
admin_basic_auth = HTTPBasic(auto_error=False)


def require_admin(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(admin_basic_auth),
):
    expected_username = os.getenv("ADMIN_USERNAME", "")
    expected_password = os.getenv("ADMIN_PASSWORD", "")
    if not expected_username.strip() or not expected_password.strip():
        raise HTTPException(status_code=503, detail="Admin access is not configured.")

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": 'Basic realm="Career profile admin"'},
        )

    username_matches = secrets.compare_digest(
        credentials.username.encode("utf-8"), expected_username.encode("utf-8")
    )
    password_matches = secrets.compare_digest(
        credentials.password.encode("utf-8"), expected_password.encode("utf-8")
    )
    if not (username_matches and password_matches):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": 'Basic realm="Career profile admin"'},
        )

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin_headers = [
            value.decode("latin-1")
            for key, value in request.scope.get("headers", [])
            if key.lower() == b"origin"
        ]
        if os.getenv("APP_ENV", "development").casefold() == "production":
            configured = os.getenv("ADMIN_ALLOWED_ORIGINS", "")
            allowed = {
                normalized
                for item in configured.split(",")
                if (normalized := normalize_origin(item.strip())) is not None
            }
            if not allowed:
                raise HTTPException(status_code=503, detail="Admin writes are not configured.")
            supplied = normalize_origin(origin_headers[0]) if len(origin_headers) == 1 else None
            if supplied is None or supplied not in allowed:
                raise HTTPException(status_code=403, detail="Admin form origin was not accepted.")
        else:
            origin = origin_headers[0] if len(origin_headers) == 1 else ""
            parsed_origin = urlsplit(origin)
            if (
                not origin
                or parsed_origin.scheme != request.url.scheme
                or parsed_origin.netloc.casefold() != request.url.netloc.casefold()
                or parsed_origin.username is not None
                or parsed_origin.password is not None
            ):
                raise HTTPException(status_code=403, detail="Admin form origin was not accepted.")

    return credentials.username


admin_router = APIRouter(dependencies=[Depends(require_admin)])

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
    """Return a SQLAlchemy connection from the configured shared engine."""
    return get_engine().connect()


def _row_dict(row: RowMapping | None):
    return dict(row) if row is not None else None


def profile_data():
    with connect() as db:
        person_row = db.execute(
            text("SELECT * FROM person ORDER BY id LIMIT 1")
        ).mappings().first()
        result = {"person": _row_dict(person_row)}
        for key, (_, table, _) in ENTITIES.items():
            order = "start_date DESC" if key in ("education", "experience", "volunteer") else "id ASC"
            if person_row:
                rows = db.execute(
                    text(f"SELECT * FROM {table} WHERE person_id=:person_id ORDER BY {order}"),
                    {"person_id": person_row["id"]},
                ).mappings().all()
                result[PLURALS[key]] = [dict(row) for row in rows]
            else:
                result[PLURALS[key]] = []
        return result


# Last profile this worker read successfully. On a database failure the page
# keeps showing that real profile (never sample data) and marks projects as
# unavailable with HTTP 503. A later successful read replaces it, so recovery
# needs no restart.
_last_good_profile: dict | None = None


def _empty_context() -> dict:
    return {"person": None, **{plural: [] for plural in PLURALS.values()}}


@app.get("/")
def home(request: Request):
    global _last_good_profile
    try:
        context = profile_data()
        _last_good_profile = context
        context = {**context, "projects_unavailable": False}
        status_code = 200
    except SQLAlchemyError:
        cached = _last_good_profile or _empty_context()
        context = {**cached, "projects": [], "projects_unavailable": True}
        status_code = 503
    return templates.TemplateResponse(
        request=request, name="home.html", context=context, status_code=status_code
    )


@app.get("/privacy")
def privacy(request: Request):
    try:
        person = profile_data()["person"]
    except SQLAlchemyError:
        person = None
    return templates.TemplateResponse(
        request=request, name="privacy.html", context={"person": person}
    )


@admin_router.get("/admin")
def admin(request: Request):
    data = profile_data()
    data["labels"] = LABELS
    data["entities"] = ENTITIES
    return templates.TemplateResponse(request=request, name="admin.html", context=data)


@admin_router.post("/admin/profile")
def save_profile(full_name: str = Form(""), location_city: str = Form(""), location_state: str = Form(""), location_country: str = Form(""), email: str = Form(""), phone: str = Form(""), career_goal: str = Form(""), summary: str = Form(""), profile_photo_url: str = Form("")):
    with get_engine().begin() as db:
        db.execute(
            text("UPDATE person SET full_name=:full_name,location_city=:location_city,location_state=:location_state,location_country=:location_country,email=:email,phone=:phone,career_goal=:career_goal,summary=:summary,profile_photo_url=:profile_photo_url WHERE id=(SELECT id FROM person ORDER BY id LIMIT 1)"),
            {key: value.strip() for key, value in {
                "full_name": full_name, "location_city": location_city,
                "location_state": location_state, "location_country": location_country,
                "email": email, "phone": phone, "career_goal": career_goal,
                "summary": summary, "profile_photo_url": profile_photo_url,
            }.items()},
        )
    return RedirectResponse("/admin", status_code=303)


@admin_router.post("/admin/add/{entity}")
async def add_item(entity: str, request: Request):
    if entity not in ENTITIES:
        return RedirectResponse("/admin", status_code=303)
    _, table, fields = ENTITIES[entity]
    values = await request.form()
    row = [1 if f == "is_current" and values.get(f) else 0 if f == "is_current" else str(values.get(f, "")).strip() for f in fields]
    columns = ["person_id", *fields]
    parameters = {column: value for column, value in zip(columns, [1, *row])}
    placeholders = ",".join(f":{column}" for column in columns)
    with get_engine().begin() as db:
        db.execute(text(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"), parameters)
    return RedirectResponse("/admin", status_code=303)


@admin_router.post("/admin/delete/{entity}/{item_id}")
def delete_item(entity: str, item_id: int):
    if entity in ENTITIES:
        with get_engine().begin() as db:
            db.execute(
                text(f"DELETE FROM {ENTITIES[entity][1]} WHERE id=:item_id"),
                {"item_id": item_id},
            )
    return RedirectResponse("/admin", status_code=303)


app.include_router(admin_router)


def run_server() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    run_server()
