from typing import List, Dict
from llama_parse import LlamaParse


class DocumentParser:
    """Wrapper for LlamaParse to parse documents."""

    def __init__(
        self,
        llamaparse_api_key: str,
        result_type: str = "markdown"
    ) -> None:
        """Initialize the DocumentParser.

        Args:
            result_type: The result type for parsing.
        """
        self.parser = LlamaParse(
            result_type=result_type,
            api_key=llamaparse_api_key
        )

    def parse_document(self, pdf_path: str, image_download_dir: str) -> List[Dict]:
        """Parse a document to extract markdown pages and images.

        Args:
            pdf_path: The path to the PDF file.
            image_download_dir: The directory to download images.

        Returns:
            A list of dictionaries representing parsed markdown pages.
        """
        md_json_objs = self.parser.get_json_result(pdf_path)
        md_json_list = md_json_objs[0]["pages"]
        self.parser.get_images(md_json_objs, download_path=image_download_dir)
        return md_json_list

