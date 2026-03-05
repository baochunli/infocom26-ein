from __future__ import annotations

import copy
import io
import zipfile
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}

ET.register_namespace("w", W_NS)


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets" / "files"
TEMPLATE_PATH = ASSETS_DIR / "workshop-program-template.docx"
PROGRAM_HTML = ROOT / "program.html"
COMMITTEE_HTML = ROOT / "committee.html"
OUTPUT_DOCX = ASSETS_DIR / "ein26-program.docx"


def w_tag(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def normalize_spaces(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def to_24h_range(label: str) -> str:
    mapping = {
        "8:20 a.m. to 12:00 p.m.": "08:20 – 12:00",
        "2:00 p.m. to 6:00 p.m.": "14:00 – 18:00",
    }
    return mapping.get(label, label)


def load_template_body() -> tuple[ET.Element, list[ET.Element], ET.Element]:
    with zipfile.ZipFile(TEMPLATE_PATH) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    body = root.find("w:body", NS)
    assert body is not None
    paragraphs = body.findall("w:p", NS)
    sect_pr = body.find("w:sectPr", NS)
    assert sect_pr is not None
    return root, paragraphs, sect_pr


def clear_paragraph_text(paragraph: ET.Element) -> ET.Element:
    clone = copy.deepcopy(paragraph)
    for child in list(clone):
        if child.tag == w_tag("r"):
            clone.remove(child)
    return clone


def first_run_props(paragraph: ET.Element) -> ET.Element | None:
    for run in paragraph.findall("w:r", NS):
        props = run.find("w:rPr", NS)
        if props is not None:
            return copy.deepcopy(props)
    para_props = paragraph.find("w:pPr", NS)
    if para_props is not None:
        props = para_props.find("w:rPr", NS)
        if props is not None:
            return copy.deepcopy(props)
    return None


def add_text_run(paragraph: ET.Element, text: str, *, italic: bool = False) -> None:
    run = ET.SubElement(paragraph, w_tag("r"))
    props = first_run_props(paragraph)
    if props is not None:
        run.append(props)
        if italic and props.find("w:i", NS) is None:
            ET.SubElement(props, w_tag("i"))
            ET.SubElement(props, w_tag("iCs"))
    elif italic:
        props = ET.SubElement(run, w_tag("rPr"))
        ET.SubElement(props, w_tag("i"))
        ET.SubElement(props, w_tag("iCs"))

    text_el = ET.SubElement(run, w_tag("t"))
    if text[:1].isspace() or text[-1:].isspace():
        text_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_el.text = text


def make_paragraph(template: ET.Element, text: str) -> ET.Element:
    paragraph = clear_paragraph_text(template)
    if text:
        add_text_run(paragraph, text)
    return paragraph


def extract_committee() -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(COMMITTEE_HTML.read_text(encoding="utf-8"), "html.parser")
    chairs: list[str] = []
    committee: list[str] = []
    for section in soup.select("main .page-section"):
        heading = section.select_one("h2")
        if heading is None:
            continue
        title = normalize_spaces(heading.get_text(" ", strip=True))
        members = []
        for li in section.select("li"):
            name_el = li.select_one(".highlight")
            aff_el = li.select_one(".committee-affiliation")
            if name_el is None or aff_el is None:
                continue
            name = normalize_spaces(name_el.get_text(" ", strip=True))
            affiliation = normalize_spaces(aff_el.get_text(" ", strip=True)).lstrip("—").strip()
            members.append(f"{name} ({affiliation})")
        if title in {"General Chair", "Technical Program Committee Co-Chairs"}:
            chairs.extend(members)
        else:
            committee.extend(members)
    return committee, chairs


def extract_program() -> dict:
    soup = BeautifulSoup(PROGRAM_HTML.read_text(encoding="utf-8"), "html.parser")
    hero = soup.select_one("section.page-hero")
    assert hero is not None

    page_title = normalize_spaces(soup.title.get_text(" ", strip=True))
    if "–" in page_title:
        title = page_title.split("–", 1)[1].strip()
    else:
        short_title = normalize_spaces(hero.select_one(".page-title").get_text(" ", strip=True))
        title = f"INFOCOM 2026 Workshop on {short_title}"
    subtitle = normalize_spaces(hero.select_one(".page-subtitle").get_text(" ", strip=True))

    meta = {}
    for card in hero.select(".program-meta-card"):
        key = normalize_spaces(card.select_one("strong").get_text(" ", strip=True))
        value = normalize_spaces(card.select_one("span").get_text(" ", strip=True))
        meta[key] = value

    schedule = []
    for article in soup.select(".program-list > article.program-item"):
        time = normalize_spaces(article.select_one(".program-time").get_text(" ", strip=True))
        label_el = article.select_one(".program-label")
        h3 = article.select_one("h3")
        h4 = article.select_one("h4")
        note_el = article.select_one(".program-session-note")
        authors_el = article.select_one(".program-authors")

        note_lines: list[str] = []
        if note_el is not None:
            if note_el.find("br") is not None:
                note_lines = [
                    normalize_spaces(part)
                    for part in note_el.get_text("\n", strip=True).split("\n")
                    if normalize_spaces(part) and not normalize_spaces(part).startswith("Abstract:")
                ]
            else:
                note_text = normalize_spaces(note_el.get_text(" ", strip=True))
                if note_text:
                    note_lines = [note_text]

        schedule.append(
            {
                "time": time,
                "label": normalize_spaces(label_el.get_text(" ", strip=True)) if label_el else None,
                "title": normalize_spaces((h3 or h4).get_text(" ", strip=True)),
                "note_lines": note_lines,
                "authors": normalize_spaces(authors_el.get_text(" ", strip=True))
                if authors_el
                else None,
                "is_paper": h4 is not None,
            }
        )

    return {"title": title, "subtitle": subtitle, "meta": meta, "schedule": schedule}


def build_document_xml() -> bytes:
    root, template_paragraphs, sect_pr = load_template_body()
    committee_members, chairs = extract_committee()
    program = extract_program()

    body = root.find("w:body", NS)
    assert body is not None
    for child in list(body):
        body.remove(child)

    p_title = template_paragraphs[0]
    p_blank = template_paragraphs[1]
    p_meta = template_paragraphs[2]
    p_desc = template_paragraphs[3]
    p_committee_heading = template_paragraphs[4]
    p_committee_item = template_paragraphs[5]
    p_committee_more = template_paragraphs[6]
    p_committee_ellipsis = template_paragraphs[7]
    p_chairs_heading = template_paragraphs[9]
    p_chair_item = template_paragraphs[10]
    p_time = template_paragraphs[15]
    p_event = template_paragraphs[16]
    p_keynote = template_paragraphs[20]
    p_speaker = template_paragraphs[21]
    p_session_heading = template_paragraphs[25]
    p_paper_title = template_paragraphs[27]
    p_paper_authors = template_paragraphs[28]
    p_break_title = template_paragraphs[34]

    body.append(make_paragraph(p_title, program["title"]))
    body.append(make_paragraph(p_blank, ""))

    date_text = program["meta"].get("Date", "Monday, May 18, 2026")
    time_text = to_24h_range(program["meta"].get("Workshop time", "2:00 p.m. to 6:00 p.m."))
    location_text = program["meta"].get("Location", "Room Fuyo, IEEE INFOCOM 2026, Tokyo, Japan")
    location_suffix = location_text.replace("Room Fuyo, ", "", 1)
    meta_text = f"{date_text} ● {time_text} ● Room: Fuyo ● {location_suffix}"
    body.append(make_paragraph(p_meta, meta_text))
    body.append(make_paragraph(p_desc, program["subtitle"]))

    body.append(make_paragraph(p_committee_heading, "Committee"))
    committee_templates = [p_committee_item, p_committee_more, p_committee_ellipsis]
    for idx, member in enumerate(committee_members):
        body.append(make_paragraph(committee_templates[min(idx, len(committee_templates) - 1)], member))
    body.append(make_paragraph(p_blank, ""))

    body.append(make_paragraph(p_chairs_heading, "Chairs:"))
    for member in chairs:
        body.append(make_paragraph(p_chair_item, member))
    body.append(make_paragraph(p_blank, ""))
    body.append(make_paragraph(p_blank, ""))

    for item in program["schedule"]:
        if item["is_paper"]:
            paper_title = clear_paragraph_text(p_paper_title)
            add_text_run(paper_title, item["title"], italic=True)
            body.append(paper_title)
            if item["authors"]:
                body.append(make_paragraph(p_paper_authors, item["authors"]))
            body.append(make_paragraph(p_blank, ""))
            continue

        body.append(make_paragraph(p_time, item["time"]))
        if item["label"] in {"Break", "Opening", "Closing"}:
            body.append(make_paragraph(p_event, item["title"]))
            for line in item["note_lines"]:
                body.append(make_paragraph(p_desc, line))
            body.append(make_paragraph(p_blank, ""))
            continue

        if item["label"] == "Keynote":
            body.append(make_paragraph(p_keynote, f"Keynote: {item['title']}"))
            speaker_text = " | ".join(item["note_lines"]) if item["note_lines"] else "Speaker: TBD | Title: TBD"
            body.append(make_paragraph(p_speaker, speaker_text))
            body.append(make_paragraph(p_blank, ""))
            continue

        if item["label"] and item["label"].startswith("Session"):
            session_title = f"{item['label']}: {item['title']}"
            body.append(make_paragraph(p_session_heading, session_title))
            body.append(make_paragraph(p_blank, ""))
            continue

        body.append(make_paragraph(p_break_title, item["title"]))
        body.append(make_paragraph(p_blank, ""))

    body.append(copy.deepcopy(sect_pr))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_docx() -> None:
    new_document_xml = build_document_xml()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    buffer = io.BytesIO()
    with zipfile.ZipFile(TEMPLATE_PATH) as src, zipfile.ZipFile(buffer, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_document_xml
            dst.writestr(item, data)

    OUTPUT_DOCX.write_bytes(buffer.getvalue())


if __name__ == "__main__":
    write_docx()
