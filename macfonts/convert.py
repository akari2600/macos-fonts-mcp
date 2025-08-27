import os
from typing import Tuple
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.subset import Subsetter, Options, save_font
from .models import ConvertOptions
from .config import DEFAULT_OUT_DIR, ensure_dirs

def _sha256(path:str)->str:
    import hashlib
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def convert_to_woff2(path:str, options:ConvertOptions, out_name_hint:str)->Tuple[str,int,str]:
    ensure_dirs()
    font = TTFont(path)
    if options.target_axes and "fvar" in font:
        font = instantiateVariableFont(font, options.target_axes, inplace=False)

    if options.subset_mode:
        o = Options(); o.drop_hints = options.drop_hints; o.flavor = "woff2"
        subsetter = Subsetter(options=o)
        if options.subset_mode == "text" and options.text:
            subsetter.populate(text=options.text)
        elif options.subset_mode == "unicodes" and options.unicodes:
            subsetter.populate(unicodes=[int(u.replace("U+",""),16) for u in options.unicodes])
        elif options.subset_mode == "ranges" and options.ranges:
            cps = []
            for r in options.ranges:
                if "-" in r:
                    lo, hi = r.split("-")
                    lo = int(lo.replace("U+",""),16); hi = int(hi.replace("U+",""),16)
                    cps.extend(range(lo, hi+1))
                else:
                    cps.append(int(r.replace("U+",""),16))
            subsetter.populate(unicodes=cps)
        subsetter.subset(font)

    safe = out_name_hint.replace(" ", "").replace("/", "_")
    out_path = os.path.join(DEFAULT_OUT_DIR, f"{safe}.woff2")
    save_font(font, out_path, Options(flavor="woff2"))
    size = os.path.getsize(out_path)
    sha = _sha256(out_path)
    return out_path, size, sha
