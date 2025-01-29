import boto3
from botocore.exceptions import NoCredentialsError
import uuid
import os
from dotenv import load_dotenv

load_dotenv()
class AWS3Settings:
    AWS3_ACCESS_KEY_ID = os.getenv("AWS3_ACCESS_KEY_ID")
    AWS3_SECRET_ACCESS_KEY = os.getenv("AWS3_SECRET_ACCESS_KEY")
    AWS3_REGION = os.getenv("AWS3_REGION")
    AWS3_BUCKET_NAME = os.getenv("AWS3_BUCKET_NAME")
async def upload_to_s3(file_content: bytes, file_name: str) -> str:
    bucket_name = AWS3Settings.AWS3_BUCKET_NAME
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS3Settings.AWS3_ACCESS_KEY_ID,
        aws_secret_access_key=AWS3Settings.AWS3_SECRET_ACCESS_KEY,
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
def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    bucket_name = AWS3Settings.AWS3_BUCKET_NAME
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS3Settings.AWS3_ACCESS_KEY_ID,
        aws_secret_access_key=AWS3Settings.AWS3_SECRET_ACCESS_KEY,
    )
    try:
        # Generate a presigned URL to access the object
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": s3_key},
            ExpiresIn=expiration,  # URL will expire after 'expiration' seconds
        )
        return url
    except NoCredentialsError:
        raise RuntimeError("AWS credentials are not configured properly.")
    except Exception as e:
        raise RuntimeError(f"Error generating presigned URL: {e}")
