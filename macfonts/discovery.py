from typing import List
import CoreText
import os
from .models import FontFace

def _fmt_from_path(p: str) -> str:
    ext = os.path.splitext(p)[1].lower()
    return {".ttf":"ttf", ".otf":"otf", ".ttc":"ttc", ".dfont":"dfont"}.get(ext, ext.strip("."))

def list_families() -> List[str]:
    fams = CoreText.CTFontManagerCopyAvailableFontFamilyNames()
    return [str(x) for x in fams]

def faces_for_family(family: str) -> List[FontFace]:
    desc = CoreText.CTFontDescriptorCreateWithAttributes({CoreText.kCTFontFamilyNameAttribute: family})
    coll = CoreText.CTFontCollectionCreateWithFontDescriptors([desc], None)
    matched = CoreText.CTFontCollectionCreateMatchingFontDescriptors(coll) or []
    faces: List[FontFace] = []
    for d in matched:
        ps  = CoreText.CTFontDescriptorCopyAttribute(d, CoreText.kCTFontNameAttribute)
        fam = CoreText.CTFontDescriptorCopyAttribute(d, CoreText.kCTFontFamilyNameAttribute)
        sub = CoreText.CTFontDescriptorCopyAttribute(d, CoreText.kCTFontStyleNameAttribute)
        url = CoreText.CTFontDescriptorCopyAttribute(d, CoreText.kCTFontURLAttribute)
        path = url.path() if url else None
        if not path:
            continue
        fmt = _fmt_from_path(path)
        faces.append(FontFace(
            postScriptName=str(ps), family=str(fam), subfamily=str(sub) if sub else None,
            path=path, format=fmt
        ))
    return faces
