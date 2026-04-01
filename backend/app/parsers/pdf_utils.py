import io
from typing import List

import pdfplumber


def extract_tables_from_pdf(
    pdf_bytes: bytes, password: str = ""
) -> List[List[List[str]]]:
    """Extract all tables from all pages of a PDF.

    Args:
        pdf_bytes: Raw PDF file content.
        password: Optional password for encrypted PDFs.

    Returns:
        A list of tables, where each table is a list of rows,
        and each row is a list of cell strings.
    """
    all_tables: List[List[List[str]]] = []
    open_kwargs = {}
    if password:
        open_kwargs["password"] = password

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), **open_kwargs) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        cleaned_table: List[List[str]] = []
                        for row in table:
                            cleaned_row = [
                                (cell.strip() if cell else "") for cell in row
                            ]
                            cleaned_table.append(cleaned_row)
                        all_tables.append(cleaned_table)
    except Exception:
        return []

    return all_tables


def extract_text_from_pdf(pdf_bytes: bytes, password: str = "") -> str:
    """Extract full text content from all pages of a PDF.

    Args:
        pdf_bytes: Raw PDF file content.
        password: Optional password for encrypted PDFs.

    Returns:
        Concatenated text from all pages.
    """
    text_parts: List[str] = []
    open_kwargs = {}
    if password:
        open_kwargs["password"] = password

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), **open_kwargs) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception:
        return ""

    return "\n".join(text_parts)
