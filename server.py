import json
import asyncio
import signal
from typing import Optional
from mcp.server.fastmcp import FastMCP

from macfonts.models import ConvertOptions, PublishOptions
from macfonts import discovery, metadata, convert, cssgen, s3publish
from macfonts.logging_config import logger, setup_logging
from macfonts.cache import start_cache_cleanup_task
from macfonts.cleanup import start_cleanup_task, cleanup_on_exit

# Create MCP server
mcp = FastMCP("macOS Fonts MCP Server")

# MCP Tools using FastMCP decorators

@mcp.tool()
async def list_families() -> str:
    """Return all macOS font families"""
    logger.info("Listing font families")
    families = await discovery.list_families()
    return json.dumps(families, indent=2)

@mcp.tool()
async def faces_for_family(family: str) -> str:
    """Return faces for a given font family"""
    logger.info(f"Getting faces for family: {family}")
    faces = await discovery.faces_for_family(family)
    enriched_faces = []
    for face in faces:
        enriched_face = await metadata.enrich_face(face)
        enriched_faces.append(enriched_face.model_dump())
    return json.dumps(enriched_faces, indent=2)

@mcp.tool()
async def font_overview(postScriptName: str) -> str:
    """Font Book–style overview of a font"""
    logger.info(f"Getting overview for font: {postScriptName}")
    face = await metadata.face_by_postscript(postScriptName)
    overview = await metadata.overview(face)
    return json.dumps(overview.model_dump(), indent=2)

@mcp.tool()
async def publish_font(
    postScriptName: str,
    bucket: str,
    convert: Optional[dict] = None,
    prefix: Optional[str] = None,
    region: Optional[str] = None,
    public: bool = True,
    cache_seconds: int = 31536000,
    overwrite: bool = False
) -> str:
    """Convert font to WOFF2 and upload to S3 in one step"""
    logger.info(f"Publishing font: {postScriptName} to S3 bucket: {bucket}")
    
    # Create options from parameters
    convert_options = ConvertOptions(**(convert or {}))
    publish_options = PublishOptions(
        bucket=bucket,
        prefix=prefix,
        region=region,
        public=public,
        cache_seconds=cache_seconds,
        overwrite=overwrite
    )
    
    # Execute the publishing pipeline
    face = await metadata.face_by_postscript(postScriptName)
    out_path, size, sha = await convert.convert_to_woff2(
        face.path, convert_options, postScriptName
    )
    result = await s3publish.upload_woff2(out_path, publish_options)
    
    if not result.css:
        result.css = cssgen.simple_css(face.family or postScriptName, result.woff2_url)
    
    return json.dumps(result.model_dump(), indent=2)

# MCP Resource
@mcp.resource("font://families")
async def get_font_families() -> str:
    """All font families resource"""
    families = await discovery.list_families()
    return json.dumps(families, indent=2)

if __name__ == "__main__":
    # Setup basic logging
    setup_logging(level="INFO")
    logger.info("Starting macOS Fonts MCP Server v0.2")
    
    try:
        # FastMCP handles its own event loop
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        pass
