import asyncio
from fontTools.ttLib import TTFont
from .models import FontFace, FontAxis, Overview
from . import discovery
from .cache import cached
from .logging_config import logger

COLOR_TABLES = {"COLR":"COLR","CPAL":"CPAL","sbix":"sbix","CBDT":"CBDT","CBLC":"CBLC","SVG ":"SVG "}

def _enrich_face_sync(face: FontFace) -> FontFace:
    """Synchronous version of enrich_face for internal use."""
    logger.debug(f"Enriching font face: {face.postScriptName}")
    
    try:
        tt = TTFont(face.path, fontNumber=face.index or 0, lazy=True)
        name = tt["name"]
        
        def _get_name(nid):
            rec = name.getName(nid, 3, 1) or name.getName(nid, 1, 0)
            return str(rec) if rec else None
        
        face.version = _get_name(5)
        face.license = _get_name(13)
        face.copyright = _get_name(0)
        
        if "OS/2" in tt:
            face.fsType = getattr(tt["OS/2"], "fsType", None)
        
        face.glyphCount = tt["maxp"].numGlyphs if "maxp" in tt else None
        
        if "fvar" in tt:
            face.isVariable = True
            axes = []
            for a in tt["fvar"].axes:
                axes.append(FontAxis(
                    tag=a.axisTag, 
                    name=str(a.getAxisNameID()), 
                    min=a.minValue, 
                    max=a.maxValue, 
                    default=a.defaultValue
                ))
            face.axes = axes
        
        face.tables = list(tt.keys())
        face.colorFormats = [k for k in COLOR_TABLES if k in tt]
        
        tt.close()
        logger.debug(f"Successfully enriched font face: {face.postScriptName}")
        return face
        
    except Exception as e:
        logger.error(f"Error enriching font face {face.postScriptName}: {e}")
        raise

@cached(ttl=1800)  # Cache for 30 minutes
async def enrich_face(face: FontFace) -> FontFace:
    """Enrich a FontFace with detailed metadata."""
    return await asyncio.to_thread(_enrich_face_sync, face)

async def face_by_postscript(psname: str) -> FontFace:
    """Get font face by PostScript name with fast lookup."""
    face = await discovery.face_by_postscript(psname)
    if not face:
        raise ValueError(f"PostScript name not found: {psname}")
    return await enrich_face(face)

async def overview(face: FontFace) -> Overview:
    """Generate overview for a font face."""
    logger.debug(f"Generating overview for: {face.postScriptName}")
    enriched_face = await enrich_face(face)
    return Overview(face=enriched_face, opentypeFeatures=None, samples=None)
