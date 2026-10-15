import asyncio
import unittest

from forwarded_headers import ForwardedOriginMiddleware, normalize_origin, public_origin


def make_scope(headers=None, scheme="http"):
    scope_headers = [(b"host", b"service.internal")]
    scope_headers.extend(headers or [])
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": scheme,
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": scope_headers,
        "server": ("service.internal", 80),
        "client": ("127.0.0.1", 12345),
    }


class ForwardedOriginTests(unittest.TestCase):
    def test_untrusted_forwarding_headers_do_not_change_public_origin(self):
        scope = make_scope(
            [
                (b"x-forwarded-proto", b"https"),
                (b"x-forwarded-host", b"profile.example"),
            ]
        )

        self.assertEqual(public_origin(scope, trusted_proxy=False), ("http", "service.internal"))

    def test_trusted_proxy_uses_complete_forwarded_origin(self):
        scope = make_scope(
            [
                (b"x-forwarded-proto", b"HTTPS"),
                (b"x-forwarded-host", b"Profile.Example:443"),
            ]
        )

        self.assertEqual(public_origin(scope, trusted_proxy=True), ("https", "profile.example"))

    def test_incomplete_or_ambiguous_forwarding_falls_back_to_direct_origin(self):
        for forwarded in (
            [(b"x-forwarded-proto", b"https")],
            [
                (b"x-forwarded-proto", b"https"),
                (b"x-forwarded-host", b"profile.example/path"),
            ],
            [
                (b"x-forwarded-proto", b"https"),
                (b"x-forwarded-host", b"profile.example,attacker.example"),
            ],
        ):
            with self.subTest(forwarded=forwarded):
                scope = make_scope(forwarded)
                self.assertEqual(
                    public_origin(scope, trusted_proxy=True), ("http", "service.internal")
                )

    def test_origin_normalization_rejects_non_origin_urls(self):
        for value in (
            "https://profile.example/path",
            "https://user@profile.example",
            "https://profile.example?next=attacker",
            "https://profile.example:",
        ):
            with self.subTest(value=value):
                self.assertIsNone(normalize_origin(value))

    def test_middleware_only_rewrites_scope_when_trust_callback_accepts_it(self):
        async def exercise(trusted):
            seen = []

            async def app(scope, receive, send):
                seen.append(scope)

            middleware = ForwardedOriginMiddleware(app, trust_proxy=lambda scope: trusted)
            scope = make_scope(
                [
                    (b"x-forwarded-proto", b"https"),
                    (b"x-forwarded-host", b"profile.example"),
                ]
            )

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                return None

            await middleware(scope, receive, send)
            return scope, seen[0]

        untrusted_original, untrusted_seen = asyncio.run(exercise(False))
        self.assertEqual(untrusted_seen["scheme"], "http")
        self.assertIn((b"host", b"service.internal"), untrusted_seen["headers"])
        self.assertEqual(untrusted_original["scheme"], "http")

        _, trusted_seen = asyncio.run(exercise(True))
        self.assertEqual(trusted_seen["scheme"], "https")
        self.assertIn((b"host", b"profile.example"), trusted_seen["headers"])


if __name__ == "__main__":
    unittest.main()
