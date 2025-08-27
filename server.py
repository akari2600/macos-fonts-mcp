import sys
import json
import traceback
import asyncio
import signal
from typing import Dict, Any
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource, ResourceContents, CallToolRequest
from pydantic import ValidationError

from macfonts.models import (
    ConvertOptions, PublishOptions, 
    ListFamiliesRequest, FacesForFamilyRequest, 
    FontOverviewRequest, PublishFontRequest
)
from macfonts import discovery, metadata, convert, cssgen, s3publish
from macfonts.logging_config import logger, setup_logging
from macfonts.cache import start_cache_cleanup_task
from macfonts.cleanup import start_cleanup_task, cleanup_on_exit

async def validate_and_parse_args(tool_name: str, args: Dict[str, Any]) -> Any:
    """Validate tool arguments using Pydantic models."""
    try:
        if tool_name == "list_families":
            return ListFamiliesRequest.model_validate(args)
        elif tool_name == "faces_for_family":
            return FacesForFamilyRequest.model_validate(args)
        elif tool_name == "font_overview":
            return FontOverviewRequest.model_validate(args)
        elif tool_name == "publish_font":
            return PublishFontRequest.model_validate(args)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    except ValidationError as e:
        logger.error(f"Validation error for {tool_name}: {e}")
        raise ValueError(f"Invalid arguments for {tool_name}: {e}")

async def handle_tool_call(req: CallToolRequest, msg_id: str) -> Dict[str, Any]:
    """Handle a tool call with proper validation and error handling."""
    tool_name = req.name
    args = req.arguments or {}
    
    logger.info(f"Handling tool call: {tool_name}")
    
    try:
        # Validate arguments
        validated_args = await validate_and_parse_args(tool_name, args)
        
        if tool_name == "list_families":
            families = await discovery.list_families()
            content = json.dumps(families)
            
        elif tool_name == "faces_for_family":
            faces = await discovery.faces_for_family(validated_args.family)
            enriched_faces = []
            for face in faces:
                enriched_face = await metadata.enrich_face(face)
                enriched_faces.append(enriched_face.model_dump())
            content = json.dumps(enriched_faces, indent=2)
            
        elif tool_name == "font_overview":
            face = await metadata.face_by_postscript(validated_args.postScriptName)
            overview = await metadata.overview(face)
            content = json.dumps(overview.model_dump(), indent=2)
            
        elif tool_name == "publish_font":
            face = await metadata.face_by_postscript(validated_args.postScriptName)
            out_path, size, sha = await convert.convert_to_woff2(
                face.path, validated_args.convert, validated_args.postScriptName
            )
            result = await s3publish.upload_woff2(out_path, validated_args.publish)
            
            if not result.css:
                result.css = cssgen.simple_css(face.family or validated_args.postScriptName, result.woff2_url)
            
            content = json.dumps(result.model_dump(), indent=2)
            
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        logger.info(f"Successfully handled tool call: {tool_name}")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [TextContent(type="text", text=content).model_dump()]
            }
        }
        
    except Exception as e:
        logger.error(f"Error handling tool call {tool_name}: {e}")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32000,
                "message": str(e),
                "data": traceback.format_exc()
            }
        }

async def main():
    # Setup logging
    setup_logging(level="INFO")
    logger.info("Starting macOS Fonts MCP Server v0.2")
    
    # Start background tasks
    await start_cache_cleanup_task()
    await start_cleanup_task()
    
    # Setup graceful shutdown
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(cleanup_on_exit())
    
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    
    async with stdio_server("macos-fonts-mcp") as (read, write):
        tools = [
            Tool(name="list_families", description="Return macOS font families"),
            Tool(name="faces_for_family", description="Return faces for a given family. Input: {\"family\":\"...\"}"),
            Tool(name="font_overview", description="Font Book–style overview. Input: {\"postScriptName\":\"...\"}"),
            Tool(name="publish_font", description="ONE-STEP: Convert to WOFF2 and upload to S3. Input: {postScriptName, convert, publish}")
        ]
        resources = [
            Resource(uri="font://families", name="All font families")
        ]

        logger.info("Sending tools and resources to client")
        await write({"jsonrpc":"2.0","id":"tools","result": {"tools":[t.model_dump() for t in tools]}})
        await write({"jsonrpc":"2.0","id":"resources","result": {"resources":[r.model_dump() for r in resources]}})

        logger.info("MCP server ready, listening for messages...")
        
        async for msg in read:
            try:
                if "method" not in msg:
                    logger.debug("Received message without method, skipping")
                    continue

                method = msg["method"]
                msg_id = msg.get("id", "unknown")
                
                logger.debug(f"Received message: {method}")

                if method == "tools/call":
                    req = CallToolRequest.model_validate(msg["params"])
                    response = await handle_tool_call(req, msg_id)
                    await write(response)

                elif method == "resources/list":
                    logger.debug("Handling resources/list")
                    await write({
                        "jsonrpc":"2.0",
                        "id": msg_id,
                        "result": {"resources":[{"uri":"font://families","name":"All font families"}]}
                    })

                elif method == "resources/read":
                    logger.debug("Handling resources/read")
                    uri = msg["params"]["uri"]
                    if uri == "font://families":
                        families = await discovery.list_families()
                        body = json.dumps(families, indent=2)
                        res = ResourceContents(mimeType="application/json", text=body)
                        await write({
                            "jsonrpc":"2.0",
                            "id": msg_id,
                            "result": {"contents":[res.model_dump()]}
                        })
                    else:
                        await write({
                            "jsonrpc":"2.0",
                            "id": msg_id,
                            "error": {"code":-32602,"message":f"Unknown resource {uri}"}
                        })

                else:
                    logger.warning(f"Unknown method: {method}")
                    await write({
                        "jsonrpc":"2.0",
                        "id": msg_id,
                        "error": {"code":-32601,"message":"Method not found"}
                    })

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                tb = traceback.format_exc()
                await write({
                    "jsonrpc":"2.0",
                    "id": msg.get("id", "unknown"),
                    "error": {"code":-32000,"message":str(e),"data":tb}
                })

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
