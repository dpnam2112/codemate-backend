from services.parser import DocumentParser
from settings import env_settings

def main():
    parser = DocumentParser(env_settings.llamaparse_api_key)
    result = parser.parse_document(env_settings.pdf_path, image_download_dir="./images")
    print(result)

if __name__ == "__main__":
    main()
