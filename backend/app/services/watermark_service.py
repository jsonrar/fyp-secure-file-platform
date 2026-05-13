class WatermarkService:
    def is_supported(self, mime_type: str | None) -> bool:
        return mime_type in {"application/pdf", "image/png", "image/jpeg"}

    def apply_watermark_draft(self, file_path: str, user_label: str) -> str:
        """Placeholder.

        Real implementation can use PyMuPDF for PDF and Pillow for images.
        """
        return file_path
