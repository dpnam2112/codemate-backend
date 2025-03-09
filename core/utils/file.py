import boto3
from botocore.exceptions import NoCredentialsError
import uuid
import os
from dotenv import load_dotenv
from typing import Optional, Tuple, Dict, Any
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
async def update_course_image_s3(existing_image_key: Optional[str], new_file_content: bytes, new_file_name: str) -> Tuple[str, str]:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS3Settings.AWS3_ACCESS_KEY_ID,
        aws_secret_access_key=AWS3Settings.AWS3_SECRET_ACCESS_KEY,
    )
    
    if existing_image_key:
        try:
            s3.delete_object(
                Bucket=AWS3Settings.AWS3_BUCKET_NAME,
                Key=existing_image_key
            )
        except Exception as e:
            print(f"Error deleting previous image: {e}")
    
    new_s3_key = await upload_to_s3(new_file_content, new_file_name)
    
    presigned_url = generate_presigned_url(new_s3_key)
    
    return new_s3_key, presigned_url
async def get_s3_image(s3_key: str) -> Dict[str, Any]:
    bucket_name = AWS3Settings.AWS3_BUCKET_NAME
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS3Settings.AWS3_ACCESS_KEY_ID,
        aws_secret_access_key=AWS3Settings.AWS3_SECRET_ACCESS_KEY,
    )
    
    try:
        response = s3.get_object(
            Bucket=bucket_name,
            Key=s3_key
        )
        
        content_type = response.get('ContentType')
        
        if not content_type:
            file_extension = os.path.splitext(s3_key)[1].lower()
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(file_extension, 'application/octet-stream')
        
        return {
            'content': response['Body'].read(),
            'content_type': content_type
        }
        
    except NoCredentialsError:
        raise RuntimeError("AWS credentials are not configured properly.")
    except Exception as e:
        raise RuntimeError(f"Error retrieving image from S3: {e}")