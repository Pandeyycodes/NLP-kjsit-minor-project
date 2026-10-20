"""Extract text from an uploaded PDF in memory using PyMuPDF."""

import pymupdf

# Vercel Functions accept request bodies of at most 4.5 MB, so a 4 MB file
# (plus multipart form overhead) is the largest that can always get through.
MAX_PDF_BYTES = 4 * 1024 * 1024
PDF_LIMIT_TEXT = f"{MAX_PDF_BYTES // (1024 * 1024)} MB"
PDF_SIGNATURE = b"%PDF-"


class PdfError(ValueError):
    """A problem with the uploaded PDF, with a message safe to show the user."""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def extract_pdf_text(data: bytes) -> tuple[str, int]:
    """Return (text, page_count). Pages are separated by blank lines."""
    if not data:
        raise PdfError("The uploaded file is empty.")
    # The file contents decide, not its name or Content-Type. The PDF header
    # must appear within the first 1024 bytes.
    if PDF_SIGNATURE not in data[:1024]:
        raise PdfError("This file is not a PDF. Please upload a .pdf document.", 415)
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise PdfError("This PDF is damaged or could not be read.")

    with document:  # closes the document even if extraction fails
        if document.needs_pass:
            raise PdfError("This PDF is password-protected. Please upload an unlocked copy.")
        if document.page_count == 0:
            raise PdfError("This PDF has no pages.")
        try:
            pages = [page.get_text("text").strip() for page in document]
        except Exception:
            raise PdfError("The text in this PDF could not be read.")
        return "\n\n".join(page for page in pages if page), document.page_count
