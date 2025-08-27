import sys, json, traceback, asyncio
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource, ResourceContents, CallToolRequest

from macfonts.models import ConvertOptions, PublishOptions
from macfonts import discovery, metadata, convert, cssgen, s3publish

async def main():
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

        await write({"jsonrpc":"2.0","id":"tools","result": {"tools":[t.model_dump() for t in tools]}})
        await write({"jsonrpc":"2.0","id":"resources","result": {"resources":[r.model_dump() for r in resources]}})

        async for msg in read:
            try:
                if "method" not in msg:
                    continue

                if msg["method"] == "tools/call":
                    req = CallToolRequest.model_validate(msg["params"])
                    name = req.name
                    args = req.arguments or {}

                    if name == "list_families":
                        fams = discovery.list_families()
                        await write({"jsonrpc":"2.0","id":msg["id"],"result":{"content":[TextContent(type="text", text=json.dumps(fams)).model_dump()]}})

                    elif name == "faces_for_family":
                        fam = args.get("family")
                        faces = discovery.faces_for_family(fam)
                        faces = [metadata.enrich_face(f) for f in faces]
                        await write({"jsonrpc":"2.0","id":msg["id"],"result":{"content":[TextContent(type="text", text=json.dumps([f.model_dump() for f in faces], indent=2)).model_dump()]}})

                    elif name == "font_overview":
                        ps = args.get("postScriptName")
                        face = metadata.face_by_postscript(ps)
                        ov = metadata.overview(face)
                        await write({"jsonrpc":"2.0","id":msg["id"],"result":{"content":[TextContent(type="text", text=json.dumps(ov.model_dump(), indent=2)).model_dump()]}})

                    elif name == "publish_font":
                        ps = args.get("postScriptName")
                        convert_opts = ConvertOptions(**(args.get("convert") or {}))
                        publish_opts = PublishOptions(**(args.get("publish") or {}))
                        face = metadata.face_by_postscript(ps)
                        out_path, size, sha = convert.convert_to_woff2(face.path, convert_opts, out_name_hint=ps)
                        res = s3publish.upload_woff2(out_path, publish_opts)
                        if not res.css:
                            res.css = cssgen.simple_css(face.family or ps, res.woff2_url)
                        await write({"jsonrpc":"2.0","id":msg["id"],"result":{"content":[TextContent(type="text", text=json.dumps(res.model_dump(), indent=2)).model_dump()]}})

                    else:
                        await write({"jsonrpc":"2.0","id":msg["id"],"error":{"code":-32601,"message":f"Unknown tool {name}"}})

                elif msg["method"] == "resources/list":
                    await write({"jsonrpc":"2.0","id":msg["id"],"result":{"resources":[{"uri":"font://families","name":"All font families"}]}})

                elif msg["method"] == "resources/read":
                    uri = msg["params"]["uri"]
                    if uri == "font://families":
                        fams = discovery.list_families()
                        body = json.dumps(fams, indent=2)
                        res = ResourceContents(mimeType="application/json", text=body)
                        await write({"jsonrpc":"2.0","id":msg["id"],"result":{"contents":[res.model_dump()]}})
                    else:
                        await write({"jsonrpc":"2.0","id":msg["id"],"error":{"code":-32602,"message":f"Unknown resource {uri}"}})

                else:
                    await write({"jsonrpc":"2.0","id":msg.get("id"),"error":{"code":-32601,"message":"Method not found"}})

            except Exception as e:
                tb = traceback.format_exc()
                await write({"jsonrpc":"2.0","id":msg.get("id"),"error":{"code":-32000,"message":str(e),"data":tb}})

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
