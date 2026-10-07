from dataclasses import dataclass, field
from io import BytesIO
from itertools import zip_longest
from typing import Mapping

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from analyzer.i18n import translate


TEMPLATES = {"europass", "ats", "modern"}
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_PHOTO_BYTES = 3 * 1024 * 1024
MAX_PHOTO_PIXELS = 20_000_000


class CVBuildError(ValueError):
    """Raised when CV builder input is missing or exceeds safe limits."""


@dataclass
class Experience:
    role: str
    organization: str = ""
    location: str = ""
    dates: str = ""
    details: str = ""


@dataclass
class Education:
    qualification: str
    institution: str = ""
    location: str = ""
    dates: str = ""
    details: str = ""


@dataclass
class CVProfile:
    full_name: str
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    website: str = ""
    summary: str = ""
    skills: str = ""
    digital_skills: str = ""
    languages: str = ""
    certifications: str = ""
    projects: str = ""
    additional: str = ""
    experiences: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)


def _clean(value: object, limit: int, label: str, language: str = "ro") -> str:
    text = str(value or "").replace("\x00", "").strip()
    if len(text) > limit:
        raise CVBuildError(translate("field_too_long", language, label=label, limit=limit))
    return text


def _values(form: Mapping, key: str) -> list[str]:
    if hasattr(form, "getlist"):
        return list(form.getlist(key))
    value = form.get(key, [])
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def profile_from_form(form: Mapping, language: str = "ro") -> tuple[CVProfile, str]:
    template = _clean(form.get("template", "ats"), 20, "Template", language)
    if template not in TEMPLATES:
        raise CVBuildError(translate("template_unknown", language))

    full_name = _clean(form.get("full_name"), 120, translate("full_name", language), language)
    if not full_name:
        raise CVBuildError(translate("name_required", language))

    experience_rows = zip_longest(
        _values(form, "experience_role"),
        _values(form, "experience_organization"),
        _values(form, "experience_location"),
        _values(form, "experience_dates"),
        _values(form, "experience_details"),
        fillvalue="",
    )
    experiences = []
    for role, organization, location, dates, details in list(experience_rows)[:8]:
        role = _clean(role, 180, translate("role", language), language)
        if not role:
            continue
        experiences.append(
            Experience(
                role=role,
                organization=_clean(organization, 180, translate("organization", language), language),
                location=_clean(location, 120, translate("location", language), language),
                dates=_clean(dates, 100, translate("period", language), language),
                details=_clean(details, 4_000, translate("achievements", language), language),
            )
        )

    education_rows = zip_longest(
        _values(form, "education_qualification"),
        _values(form, "education_institution"),
        _values(form, "education_location"),
        _values(form, "education_dates"),
        _values(form, "education_details"),
        fillvalue="",
    )
    education = []
    for qualification, institution, location, dates, details in list(education_rows)[:8]:
        qualification = _clean(qualification, 180, translate("qualification", language), language)
        if not qualification:
            continue
        education.append(
            Education(
                qualification=qualification,
                institution=_clean(institution, 180, translate("institution", language), language),
                location=_clean(location, 120, translate("location", language), language),
                dates=_clean(dates, 100, translate("period", language), language),
                details=_clean(details, 3_000, translate("details", language), language),
            )
        )

    profile = CVProfile(
        full_name=full_name,
        headline=_clean(form.get("headline"), 180, translate("professional_title", language), language),
        email=_clean(form.get("email"), 254, "Email", language),
        phone=_clean(form.get("phone"), 80, translate("phone", language), language),
        location=_clean(form.get("location"), 160, translate("location", language), language),
        linkedin=_clean(form.get("linkedin"), 300, "LinkedIn", language),
        website=_clean(form.get("website"), 300, "Website", language),
        summary=_clean(form.get("summary"), 4_000, translate("professional_summary", language), language),
        skills=_clean(form.get("skills"), 2_000, translate("skills", language), language),
        digital_skills=_clean(form.get("digital_skills"), 2_000, translate("digital_skills", language), language),
        languages=_clean(form.get("languages"), 2_000, translate("languages", language), language),
        certifications=_clean(form.get("certifications"), 2_000, translate("certifications", language), language),
        projects=_clean(form.get("projects"), 3_000, translate("projects", language), language),
        additional=_clean(form.get("additional"), 3_000, translate("additional_information", language), language),
        experiences=experiences,
        education=education,
    )
    return profile, template


def prepare_profile_photo(upload, language: str = "ro") -> BytesIO | None:
    if upload is None or not getattr(upload, "filename", ""):
        return None
    extension = str(upload.filename).rsplit(".", 1)[-1].lower()
    if extension not in PHOTO_EXTENSIONS:
        raise CVBuildError(translate("photo_invalid", language))

    payload = upload.stream.read(MAX_PHOTO_BYTES + 1)
    if len(payload) > MAX_PHOTO_BYTES:
        raise CVBuildError(translate("photo_too_large", language))
    try:
        source = Image.open(BytesIO(payload))
        if source.width * source.height > MAX_PHOTO_PIXELS:
            raise CVBuildError(translate("photo_invalid", language))
        source.load()
        source = ImageOps.exif_transpose(source).convert("RGB")
    except CVBuildError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise CVBuildError(translate("photo_invalid", language)) from None

    square = ImageOps.fit(source, (600, 600), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", square.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 599, 599), fill=255)
    portrait = Image.new("RGBA", square.size, (0, 0, 0, 0))
    portrait.paste(square, (0, 0), mask)
    output = BytesIO()
    portrait.save(output, format="PNG", optimize=True)
    output.seek(0)
    return output


def _set_cell_shading(cell, color: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color)
    properties.append(shading)


def _set_cell_margins(cell, top=90, start=120, bottom=90, end=120) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        element = margins.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            margins.append(element)
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")


def _set_repeat_table_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    properties.append(repeat)


def _add_rule(paragraph, color: str, size: int = 8) -> None:
    properties = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    borders.append(bottom)
    properties.append(borders)


def _add_section_heading(document: Document, title: str, color: RGBColor, template: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(11)
    paragraph.paragraph_format.space_after = Pt(5)
    run = paragraph.add_run(title.upper())
    run.bold = True
    run.font.size = Pt(10 if template == "europass" else 9.5)
    run.font.color.rgb = color
    run.font.name = "Aptos Display"
    if template != "ats":
        _add_rule(paragraph, str(color), 7)


def _add_contact_line(document: Document, profile: CVProfile, color: RGBColor) -> None:
    contact = [profile.email, profile.phone, profile.location, profile.linkedin, profile.website]
    contact = [item for item in contact if item]
    if not contact:
        return
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(7)
    run = paragraph.add_run("  •  ".join(contact))
    run.font.size = Pt(8.5)
    run.font.color.rgb = color


def _add_bullets(document: Document, text: str) -> None:
    for line in (line.strip(" •\t-") for line in text.splitlines()):
        if not line:
            continue
        paragraph = document.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.left_indent = Cm(.45)
        paragraph.add_run(line)


def _add_experience(document: Document, item: Experience, accent: RGBColor) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(1)
    role = paragraph.add_run(item.role)
    role.bold = True
    role.font.size = Pt(10.5)
    role.font.color.rgb = accent
    if item.organization:
        paragraph.add_run(f"  |  {item.organization}").bold = True
    meta = " · ".join(value for value in (item.dates, item.location) if value)
    if meta:
        meta_paragraph = document.add_paragraph(meta)
        meta_paragraph.paragraph_format.space_after = Pt(3)
        meta_paragraph.runs[0].italic = True
        meta_paragraph.runs[0].font.size = Pt(8.5)
        meta_paragraph.runs[0].font.color.rgb = RGBColor(95, 99, 110)
    _add_bullets(document, item.details)


def _add_education(document: Document, item: Education, accent: RGBColor) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(1)
    qualification = paragraph.add_run(item.qualification)
    qualification.bold = True
    qualification.font.size = Pt(10.5)
    qualification.font.color.rgb = accent
    if item.institution:
        paragraph.add_run(f"  |  {item.institution}").bold = True
    meta = " · ".join(value for value in (item.dates, item.location) if value)
    if meta:
        meta_paragraph = document.add_paragraph(meta)
        meta_paragraph.paragraph_format.space_after = Pt(3)
        meta_paragraph.runs[0].italic = True
        meta_paragraph.runs[0].font.size = Pt(8.5)
        meta_paragraph.runs[0].font.color.rgb = RGBColor(95, 99, 110)
    if item.details:
        document.add_paragraph(item.details)


def _add_text_section(document: Document, title: str, value: str, accent: RGBColor, template: str) -> None:
    if not value:
        return
    _add_section_heading(document, title, accent, template)
    paragraph = document.add_paragraph(value)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.line_spacing = 1.08


def build_cv_document(
    profile: CVProfile,
    template: str,
    profile_photo: BytesIO | None = None,
    language: str = "ro",
) -> BytesIO:
    if template not in TEMPLATES:
        raise CVBuildError(translate("template_unknown", language))

    document = Document()
    section = document.sections[0]
    section.start_type = WD_SECTION.NEW_PAGE
    section.top_margin = Cm(1.45)
    section.bottom_margin = Cm(1.45)
    section.left_margin = Cm(1.65 if template != "europass" else 1.45)
    section.right_margin = Cm(1.65 if template != "europass" else 1.45)

    colors = {
        "europass": RGBColor(32, 88, 135),
        "ats": RGBColor(35, 38, 43),
        "modern": RGBColor(111, 63, 214),
    }
    accent = colors[template]
    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9.5)
    styles["Normal"].paragraph_format.space_after = Pt(3)

    if template == "europass":
        banner = document.add_table(rows=1, cols=2)
        banner.autofit = False
        banner.columns[0].width = Cm(4.2)
        banner.columns[1].width = Cm(13.2)
        left, right = banner.rows[0].cells
        _set_cell_shading(left, "205887")
        _set_cell_shading(right, "EEF4F8")
        _set_cell_margins(left, 180, 180, 180, 180)
        _set_cell_margins(right, 180, 220, 180, 220)
        left_paragraph = left.paragraphs[0]
        left_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if profile_photo:
            profile_photo.seek(0)
            left_paragraph.add_run().add_picture(profile_photo, width=Cm(2.45))
            left_paragraph = left.add_paragraph()
            left_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        label = left_paragraph.add_run("CURRICULUM\nVITAE")
        label.bold = True
        label.font.color.rgb = RGBColor(255, 255, 255)
        label.font.size = Pt(13)
        name = right.paragraphs[0].add_run(profile.full_name)
        name.bold = True
        name.font.size = Pt(24)
        name.font.color.rgb = accent
        if profile.headline:
            right.add_paragraph(profile.headline)
        note = document.add_paragraph(translate("europass_independent", language))
        note.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        note.runs[0].font.size = Pt(7)
        note.runs[0].font.color.rgb = RGBColor(125, 132, 142)
    else:
        if template == "modern":
            accent_line = document.add_paragraph()
            _add_rule(accent_line, "6F3FD6", 22)
        if profile_photo:
            header = document.add_table(rows=1, cols=2)
            header.autofit = False
            header.columns[0].width = Cm(3.1)
            header.columns[1].width = Cm(14.5)
            image_cell, name_cell = header.rows[0].cells
            profile_photo.seek(0)
            image_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            image_cell.paragraphs[0].add_run().add_picture(profile_photo, width=Cm(2.45))
            name = name_cell.paragraphs[0]
            name.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else:
            name = document.add_paragraph()
            name.alignment = WD_ALIGN_PARAGRAPH.CENTER
        name.paragraph_format.space_after = Pt(2)
        run = name.add_run(profile.full_name)
        run.bold = True
        run.font.name = "Aptos Display"
        run.font.size = Pt(26 if template == "modern" else 23)
        run.font.color.rgb = accent
        if profile.headline:
            if profile_photo:
                headline = name_cell.add_paragraph(profile.headline)
                headline.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:
                headline = document.add_paragraph(profile.headline)
                headline.alignment = WD_ALIGN_PARAGRAPH.CENTER
            headline.paragraph_format.space_after = Pt(4)
            headline.runs[0].font.size = Pt(10.5)

    _add_contact_line(document, profile, accent)
    _add_text_section(document, translate("professional_summary", language), profile.summary, accent, template)

    if profile.experiences:
        _add_section_heading(document, translate("work_experience", language), accent, template)
        for item in profile.experiences:
            _add_experience(document, item, accent)

    if profile.education:
        _add_section_heading(document, translate("education_training", language), accent, template)
        for item in profile.education:
            _add_education(document, item, accent)

    _add_text_section(document, translate("skills", language), profile.skills, accent, template)
    _add_text_section(document, translate("digital_skills", language), profile.digital_skills, accent, template)
    _add_text_section(document, translate("languages", language), profile.languages, accent, template)
    _add_text_section(document, translate("projects", language), profile.projects, accent, template)
    _add_text_section(document, translate("certifications", language), profile.certifications, accent, template)
    _add_text_section(document, translate("additional_information", language), profile.additional, accent, template)

    properties = document.core_properties
    properties.title = f"Curriculum Vitae — {profile.full_name}"
    properties.subject = "Curriculum Vitae generated locally with MORPH WRLD CV Studio"
    properties.author = profile.full_name
    properties.comments = "Generated locally. Europass-inspired is not an official Europass document."

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return output
