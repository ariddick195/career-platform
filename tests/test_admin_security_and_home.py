import asyncio
import base64
import os
import secrets
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from urllib.parse import urlencode


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
        main.DB_PATH = Path(self.test_data.name) / "career-platform.db"
        main.initialize()
        with closing(main.connect()) as db:
            db.execute(
                "UPDATE experience SET achievements=? WHERE id=(SELECT id FROM experience ORDER BY id LIMIT 1)",
                (
                    "Processed an average of 250+ departmental orders weekly across nearly 200+ campus departments across 25 buildings with an error rate of approximately 0.02%.\n"
                    "Trained 6+ student hires on inventory software, order procedures, and delivery protocols.",
                ),
            )
            db.execute(
                "UPDATE project SET outcome=? WHERE id=(SELECT id FROM project ORDER BY id LIMIT 1)",
                ("Compared two candidate warehouse locations and found a $200 transportation cost difference.",),
            )
            db.commit()

    def tearDown(self):
        self.test_data.cleanup()

    def test_public_homepage_remains_available_without_admin_credentials(self):
        os.environ.pop("ADMIN_USERNAME", None)
        os.environ.pop("ADMIN_PASSWORD", None)

        status, _, body = asgi_request()

        self.assertEqual(status, 200)
        self.assertIn("Adam Riddick", body)
        self.assertNotIn("Manage content", body)

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
            with closing(main.connect()) as db:
                return {
                    "name": db.execute("SELECT full_name FROM person ORDER BY id LIMIT 1").fetchone()[0],
                    "projects": db.execute("SELECT COUNT(*) FROM project").fetchone()[0],
                    "skills": db.execute("SELECT COUNT(*) FROM skill").fetchone()[0],
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
        with closing(main.connect()) as db:
            name = db.execute("SELECT full_name FROM person ORDER BY id LIMIT 1").fetchone()[0]
        self.assertEqual(name, "Adam Riddick")

    def test_authenticated_same_origin_admin_write_still_works(self):
        headers = [basic_auth(), (b"origin", b"http://testserver")]
        body = urlencode({"full_name": "Adam Riddick Updated"}).encode()

        status, _, _ = asgi_request("POST", "/admin/profile", body=body, headers=headers)

        self.assertEqual(status, 303)
        with closing(main.connect()) as db:
            name = db.execute("SELECT full_name FROM person ORDER BY id LIMIT 1").fetchone()[0]
        self.assertEqual(name, "Adam Riddick Updated")

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


if __name__ == "__main__":
    unittest.main()
