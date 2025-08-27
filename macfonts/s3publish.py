import os
import hashlib
import asyncio
from typing import Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
from .models import PublishOptions, PublishResult
from .logging_config import logger

# Global S3 client with connection pooling
_s3_clients = {}

def _get_s3_client(region: Optional[str] = None) -> boto3.client:
    """Get or create S3 client with connection pooling."""
    region = region or 'us-east-1'
    
    if region not in _s3_clients:
        config = Config(
            region_name=region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50
        )
        _s3_clients[region] = boto3.client('s3', config=config)
        logger.debug(f"Created S3 client for region: {region}")
    
    return _s3_clients[region]

def _hash(path: str) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

async def _upload_with_retry(s3_client, local_path: str, bucket: str, key: str, extra_args: dict, max_retries: int = 3) -> None:
    """Upload file to S3 with retry logic."""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Uploading {local_path} to s3://{bucket}/{key} (attempt {attempt + 1})")
            await asyncio.to_thread(s3_client.upload_file, local_path, bucket, key, ExtraArgs=extra_args)
            logger.info(f"Successfully uploaded {local_path} to s3://{bucket}/{key}")
            return
        except (ClientError, BotoCoreError) as e:
            logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"All upload attempts failed for {local_path}")
                raise
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)

def _upload_woff2_sync(local_path: str, options: PublishOptions) -> PublishResult:
    """Synchronous version of upload_woff2 for internal use."""
    logger.debug(f"Starting WOFF2 upload: {local_path}")
    
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"File not found: {local_path}")
    
    s3 = _get_s3_client(options.region)
    sha = _hash(local_path)[:8]
    base = os.path.basename(local_path)
    key = f"{options.prefix.rstrip('/') + '/' if options.prefix else ''}{sha}-{base}"
    
    # Check if file already exists and overwrite is False
    if not options.overwrite:
        try:
            s3.head_object(Bucket=options.bucket, Key=key)
            logger.info(f"File already exists in S3: {key}")
            url = f"https://{options.bucket}.s3.amazonaws.com/{key}"
            css = f'@font-face{{font-family:"{os.path.splitext(base)[0]}";src:url("{url}") format("woff2");font-display:swap;}}'
            sample = f'<!doctype html><meta charset="utf-8"><style>{css}</style><p style="font-family:{os.path.splitext(base)[0]};font-size:48px">Sphinx of black quartz, judge my vow. 12345</p>'
            size = os.path.getsize(local_path)
            return PublishResult(woff2_url=url, css=css, size_bytes=size, sha256=_hash(local_path), sample_html=sample)
        except ClientError as e:
            if e.response['Error']['Code'] != '404':
                raise
    
    extra = {
        "ContentType": "font/woff2",
        "CacheControl": f"public, max-age={options.cache_seconds}, immutable",
    }
    
    if options.public:
        extra["ACL"] = "public-read"
    
    s3.upload_file(local_path, options.bucket, key, ExtraArgs=extra)
    
    url = f"https://{options.bucket}.s3.amazonaws.com/{key}"
    css = f'@font-face{{font-family:"{os.path.splitext(base)[0]}";src:url("{url}") format("woff2");font-display:swap;}}'
    sample = f'<!doctype html><meta charset="utf-8"><style>{css}</style><p style="font-family:{os.path.splitext(base)[0]};font-size:48px">Sphinx of black quartz, judge my vow. 12345</p>'
    size = os.path.getsize(local_path)
    
    logger.info(f"Successfully published WOFF2: {url}")
    return PublishResult(woff2_url=url, css=css, size_bytes=size, sha256=_hash(local_path), sample_html=sample)

async def upload_woff2(local_path: str, options: PublishOptions) -> PublishResult:
    """Upload WOFF2 file to S3 with retry logic and connection pooling."""
    return await asyncio.to_thread(_upload_woff2_sync, local_path, options)
