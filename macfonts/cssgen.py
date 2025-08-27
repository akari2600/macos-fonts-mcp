import re
from typing import Optional
from .logging_config import logger

def _sanitize_font_family(family: str) -> str:
    """Sanitize font family name for CSS."""
    if not family:
        return "Unknown"
    
    # Remove potentially problematic characters
    sanitized = re.sub(r'[^\w\s-]', '', family)
    sanitized = sanitized.strip()
    
    if not sanitized:
        return "Unknown"
    
    return sanitized

def _sanitize_url(url: str) -> str:
    """Basic URL validation and sanitization."""
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Basic URL validation
    if not (url.startswith('http://') or url.startswith('https://')):
        raise ValueError("URL must start with http:// or https://")
    
    # Remove any quotes that might break CSS
    return url.replace('"', '%22').replace("'", '%27')

def simple_css(font_family: str, url: str, font_weight: Optional[str] = None, font_style: Optional[str] = None) -> str:
    """Generate CSS @font-face rule with proper sanitization and error handling."""
    try:
        logger.debug(f"Generating CSS for font: {font_family}")
        
        # Sanitize inputs
        clean_family = _sanitize_font_family(font_family)
        clean_url = _sanitize_url(url)
        
        # Build CSS rule
        css_parts = [
            f'  font-family: "{clean_family}";',
            f'  src: url("{clean_url}") format("woff2");',
            '  font-display: swap;'
        ]
        
        # Add optional properties
        if font_weight:
            css_parts.insert(-1, f'  font-weight: {font_weight};')
        
        if font_style:
            css_parts.insert(-1, f'  font-style: {font_style};')
        
        css = '@font-face {\n' + '\n'.join(css_parts) + '\n}'
        
        logger.debug(f"Generated CSS: {css}")
        return css
        
    except Exception as e:
        logger.error(f"Error generating CSS for {font_family}: {e}")
        # Return a fallback CSS rule
        return f'@font-face {{ font-family: "Unknown"; src: url("data:,") format("woff2"); font-display: swap; }}'

def generate_font_stack_css(fonts: list, fallback_fonts: Optional[list] = None) -> str:
    """Generate CSS with multiple font-face rules and a font stack."""
    if not fonts:
        raise ValueError("At least one font must be provided")
    
    fallback_fonts = fallback_fonts or ['system-ui', 'sans-serif']
    
    try:
        css_rules = []
        font_families = []
        
        for font_info in fonts:
            if isinstance(font_info, dict):
                family = font_info.get('family', 'Unknown')
                url = font_info.get('url', '')
                weight = font_info.get('weight')
                style = font_info.get('style')
            else:
                # Assume it's a simple family name
                family = str(font_info)
                url = ''
                weight = None
                style = None
            
            if url:
                css_rule = simple_css(family, url, weight, style)
                css_rules.append(css_rule)
            
            font_families.append(f'"{_sanitize_font_family(family)}"')
        
        # Add fallback fonts
        font_families.extend(fallback_fonts)
        
        # Generate complete CSS
        font_stack = ', '.join(font_families)
        complete_css = '\n\n'.join(css_rules)
        
        if css_rules:
            complete_css += f'\n\n/* Font stack: {font_stack} */'
        
        return complete_css
        
    except Exception as e:
        logger.error(f"Error generating font stack CSS: {e}")
        return '/* Error generating font CSS */'
