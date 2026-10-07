import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.serving import make_server
from werkzeug.utils import secure_filename

from analyzer.ats_scorer import score_cv
from analyzer.cv_builder import (
    CVBuildError,
    build_cv_document,
    prepare_profile_photo,
    profile_from_form,
)
from analyzer.extractor import DocumentExtractionError, extract_text
from analyzer.i18n import normalize_language, translate
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

    def active_language() -> str:
        return normalize_language(session.get("language"))

    def translated(key: str, **values) -> str:
        return translate(key, active_language(), **values)

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["t"] = translated

    @app.context_processor
    def inject_language():
        return {"lang": active_language()}

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
        flash(translated("file_too_large"))
        endpoint = "builder" if request.path.startswith("/builder") else "index"
        return redirect(url_for(endpoint))

    @app.post("/language/<language>")
    def set_language(language: str):
        submitted_token = request.form.get("csrf_token", "")
        expected_token = session.get("csrf_token", "")
        if not expected_token or not secrets.compare_digest(submitted_token, expected_token):
            flash(translated("session_expired"))
            return redirect(url_for("index"))

        session["language"] = normalize_language(language)
        destination = request.form.get("next", "/")
        if destination not in {"/", "/builder"}:
            destination = "/"
        return redirect(destination)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/builder")
    def builder():
        return render_template("builder.html")

    @app.post("/builder/export")
    def export_cv():
        submitted_token = request.form.get("csrf_token", "")
        expected_token = session.get("csrf_token", "")
        if not expected_token or not secrets.compare_digest(submitted_token, expected_token):
            flash(translated("session_expired"))
            return redirect(url_for("builder"))

        try:
            language = active_language()
            profile, template = profile_from_form(request.form, language)
            photo = prepare_profile_photo(request.files.get("profile_photo"), language)
            document = build_cv_document(profile, template, photo, language)
        except CVBuildError as error:
            flash(str(error))
            return redirect(url_for("builder"))

        safe_name = secure_filename(profile.full_name) or "Curriculum-Vitae"
        return send_file(
            document,
            as_attachment=True,
            download_name=f"{safe_name}-CV-{template}.docx",
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            max_age=0,
        )

    @app.post("/analyze")
    def analyze():
        submitted_token = request.form.get("csrf_token", "")
        expected_token = session.get("csrf_token", "")
        if not expected_token or not secrets.compare_digest(submitted_token, expected_token):
            flash(translated("session_expired"))
            return redirect(url_for("index"))

        file = request.files.get("cv_file")
        if file is None or not file.filename:
            flash(translated("no_file"))
            return redirect(url_for("index"))

        extension = file_extension(file.filename)
        if extension not in ALLOWED_EXTENSIONS:
            flash(translated("unsupported_cv"))
            return redirect(url_for("index"))

        job_description = request.form.get("job_description", "").strip()
        if len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
            flash(translated("job_too_long"))
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
                flash(translated("cv_read_error"))
                return redirect(url_for("index"))

            if not cv_text.strip():
                flash(translated("cv_empty"))
                return redirect(url_for("index"))

            language = active_language()
            ats_result = score_cv(cv_text, language)
            match_result = match_job(cv_text, job_description, language)
            suggestions = generate_suggestions(
                cv_text,
                ats_result.score,
                match_result.score,
                match_result.missing_keywords,
                language,
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
            title="MORPH WRLD — Curriculum Vitae",
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
