import boto3
from botocore.exceptions import NoCredentialsError
import uuid
from core.settings import settings
async def upload_to_s3(file_content: bytes, file_name: str, bucket_name: str) -> str:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS3_SECRET_ACCESS_KEY,
    )

    s3_key = f"documents/{uuid.uuid4()}-{file_name}"
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_content,
            ACL="private", 
        )
        return s3_key
    except NoCredentialsError:
        raise RuntimeError("AWS credentials are not configured properly.")
