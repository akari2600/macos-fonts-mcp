from fontTools.ttLib import TTFont
from .models import FontFace, FontAxis, Overview
from . import discovery

COLOR_TABLES = {"COLR":"COLR","CPAL":"CPAL","sbix":"sbix","CBDT":"CBDT","CBLC":"CBLC","SVG ":"SVG "}

def enrich_face(face: FontFace) -> FontFace:
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
            axes.append(FontAxis(tag=a.axisTag, name=str(a.getAxisNameID()), min=a.minValue, max=a.maxValue, default=a.defaultValue))
        face.axes = axes
    face.tables = list(tt.keys())
    face.colorFormats = [k for k in COLOR_TABLES if k in tt]
    tt.close()
    return face

def face_by_postscript(psname: str) -> FontFace:
    for fam in discovery.list_families():
        for f in discovery.faces_for_family(fam):
            if f.postScriptName == psname:
                return enrich_face(f)
    raise ValueError(f"PostScript name not found: {psname}")

def overview(face: FontFace) -> Overview:
    face = enrich_face(face)
    return Overview(face=face, opentypeFeatures=None, samples=None)
