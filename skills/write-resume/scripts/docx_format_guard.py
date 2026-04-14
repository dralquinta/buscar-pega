#!/usr/bin/env python3
"""Detect formatting and layout drift between an original and revised DOCX."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NAMESPACES = {"w": WORD_NAMESPACE}
TEXT_TAGS = {"t", "delText", "instrText"}
DROP_TAGS = {"proofErr", "lastRenderedPageBreak"}
VOLATILE_ATTRS = {"rsidR", "rsidRDefault", "rsidP", "rsidRPr", "paraId", "textId"}
EXACT_COMPARE_PARTS = {
    "word/styles.xml",
    "word/numbering.xml",
    "word/fontTable.xml",
    "word/settings.xml",
    "word/webSettings.xml",
    "word/theme/theme1.xml",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "word/comments.xml",
}
EXACT_COMPARE_PREFIXES = (
    "word/header",
    "word/footer",
    "word/media/",
    "word/embeddings/",
    "word/charts/",
    "word/diagrams/",
)


@dataclass
class GuardReport:
    passed: bool
    failures: list[str]
    warnings: list[str]


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def normalize_tree(element: ET.Element, strip_text: bool) -> None:
    for attr_name in list(element.attrib):
        if local_name(attr_name) in VOLATILE_ATTRS:
            del element.attrib[attr_name]

    for child in list(element):
        if local_name(child.tag) in DROP_TAGS:
            element.remove(child)
            continue
        normalize_tree(child, strip_text=strip_text)

    if strip_text and local_name(element.tag) in TEXT_TAGS:
        element.text = ""
    elif element.text is not None:
        element.text = element.text.strip() or None

    element.tail = None


def normalized_xml(data: bytes, *, strip_text: bool) -> bytes:
    root = ET.fromstring(data)
    normalize_tree(root, strip_text=strip_text)
    return ET.tostring(root, encoding="utf-8")


def entry_names(docx: zipfile.ZipFile) -> set[str]:
    return set(docx.namelist())


def compare_exact_parts(
    original: zipfile.ZipFile,
    revised: zipfile.ZipFile,
    failures: list[str],
) -> None:
    original_names = entry_names(original)
    revised_names = entry_names(revised)

    for part in sorted(EXACT_COMPARE_PARTS):
        in_original = part in original_names
        in_revised = part in revised_names
        if in_original != in_revised:
            failures.append(f"Package part mismatch: {part} exists only in one file.")
            continue
        if in_original and original.read(part) != revised.read(part):
            failures.append(f"Formatting package part changed: {part}")

    for prefix in EXACT_COMPARE_PREFIXES:
        original_parts = sorted(name for name in original_names if name.startswith(prefix))
        revised_parts = sorted(name for name in revised_names if name.startswith(prefix))
        if original_parts != revised_parts:
            failures.append(f"Package entries changed under {prefix}")
            continue
        for name in original_parts:
            if original.read(name) != revised.read(name):
                failures.append(f"Non-text asset changed: {name}")


def extract_paragraph_texts(document_xml: bytes) -> list[str]:
    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:body//w:p", NAMESPACES):
        chunks: list[str] = []
        for text_node in paragraph.findall(".//w:t", NAMESPACES):
            chunks.append(text_node.text or "")
        paragraphs.append(" ".join("".join(chunks).split()))
    return paragraphs


def compare_document_structure(
    original: zipfile.ZipFile,
    revised: zipfile.ZipFile,
    failures: list[str],
    warnings: list[str],
) -> None:
    document_name = "word/document.xml"
    original_names = entry_names(original)
    revised_names = entry_names(revised)
    if document_name not in original_names or document_name not in revised_names:
        failures.append("word/document.xml is missing from one of the DOCX files.")
        return

    original_document = original.read(document_name)
    revised_document = revised.read(document_name)

    original_fingerprint = normalized_xml(original_document, strip_text=True)
    revised_fingerprint = normalized_xml(revised_document, strip_text=True)
    if original_fingerprint != revised_fingerprint:
        failures.append("Main document formatting/layout structure changed in word/document.xml")

    original_paragraphs = extract_paragraph_texts(original_document)
    revised_paragraphs = extract_paragraph_texts(revised_document)

    if len(original_paragraphs) != len(revised_paragraphs):
        failures.append(
            "Main document paragraph count changed "
            f"({len(original_paragraphs)} -> {len(revised_paragraphs)})"
        )
        return

    for index, (before, after) in enumerate(zip(original_paragraphs, revised_paragraphs), start=1):
        before_length = len(before)
        after_length = len(after)
        if before_length == 0 or after_length <= before_length:
            continue
        if after_length - before_length >= 30 and after_length / before_length >= 1.35:
            warnings.append(
                "Paragraph "
                f"{index} expanded from {before_length} to {after_length} characters; "
                "review for visual reflow or page spillover."
            )
        if len(warnings) >= 10:
            warnings.append("Additional paragraph expansion warnings were omitted.")
            break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether a revised DOCX changed formatting or layout relative to the original."
    )
    parser.add_argument("original", help="Path to the original DOCX file")
    parser.add_argument("revised", help="Path to the revised DOCX file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result as JSON",
    )
    return parser.parse_args()


def load_docx(path: str) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"Not a valid DOCX/ZIP file: {path}") from exc


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    warnings: list[str] = []

    with load_docx(args.original) as original, load_docx(args.revised) as revised:
        compare_exact_parts(original, revised, failures)
        compare_document_structure(original, revised, failures, warnings)

    report = GuardReport(passed=not failures, failures=failures, warnings=warnings)

    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        if report.passed:
            print("Format guard passed.")
        else:
            print("Format guard failed.")
        if report.failures:
            print("")
            print("Failures:")
            for failure in report.failures:
                print(f"- {failure}")
        if report.warnings:
            print("")
            print("Warnings:")
            for warning in report.warnings:
                print(f"- {warning}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
