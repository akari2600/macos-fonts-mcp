from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Union

class FontAxis(BaseModel):
    tag: str
    name: str
    min: float
    max: float
    default: float

class FontFace(BaseModel):
    postScriptName: str
    family: str
    subfamily: Optional[str] = None
    path: str
    format: str
    index: Optional[int] = None
    isVariable: bool = False
    axes: List[FontAxis] = []
    version: Optional[str] = None
    glyphCount: Optional[int] = None
    tables: List[str] = []
    colorFormats: List[str] = []
    license: Optional[str] = None
    copyright: Optional[str] = None
    fsType: Optional[int] = None

class Overview(BaseModel):
    face: "FontFace"
    opentypeFeatures: Optional[Dict[str, List[str]]] = None
    samples: Optional[Dict[str, str]] = None

class ConvertOptions(BaseModel):
    subset_mode: Optional[str] = None   # 'text'|'unicodes'|'ranges'|None
    text: Optional[str] = None
    unicodes: Optional[List[str]] = None
    ranges: Optional[List[str]] = None
    drop_hints: bool = False
    retain_gsub_gpos: bool = True
    target_axes: Optional[Dict[str, float]] = None
    target_psname_suffix: Optional[str] = None

class PublishOptions(BaseModel):
    bucket: str
    prefix: Optional[str] = None
    region: Optional[str] = None
    public: bool = True
    cache_seconds: int = 31536000
    overwrite: bool = False

class PublishResult(BaseModel):
    woff2_url: str
    css: str
    size_bytes: int
    sha256: str
    sample_html: str

# Tool input validation models
class ListFamiliesRequest(BaseModel):
    pass  # No parameters needed

class FacesForFamilyRequest(BaseModel):
    family: str = Field(..., min_length=1, description="Font family name")

class FontOverviewRequest(BaseModel):
    postScriptName: str = Field(..., min_length=1, description="PostScript name of the font")

class PublishFontRequest(BaseModel):
    postScriptName: str = Field(..., min_length=1, description="PostScript name of the font")
    convert: Optional[ConvertOptions] = Field(default_factory=ConvertOptions)
    publish: PublishOptions = Field(..., description="S3 publishing options")
    
    @validator('publish')
    def validate_publish_options(cls, v):
        if not v.bucket:
            raise ValueError("S3 bucket is required")
        return v
