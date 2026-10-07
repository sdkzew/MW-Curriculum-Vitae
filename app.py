import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.serving import make_server

from analyzer.ats_scorer import score_cv
from analyzer.extractor import DocumentExtractionError, extract_text
from analyzer.matcher import match_job
from analyzer.suggestions import generate_suggestions


ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_JOB_DESCRIPTION_CHARS = 50_000


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def create_app(upload_folder: str | None = None, testing: bool = False) -> Flask:
    app = Flask(
        __name__,
        template_folder=resource_path("templates"),
        static_folder=resource_path("static"),
    )
    app.config.update(
        SECRET_KEY=os.environ.get("CV_ANALYZER_SECRET_KEY") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
        UPLOAD_FOLDER=upload_folder
        or os.path.join(tempfile.gettempdir(), "ai-cv-analyzer-uploads"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        TESTING=testing,
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    def csrf_token() -> str:
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(_error):
        flash("Fisierul este prea mare. Limita este de 5 MB.")
        return redirect(url_for("index"))

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/analyze")
    def analyze():
        submitted_token = request.form.get("csrf_token", "")
        expected_token = session.get("csrf_token", "")
        if not expected_token or not secrets.compare_digest(submitted_token, expected_token):
            flash("Sesiunea a expirat. Incearca din nou.")
            return redirect(url_for("index"))

        file = request.files.get("cv_file")
        if file is None or not file.filename:
            flash("Nu ai selectat niciun fisier.")
            return redirect(url_for("index"))

        extension = file_extension(file.filename)
        if extension not in ALLOWED_EXTENSIONS:
            flash("Format nesuportat. Uploadeaza un fisier PDF sau DOCX.")
            return redirect(url_for("index"))

        job_description = request.form.get("job_description", "").strip()
        if len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
            flash("Descrierea jobului este prea lunga.")
            return redirect(url_for("index"))

        descriptor, filepath = tempfile.mkstemp(
            prefix="cv-", suffix=f".{extension}", dir=app.config["UPLOAD_FOLDER"]
        )
        os.close(descriptor)

        try:
            file.save(filepath)
            try:
                cv_text = extract_text(filepath)
            except DocumentExtractionError:
                app.logger.exception("CV extraction failed")
                flash("Fisierul nu a putut fi citit. Verifica daca este un PDF sau DOCX valid.")
                return redirect(url_for("index"))

            if not cv_text.strip():
                flash("Nu s-a putut extrage text din fisier. Incearca un alt PDF sau DOCX.")
                return redirect(url_for("index"))

            ats_result = score_cv(cv_text)
            match_result = match_job(cv_text, job_description)
            suggestions = generate_suggestions(
                cv_text,
                ats_result.score,
                match_result.score,
                match_result.missing_keywords,
            )

            return render_template(
                "results.html",
                ats=ats_result,
                match=match_result,
                suggestions=suggestions,
                has_job=bool(job_description),
                word_count=len(cv_text.split()),
            )
        finally:
            try:
                os.remove(filepath)
            except FileNotFoundError:
                pass

    return app


app = create_app()


def run_desktop() -> None:
    server = make_server("127.0.0.1", 0, app, threaded=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        import webview

        webview.create_window(
            title="MORPH WRLD — CV Studio",
            url=f"http://127.0.0.1:{server.server_port}",
            width=1440,
            height=900,
            min_size=(980, 680),
            resizable=True,
        )
        webview.start()
    finally:
        server.shutdown()
        server_thread.join(timeout=5)


if __name__ == "__main__":
    run_desktop()
