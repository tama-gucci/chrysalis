"""Bounded, read-only extraction of explicitly selected vault originals."""
from pathlib import Path
from io import BytesIO
from helpers.records import compute_revision, sanitize_untrusted_payload
from System.scripts.vault_paths import vault_path, native_path


def inspect(vault, *, path, extract=False, first_page=1, page_count=10):
    if not isinstance(path, str) or not path.startswith("Attachments/Originals/"):
        raise ValueError("Select an original inside Attachments/Originals")
    original = native_path(vault_path(vault, path))
    with original.open("rb") as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    size = len(raw)
    if size > 32 * 1024 * 1024:
        raise ValueError("Select a smaller original; extraction limit is 32 MiB")
    result = {"status": "observed", "path": path, "sha256": compute_revision(raw), "bytes": size,
              "link": "[[" + path + "]]", "embed": "![[" + path + "]]",
              "preview": "obsidian" if original.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".txt", ".md"} else "external_app",
              "extraction_status": "not_requested"}
    if not extract:
        return result
    if original.suffix.lower() in {".txt", ".md", ".csv"}:
        if size > 1024 * 1024:
            raise ValueError("Text extraction limit is 1 MiB")
        text = raw.decode("utf-8")
        coverage = {"status": "complete", "pages_processed": None, "total_pages": None}
    elif original.suffix.lower() == ".pdf":
        if not isinstance(first_page, int) or first_page < 1 or not isinstance(page_count, int) or not 1 <= page_count <= 50:
            raise ValueError("Select 1–50 PDF pages with a one-based first page")
        text, coverage, has_text = pdf_text(raw, first_page, page_count)
        if not has_text:
            return {**result, "extraction_status": "ocr_required", "coverage": coverage}
    else:
        return {**result, "extraction_status": "ocr_required" if result["preview"] == "obsidian" else "unsupported_deferred"}
    if len(text.encode("utf-8")) > 1024 * 1024:
        raise ValueError("Extracted text exceeds 1 MiB; select fewer pages")
    return {**result, "extraction_status": "extracted", "coverage": coverage,
            "untrusted_text": sanitize_untrusted_payload(text, source_id=Path(path).stem, sha256_digest=result["sha256"])}


def pdf_text(raw, first_page, page_count):
    from pypdf import PdfReader, apply_configuration
    limit = 8 * 1024 * 1024
    with apply_configuration(maximum_declared_stream_length=limit, array_based_stream_maximum_output_length=limit,
        zlib_maximum_output_length=limit, lzw_maximum_output_length=limit, run_length_maximum_output_length=limit,
        jbig2_maximum_output_length=limit, image_maximum_buffer_size=limit, disable_legacy_handling=True):
        reader = PdfReader(BytesIO(raw), strict=True)
        total = len(reader.pages)
        end = min(total, first_page - 1 + page_count)
        if first_page > total:
            raise ValueError("First page exceeds the document")
        parts, text_size, has_text = [], 0, False
        for index in range(first_page - 1, end):
            page = reader.pages[index]
            contents = page.get_contents()
            if contents is not None and len(contents.get_data()) > limit:
                raise ValueError("PDF content stream exceeds extraction limit")
            text = page.extract_text() or ""
            has_text = has_text or bool(text.strip())
            text_size += len(text.encode("utf-8"))
            if text_size > 1024 * 1024:
                raise ValueError("Extracted text exceeds 1 MiB; select fewer pages")
            parts.append(f"Page {index + 1}:\n{text}")
        return "\n\n".join(parts), {"status": "complete" if first_page == 1 and end == total else "partial", "pages_processed": end - first_page + 1, "total_pages": total}, has_text
