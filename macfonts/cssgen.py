def simple_css(font_family: str, url: str) -> str:
    return f'''@font-face {{
  font-family: "{font_family}";
  src: url("{url}") format("woff2");
  font-display: swap;
}}'''
