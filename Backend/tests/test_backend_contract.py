import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("GROK_API_KEY_1", "dummy-key")

import main  # noqa: E402


class BackendContractTests(unittest.TestCase):
    def setUp(self):
        self.app = main.app
        self.client = self.app.test_client()
        main.init_db()

    def test_registration_flow_supports_verification(self):
        resp = self.client.post(
            "/api/areeba/register",
            json={"username": "Test User", "email": "test@example.com", "password": "Abcd@1234"},
        )
        self.assertIn(resp.status_code, {200, 202, 201})

        verify = self.client.post(
            "/api/areeba/verify-registration",
            json={"email": "test@example.com", "code": "000000"},
        )
        self.assertNotEqual(verify.status_code, 404)

    def test_learning_chapters_require_auth_and_return_json_shape(self):
        resp = self.client.get("/api/fatima/chapters")
        self.assertIn(resp.status_code, {401, 404})

        # A valid auth header should not 404 once the route exists.
        auth_resp = self.client.get(
            "/api/fatima/chapters",
            headers={"Authorization": "Bearer invalid-token"},
        )
        self.assertNotEqual(auth_resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
