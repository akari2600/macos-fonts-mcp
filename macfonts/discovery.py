from typing import List, Dict, Optional
import CoreText
import os
import asyncio
from .models import FontFace
from .cache import cached
from .logging_config import logger

def _fmt_from_path(p: str) -> str:
    ext = os.path.splitext(p)[1].lower()
    return {".ttf":"ttf", ".otf":"otf", ".ttc":"ttc", ".dfont":"dfont"}.get(ext, ext.strip("."))

# Global cache for PostScript name lookups
_postscript_index: Optional[Dict[str, FontFace]] = None

def _build_postscript_index() -> Dict[str, FontFace]:
    """Build an index of PostScript names to FontFace objects for fast lookup."""
    global _postscript_index
    if _postscript_index is not None:
        return _postscript_index
    
    logger.info("Building PostScript name index...")
    index = {}
    families = _list_families_sync()
    
    for family in families:
        try:
            faces = _faces_for_family_sync(family)
            for face in faces:
                index[face.postScriptName] = face
        except Exception as e:
            logger.warning(f"Error processing family {family}: {e}")
    
    _postscript_index = index
    logger.info(f"Built PostScript index with {len(index)} entries")
    return index

def _list_families_sync() -> List[str]:
    """Synchronous version for internal use."""
    fams = CoreText.CTFontManagerCopyAvailableFontFamilyNames()
    return [str(x) for x in fams]

@cached(ttl=600)  # Cache for 10 minutes
async def list_families() -> List[str]:
    """List all available font families on the system."""
    logger.debug("Listing font families")
    return await asyncio.to_thread(_list_families_sync)

def _faces_for_family_sync(family: str) -> List[FontFace]:
    """Synchronous version for internal use."""
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

@cached(ttl=600)  # Cache for 10 minutes
async def faces_for_family(family: str) -> List[FontFace]:
    """Get all font faces for a given family."""
    logger.debug(f"Getting faces for family: {family}")
    return await asyncio.to_thread(_faces_for_family_sync, family)

async def face_by_postscript(postscript_name: str) -> Optional[FontFace]:
    """Fast lookup of font face by PostScript name using index."""
    logger.debug(f"Looking up font by PostScript name: {postscript_name}")
    
    # Build index if needed (done in thread to avoid blocking)
    index = await asyncio.to_thread(_build_postscript_index)
    
    face = index.get(postscript_name)
    if not face:
        logger.warning(f"PostScript name not found: {postscript_name}")
        return None
    
    return face

async def refresh_postscript_index() -> None:
    """Force refresh of the PostScript name index."""
    global _postscript_index
    _postscript_index = None
    await asyncio.to_thread(_build_postscript_index)
    logger.info("PostScript name index refreshed")
