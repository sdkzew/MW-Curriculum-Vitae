import io
import tempfile
import unittest
from docx import Document
from pathlib import Path
from unittest.mock import patch

from app import create_app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.upload_directory = tempfile.TemporaryDirectory()
        self.app = create_app(self.upload_directory.name, testing=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.upload_directory.cleanup()

    def csrf_token(self):
        self.client.get("/")
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def test_security_headers_are_present(self):
        response = self.client.get("/")

        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_builder_page_is_available(self):
        response = self.client.get("/builder")

        self.assertEqual(response.status_code, 200)
        self.assertIn("CREEAZĂ CV".encode(), response.data)

    def test_builder_export_requires_csrf_token(self):
        response = self.client.post(
            "/builder/export",
            data={"full_name": "Alex Morgan", "template": "ats"},
            follow_redirects=True,
        )

        self.assertIn("Sesiunea a expirat".encode(), response.data)

    def test_builder_exports_valid_docx(self):
        response = self.client.post(
            "/builder/export",
            data={
                "csrf_token": self.csrf_token(),
                "template": "modern",
                "full_name": "Alex Morgan",
                "headline": "Product Designer",
                "experience_role": "Lead Designer",
                "experience_organization": "MORPH WRLD",
                "experience_details": "Created a design system.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn("Alex_Morgan-CV-modern.docx", response.headers["Content-Disposition"])
        document = Document(io.BytesIO(response.data))
        self.assertIn("Alex Morgan", "\n".join(paragraph.text for paragraph in document.paragraphs))

    def test_post_requires_csrf_token(self):
        response = self.client.post(
            "/analyze",
            data={"cv_file": (io.BytesIO(b"fake"), "cv.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertIn("Sesiunea a expirat".encode(), response.data)

    def test_rejects_unsupported_extension(self):
        response = self.client.post(
            "/analyze",
            data={
                "csrf_token": self.csrf_token(),
                "cv_file": (io.BytesIO(b"text"), "cv.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertIn("Format nesuportat".encode(), response.data)

    @patch("app.extract_text", return_value="Experience Education Skills Summary Projects " * 70)
    def test_successful_analysis_removes_temporary_upload(self, _extract_text):
        response = self.client.post(
            "/analyze",
            data={
                "csrf_token": self.csrf_token(),
                "cv_file": (io.BytesIO(b"fake pdf"), "cv.pdf"),
                "job_description": "Python engineer",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("SCOR ATS".encode(), response.data)
        self.assertEqual(list(Path(self.upload_directory.name).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
