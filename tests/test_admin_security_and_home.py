import asyncio
import base64
import os
import secrets
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import URL


_test_data = tempfile.TemporaryDirectory(prefix="career-platform-tests-")
_test_username = secrets.token_urlsafe(12)
_test_password = secrets.token_urlsafe(32)
os.environ["DATA_DIR"] = _test_data.name
os.environ["ADMIN_USERNAME"] = _test_username
os.environ["ADMIN_PASSWORD"] = _test_password

import main  # noqa: E402


def asgi_request(method="GET", path="/", body=b"", headers=None):
    request_headers = [(b"host", b"testserver")]
    if body:
        request_headers.append((b"content-type", b"application/x-www-form-urlencoded"))
    if headers:
        request_headers.extend(headers)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": request_headers,
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(main.app(scope, receive, send))
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    ).decode("utf-8", errors="replace")
    response_headers = dict(response_start["headers"])
    return response_start["status"], response_headers, response_body


def basic_auth(username=None, password=None):
    username = username or _test_username
    password = password or _test_password
    token = base64.b64encode(f"{username}:{password}".encode("utf-8"))
    return (b"authorization", b"Basic " + token)


class AdminSecurityAndHomepageTests(unittest.TestCase):
    def setUp(self):
        os.environ["ADMIN_USERNAME"] = _test_username
        os.environ["ADMIN_PASSWORD"] = _test_password
        self.test_data = tempfile.TemporaryDirectory(prefix="career-platform-case-")
        self.addCleanup(self.test_data.cleanup)
        self.database_path = Path(self.test_data.name) / "career-platform.db"
        database_url = URL.create("sqlite", database=str(self.database_path))
        self.environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "DATA_DIR": self.test_data.name,
                "DATABASE_URL": database_url.render_as_string(hide_password=False),
            },
            clear=False,
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

        import database
        import seed_data

        self.engine = database.create_engine_for_url(database_url)
        self.addCleanup(self.engine.dispose)
        config = Config(str(Path(main.__file__).resolve().parent / "alembic.ini"))
        config.set_main_option(
            "script_location", str(Path(main.__file__).resolve().parent / "migrations")
        )
        command.upgrade(config, "head")
        seed_data.seed_development_data(self.engine)
        engine_patch = patch.object(main, "get_engine", return_value=self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)

        with self.engine.begin() as db:
            db.execute(
                text("UPDATE experience SET achievements=:achievements WHERE id=(SELECT id FROM experience ORDER BY id LIMIT 1)"),
                {
                    "achievements":
                    "Processed an average of 250+ departmental orders weekly across nearly 200+ campus departments across 25 buildings with an error rate of approximately 0.02%.\n"
                    "Trained 6+ student hires on inventory software, order procedures, and delivery protocols."
                },
            )
            db.execute(
                text("UPDATE project SET outcome=:outcome WHERE id=(SELECT id FROM project ORDER BY id LIMIT 1)"),
                {"outcome": "Compared two candidate warehouse locations and found a $200 transportation cost difference."},
            )

    def test_public_homepage_remains_available_without_admin_credentials(self):
        os.environ.pop("ADMIN_USERNAME", None)
        os.environ.pop("ADMIN_PASSWORD", None)

        status, _, body = asgi_request()

        self.assertEqual(status, 200)
        self.assertIn("Adam Riddick", body)
        self.assertNotIn("Manage content", body)

    def test_homepage_renders_without_inventing_data_when_database_is_unavailable(self):
        main._last_good_profile = None
        failure = OperationalError("SELECT", {}, Exception("database unavailable"))
        with patch.object(main, "profile_data", side_effect=failure):
            status, _, body = asgi_request()

        self.assertEqual(status, 503)
        self.assertIn('<main id="main-content"', body)
        self.assertIn("Projects temporarily unavailable", body)
        self.assertNotIn("Warehouse Location Optimization Analysis", body)

    def test_database_failure_keeps_profile_and_recovers_without_restart(self):
        main._last_good_profile = None
        status, _, body = asgi_request()
        self.assertEqual(status, 200)
        self.assertIn("Warehouse Location Optimization Analysis", body)

        failure = OperationalError("SELECT", {}, Exception("database unavailable"))
        with patch.object(main, "profile_data", side_effect=failure):
            status, _, body = asgi_request()
        self.assertEqual(status, 503)
        self.assertIn("Adam Riddick", body)
        self.assertIn("Projects temporarily unavailable", body)
        self.assertNotIn("Warehouse Location Optimization Analysis", body)

        status, _, body = asgi_request()
        self.assertEqual(status, 200)
        self.assertIn("Warehouse Location Optimization Analysis", body)
        self.assertNotIn("Projects temporarily unavailable", body)

    def test_placeholder_values_are_labeled_not_shown_raw(self):
        main._last_good_profile = None
        with self.engine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO volunteer_experience (person_id, organization_name, role_title, start_date, end_date, description) "
                    "VALUES (1, 'Greenworks Food Service', 'Volunteer', '2024', 'PLACEHOLDER', 'PLACEHOLDER')"
                )
            )
        status, _, body = asgi_request()
        self.assertEqual(status, 200)
        self.assertIn("Greenworks Food Service", body)
        self.assertIn("end date to be added", body)
        self.assertIn("Details to be added.", body)
        self.assertNotIn("PLACEHOLDER", body)

    def test_empty_database_returns_200_without_sample_projects(self):
        main._last_good_profile = None
        with self.engine.begin() as db:
            for table in ("link", "volunteer_experience", "certification", "skill",
                          "project", "experience", "education", "person"):
                db.execute(text(f"DELETE FROM {table}"))
        status, _, body = asgi_request()
        self.assertEqual(status, 200)
        self.assertNotIn("Warehouse Location Optimization Analysis", body)
        self.assertNotIn("Projects temporarily unavailable", body)

    def test_production_stylesheet_url_is_relative_and_ignores_forwarded_headers(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "ADMIN_ALLOWED_ORIGINS": "https://profile.example",
            },
            clear=False,
        ):
            status, _, body = asgi_request(
                headers=[
                    (b"x-forwarded-proto", b"https"),
                    (b"x-forwarded-host", b"attacker.example"),
                    (b"forwarded", b"proto=https;host=attacker.example"),
                ]
            )

        self.assertEqual(status, 200)
        self.assertIn('href="/static/styles.css"', body)
        self.assertNotIn("attacker.example", body)
        self.assertNotIn('href="http://testserver/static/styles.css"', body)

    def test_admin_requires_valid_basic_credentials(self):
        status, headers, _ = asgi_request("GET", "/admin")

        self.assertEqual(status, 401)
        self.assertIn(b"basic", headers[b"www-authenticate"].lower())

    def test_admin_rejects_incorrect_password_without_echoing_it(self):
        status, _, body = asgi_request(
            "GET", "/admin", headers=[basic_auth(password=secrets.token_urlsafe(24))]
        )

        self.assertEqual(status, 401)
        self.assertNotIn(_test_password, body)

    def test_admin_rejects_incorrect_username(self):
        status, _, _ = asgi_request(
            "GET", "/admin", headers=[basic_auth(username=secrets.token_urlsafe(24))]
        )

        self.assertEqual(status, 401)

    def test_blank_server_credentials_fail_closed(self):
        os.environ["ADMIN_USERNAME"] = " "
        os.environ["ADMIN_PASSWORD"] = ""

        status, _, body = asgi_request("GET", "/admin")

        self.assertEqual(status, 503)
        self.assertNotIn(_test_password, body)

    def test_authenticated_admin_page_is_available(self):
        status, _, body = asgi_request("GET", "/admin", headers=[basic_auth()])

        self.assertEqual(status, 200)
        self.assertIn("Career profile editor", body)

    def test_every_admin_write_route_rejects_anonymous_requests(self):
        def snapshot():
            with main.connect() as db:
                return {
                    "name": db.execute(text("SELECT full_name FROM person ORDER BY id LIMIT 1")).scalar_one(),
                    "projects": db.execute(text("SELECT COUNT(*) FROM project")).scalar_one(),
                    "skills": db.execute(text("SELECT COUNT(*) FROM skill")).scalar_one(),
                }

        before = snapshot()
        requests = [
            ("POST", "/admin/profile", urlencode({"full_name": "Unauthorized"}).encode()),
            ("POST", "/admin/add/project", urlencode({"title": "Unauthorized"}).encode()),
            ("POST", "/admin/delete/skill/1", b""),
        ]

        for method, path, body in requests:
            with self.subTest(path=path):
                status, _, _ = asgi_request(method, path, body=body)
                self.assertEqual(status, 401)

        after = snapshot()
        self.assertEqual(after, before)

    def test_authenticated_admin_write_rejects_cross_origin_or_missing_origin(self):
        body = urlencode({"full_name": "Cross-site change"}).encode()

        for origin in (b"https://attacker.example", None):
            headers = [basic_auth()]
            if origin is not None:
                headers.append((b"origin", origin))
            with self.subTest(origin=origin):
                status, _, _ = asgi_request("POST", "/admin/profile", body=body, headers=headers)
                self.assertEqual(status, 403)
        with main.connect() as db:
            name = db.execute(text("SELECT full_name FROM person ORDER BY id LIMIT 1")).scalar_one()
        self.assertEqual(name, "Adam Riddick")

    def test_authenticated_same_origin_admin_write_still_works(self):
        headers = [basic_auth(), (b"origin", b"http://testserver")]
        body = urlencode({"full_name": "Adam Riddick Updated"}).encode()

        status, _, _ = asgi_request("POST", "/admin/profile", body=body, headers=headers)

        self.assertEqual(status, 303)
        with main.connect() as db:
            name = db.execute(text("SELECT full_name FROM person ORDER BY id LIMIT 1")).scalar_one()
        self.assertEqual(name, "Adam Riddick Updated")

    def test_production_admin_write_requires_configured_origin_allowlist(self):
        body = urlencode({"full_name": "Must remain unchanged"}).encode()
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            os.environ.pop("ADMIN_ALLOWED_ORIGINS", None)
            status, _, _ = asgi_request(
                "POST", "/admin/profile", body=body,
                headers=[basic_auth(), (b"origin", b"https://profile.example")],
            )

        self.assertEqual(status, 503)
        with main.connect() as db:
            name = db.execute(text("SELECT full_name FROM person ORDER BY id LIMIT 1")).scalar_one()
        self.assertEqual(name, "Adam Riddick")

    def test_production_origin_allowlist_ignores_spoofed_forwarding_headers(self):
        body = urlencode({"full_name": "Production update"}).encode()
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "ADMIN_ALLOWED_ORIGINS": "https://profile.example"},
            clear=False,
        ):
            status, _, _ = asgi_request(
                "POST", "/admin/profile", body=body,
                headers=[
                    basic_auth(),
                    (b"origin", b"https://attacker.example"),
                    (b"x-forwarded-proto", b"https"),
                    (b"x-forwarded-host", b"attacker.example"),
                    (b"forwarded", b"proto=https;host=attacker.example"),
                ],
            )

        self.assertEqual(status, 403)
        with main.connect() as db:
            name = db.execute(text("SELECT full_name FROM person ORDER BY id LIMIT 1")).scalar_one()
        self.assertEqual(name, "Adam Riddick")

    def test_production_allowlisted_https_origin_can_write(self):
        body = urlencode({"full_name": "Production update"}).encode()
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "ADMIN_ALLOWED_ORIGINS": "https://Profile.Example:443"},
            clear=False,
        ):
            status, _, _ = asgi_request(
                "POST", "/admin/profile", body=body,
                headers=[basic_auth(), (b"origin", b"https://profile.example")],
            )

        self.assertEqual(status, 303)
        with main.connect() as db:
            name = db.execute(text("SELECT full_name FROM person ORDER BY id LIMIT 1")).scalar_one()
        self.assertEqual(name, "Production update")


    def test_authenticated_add_and_delete_routes_still_work(self):
        add_body = urlencode({
            "title": "Route regression project",
            "category": "Academic",
            "course_name": "Database Management Systems",
        }).encode()
        headers = [basic_auth(), (b"origin", b"http://testserver")]

        status, _, _ = asgi_request(
            "POST", "/admin/add/project", body=add_body, headers=headers
        )

        self.assertEqual(status, 303)
        with main.connect() as db:
            created_id = db.execute(
                text("SELECT id FROM project WHERE title=:title"),
                {"title": "Route regression project"},
            ).scalar_one()

        status, _, _ = asgi_request(
            "POST", f"/admin/delete/project/{created_id}", headers=headers
        )

        self.assertEqual(status, 303)
        with main.connect() as db:
            self.assertEqual(
                db.execute(
                    text("SELECT COUNT(*) FROM project WHERE id=:id"), {"id": created_id}
                ).scalar_one(),
                0,
            )

    def test_homepage_uses_verified_profile_and_project_evidence(self):
        status, _, body = asgi_request()

        self.assertEqual(status, 200)
        self.assertIn("250+", body)
        self.assertIn("0.02%", body)
        self.assertIn("$200", body)

    def test_hero_value_proposition_uses_current_role_and_field_of_study(self):
        status, _, body = asgi_request()

        self.assertEqual(status, 200)
        self.assertIn(
            "Hands-on shipping and receiving assistant experience, informed by Information Systems and Business Analytics.",
            body,
        )

    def test_section_navigation_links_only_to_populated_sections(self):
        status, _, body = asgi_request()

        self.assertEqual(status, 200)
        self.assertIn('aria-label="Profile sections"', body)
        for section in ("experience", "education", "projects", "skills", "certifications"):
            with self.subTest(section=section):
                self.assertIn(f'href="#{section}"', body)
                self.assertIn(f'id="{section}"', body)
        self.assertNotIn('href="#about"', body)
        self.assertNotIn('href="#volunteer"', body)


class UvicornPortTests(unittest.TestCase):
    def test_run_server_uses_configured_port_and_local_default(self):
        import main

        with patch("uvicorn.run") as run, patch.dict(os.environ, {"PORT": "9123"}):
            main.run_server()
            run.assert_called_once_with(main.app, host="0.0.0.0", port=9123)

        with patch("uvicorn.run") as run, patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORT", None)
            main.run_server()
            run.assert_called_once_with(main.app, host="0.0.0.0", port=8000)


class FreshProcessImportTests(unittest.TestCase):
    def test_import_does_not_create_a_database_or_seed_rows(self):
        with tempfile.TemporaryDirectory(prefix="career-platform-import-") as data_directory:
            environment = os.environ.copy()
            environment["APP_ENV"] = "development"
            environment["DATA_DIR"] = data_directory
            environment.pop("DATABASE_URL", None)
            script = (
                "import main; from pathlib import Path; "
                f"assert not (Path({data_directory!r}) / 'career-platform.db').exists()"
            )
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=Path(main.__file__).resolve().parent,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
