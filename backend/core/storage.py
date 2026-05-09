"""
EVIDRA — MinIO Object Storage Client.

S3-compatible storage for forensic evidence files.
All file uploads/downloads go through this module.

Usage:
    from core.storage import storage
    s3_key = storage.upload_file(case_id, file_id, filename, file_bytes, content_type)
    data   = storage.download_file(s3_key)
"""
import io
import logging
from minio import Minio
from minio.error import S3Error
from core.config import settings

logger = logging.getLogger("evidra.storage")

_client: Minio | None = None


def get_minio() -> Minio:
    """Get or create the MinIO client."""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        # Ensure the evidence bucket exists
        if not _client.bucket_exists(settings.MINIO_BUCKET):
            _client.make_bucket(settings.MINIO_BUCKET)
            logger.info(f"Created MinIO bucket: {settings.MINIO_BUCKET}")
        else:
            logger.info(f"MinIO bucket exists: {settings.MINIO_BUCKET}")
    return _client


def upload_file(case_id: str, file_id: str, filename: str,
                file_bytes: bytes, content_type: str | None = None) -> str:
    """
    Upload a file to MinIO and return the S3 key.

    Storage layout: evidence/{case_id}/{file_id}/{original_filename}
    """
    client = get_minio()
    s3_key = f"evidence/{case_id}/{file_id}/{filename}"

    client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=s3_key,
        data=io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type or "application/octet-stream",
    )
    logger.info(f"Uploaded {s3_key} ({len(file_bytes)} bytes)")
    return s3_key


def download_file(s3_key: str) -> bytes:
    """Download a file from MinIO by its S3 key."""
    client = get_minio()
    try:
        response = client.get_object(settings.MINIO_BUCKET, s3_key)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        logger.error(f"Failed to download {s3_key}: {e}")
        raise


def get_presigned_url(s3_key: str, expires_hours: int = 1) -> str:
    """Generate a presigned URL for temporary file access."""
    from datetime import timedelta
    client = get_minio()
    return client.presigned_get_object(
        settings.MINIO_BUCKET,
        s3_key,
        expires=timedelta(hours=expires_hours),
    )


# Module-level shorthand
class _Storage:
    get_minio = staticmethod(get_minio)
    upload_file = staticmethod(upload_file)
    download_file = staticmethod(download_file)
    get_presigned_url = staticmethod(get_presigned_url)

storage = _Storage()
