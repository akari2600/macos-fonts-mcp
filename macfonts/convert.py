import os
import asyncio
import tempfile
from typing import Tuple
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.subset import Subsetter, Options, save_font
from .models import ConvertOptions
from .config import DEFAULT_OUT_DIR, ensure_dirs
from .logging_config import logger

def _sha256(path: str) -> str:
    """Calculate SHA256 hash of a file."""
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def _convert_to_woff2_sync(path: str, options: ConvertOptions, out_name_hint: str) -> Tuple[str, int, str]:
    """Synchronous version of convert_to_woff2 for internal use."""
    logger.debug(f"Converting font to WOFF2: {path}")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Font file not found: {path}")
    
    ensure_dirs()
    
    font = None
    try:
        font = TTFont(path)
        logger.debug(f"Loaded font: {path}")
        
        # Handle variable font instancing
        if options.target_axes and "fvar" in font:
            logger.debug(f"Instancing variable font with axes: {options.target_axes}")
            font = instantiateVariableFont(font, options.target_axes, inplace=False)

        # Handle subsetting
        if options.subset_mode:
            logger.debug(f"Subsetting font with mode: {options.subset_mode}")
            o = Options()
            o.drop_hints = options.drop_hints
            o.retain_gids = not options.retain_gsub_gpos  # Optimize glyph IDs if not retaining layout
            o.flavor = "woff2"
            
            subsetter = Subsetter(options=o)
            
            if options.subset_mode == "text" and options.text:
                subsetter.populate(text=options.text)
                logger.debug(f"Subsetting by text: {options.text[:50]}...")
                
            elif options.subset_mode == "unicodes" and options.unicodes:
                unicodes = [int(u.replace("U+", ""), 16) for u in options.unicodes]
                subsetter.populate(unicodes=unicodes)
                logger.debug(f"Subsetting by unicodes: {len(unicodes)} codepoints")
                
            elif options.subset_mode == "ranges" and options.ranges:
                cps = []
                for r in options.ranges:
                    if "-" in r:
                        lo, hi = r.split("-")
                        lo = int(lo.replace("U+", ""), 16)
                        hi = int(hi.replace("U+", ""), 16)
                        cps.extend(range(lo, hi + 1))
                    else:
                        cps.append(int(r.replace("U+", ""), 16))
                subsetter.populate(unicodes=cps)
                logger.debug(f"Subsetting by ranges: {len(cps)} codepoints")
            
            subsetter.subset(font)

        # Generate output path
        safe = out_name_hint.replace(" ", "").replace("/", "_").replace("\\", "_")
        if options.target_psname_suffix:
            safe += f"-{options.target_psname_suffix}"
        
        out_path = os.path.join(DEFAULT_OUT_DIR, f"{safe}.woff2")
        
        # Ensure we don't overwrite existing files
        counter = 1
        base_path = out_path
        while os.path.exists(out_path):
            name, ext = os.path.splitext(base_path)
            out_path = f"{name}-{counter}{ext}"
            counter += 1

        # Save font
        save_font(font, out_path, Options(flavor="woff2"))
        size = os.path.getsize(out_path)
        sha = _sha256(out_path)
        
        logger.info(f"Successfully converted to WOFF2: {out_path} ({size} bytes, SHA256: {sha[:16]}...)")
        return out_path, size, sha
        
    except Exception as e:
        logger.error(f"Error converting font {path}: {e}")
        raise
    finally:
        # Clean up font object to free memory
        if font:
            try:
                font.close()
            except:
                pass

async def convert_to_woff2(path: str, options: ConvertOptions, out_name_hint: str) -> Tuple[str, int, str]:
    """Convert font to WOFF2 format with async support."""
    return await asyncio.to_thread(_convert_to_woff2_sync, path, options, out_name_hint)
