import os, hashlib, boto3
from .models import PublishOptions, PublishResult

def _hash(path:str)->str:
    h = hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def upload_woff2(localPath: str, options: PublishOptions) -> PublishResult:
    s3 = boto3.client("s3", region_name=options.region)
    sha = _hash(localPath)[:8]
    base = os.path.basename(localPath)
    key = f"{options.prefix.rstrip('/') + '/' if options.prefix else ''}{sha}-{base}"
    extra = {
        "ContentType": "font/woff2",
        "CacheControl": f"public, max-age={options.cache_seconds}, immutable",
    }
    s3.upload_file(localPath, options.bucket, key, ExtraArgs=extra)
    url = f"https://{options.bucket}.s3.amazonaws.com/{key}"
    css = f'@font-face{{font-family:"{os.path.splitext(base)[0]}";src:url("{url}") format("woff2");font-display:swap;}}'
    sample = f'<!doctype html><meta charset="utf-8"><style>{css}</style><p style="font-family:{os.path.splitext(base)[0]};font-size:48px">Sphinx of black quartz, judge my vow. 12345</p>'
    size = os.path.getsize(localPath)
    return PublishResult(woff2_url=url, css=css, size_bytes=size, sha256=_hash(localPath), sample_html=sample)
