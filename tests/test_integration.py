import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock

from macfonts.models import (
    ListFamiliesRequest, FacesForFamilyRequest, 
    FontOverviewRequest, PublishFontRequest,
    ConvertOptions, PublishOptions
)
from server import validate_and_parse_args, handle_tool_call
from mcp.types import CallToolRequest

class TestInputValidation:
    @pytest.mark.asyncio
    async def test_list_families_validation(self):
        """Test list_families input validation."""
        # Valid empty args
        result = await validate_and_parse_args("list_families", {})
        assert isinstance(result, ListFamiliesRequest)
        
        # Extra args should be ignored
        result = await validate_and_parse_args("list_families", {"extra": "ignored"})
        assert isinstance(result, ListFamiliesRequest)

    @pytest.mark.asyncio
    async def test_faces_for_family_validation(self):
        """Test faces_for_family input validation."""
        # Valid args
        result = await validate_and_parse_args("faces_for_family", {"family": "Arial"})
        assert isinstance(result, FacesForFamilyRequest)
        assert result.family == "Arial"
        
        # Missing family should raise error
        with pytest.raises(ValueError):
            await validate_and_parse_args("faces_for_family", {})
        
        # Empty family should raise error
        with pytest.raises(ValueError):
            await validate_and_parse_args("faces_for_family", {"family": ""})

    @pytest.mark.asyncio
    async def test_font_overview_validation(self):
        """Test font_overview input validation."""
        # Valid args
        result = await validate_and_parse_args("font_overview", {"postScriptName": "Arial-Regular"})
        assert isinstance(result, FontOverviewRequest)
        assert result.postScriptName == "Arial-Regular"
        
        # Missing postScriptName should raise error
        with pytest.raises(ValueError):
            await validate_and_parse_args("font_overview", {})

    @pytest.mark.asyncio
    async def test_publish_font_validation(self):
        """Test publish_font input validation."""
        # Valid minimal args
        args = {
            "postScriptName": "Arial-Regular",
            "publish": {"bucket": "test-bucket"}
        }
        result = await validate_and_parse_args("publish_font", args)
        assert isinstance(result, PublishFontRequest)
        assert result.postScriptName == "Arial-Regular"
        assert result.publish.bucket == "test-bucket"
        
        # Missing bucket should raise error
        with pytest.raises(ValueError):
            await validate_and_parse_args("publish_font", {
                "postScriptName": "Arial-Regular",
                "publish": {}
            })

class TestToolCallHandling:
    @pytest.mark.asyncio
    async def test_list_families_tool_call(self):
        """Test list_families tool call handling."""
        with patch('macfonts.discovery.list_families') as mock_list:
            mock_list.return_value = ["Arial", "Helvetica"]
            
            req = CallToolRequest(name="list_families", arguments={})
            response = await handle_tool_call(req, "test-id")
            
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "test-id"
            assert "result" in response
            
            content = json.loads(response["result"]["content"][0]["text"])
            assert content == ["Arial", "Helvetica"]

    @pytest.mark.asyncio
    async def test_faces_for_family_tool_call(self):
        """Test faces_for_family tool call handling."""
        with patch('macfonts.discovery.faces_for_family') as mock_faces, \
             patch('macfonts.metadata.enrich_face') as mock_enrich:
            
            from macfonts.models import FontFace
            mock_face = FontFace(
                postScriptName="Arial-Regular",
                family="Arial",
                path="/test/path",
                format="ttf"
            )
            mock_faces.return_value = [mock_face]
            mock_enrich.return_value = mock_face
            
            req = CallToolRequest(name="faces_for_family", arguments={"family": "Arial"})
            response = await handle_tool_call(req, "test-id")
            
            assert response["jsonrpc"] == "2.0"
            assert "result" in response

    @pytest.mark.asyncio
    async def test_font_overview_tool_call(self):
        """Test font_overview tool call handling."""
        with patch('macfonts.metadata.face_by_postscript') as mock_face, \
             patch('macfonts.metadata.overview') as mock_overview:
            
            from macfonts.models import FontFace, Overview
            mock_face_obj = FontFace(
                postScriptName="Arial-Regular",
                family="Arial",
                path="/test/path",
                format="ttf"
            )
            mock_overview_obj = Overview(face=mock_face_obj)
            
            mock_face.return_value = mock_face_obj
            mock_overview.return_value = mock_overview_obj
            
            req = CallToolRequest(name="font_overview", arguments={"postScriptName": "Arial-Regular"})
            response = await handle_tool_call(req, "test-id")
            
            assert response["jsonrpc"] == "2.0"
            assert "result" in response

    @pytest.mark.asyncio
    async def test_publish_font_tool_call(self):
        """Test publish_font tool call handling."""
        with patch('macfonts.metadata.face_by_postscript') as mock_face, \
             patch('macfonts.convert.convert_to_woff2') as mock_convert, \
             patch('macfonts.s3publish.upload_woff2') as mock_upload, \
             patch('macfonts.cssgen.simple_css') as mock_css:
            
            from macfonts.models import FontFace, PublishResult
            
            mock_face_obj = FontFace(
                postScriptName="Arial-Regular",
                family="Arial",
                path="/test/path",
                format="ttf"
            )
            mock_result = PublishResult(
                woff2_url="https://test-bucket.s3.amazonaws.com/font.woff2",
                css="@font-face{...}",
                size_bytes=1024,
                sha256="abcd1234",
                sample_html="<html>...</html>"
            )
            
            mock_face.return_value = mock_face_obj
            mock_convert.return_value = ("/tmp/font.woff2", 1024, "abcd1234")
            mock_upload.return_value = mock_result
            mock_css.return_value = "@font-face{...}"
            
            req = CallToolRequest(
                name="publish_font",
                arguments={
                    "postScriptName": "Arial-Regular",
                    "publish": {"bucket": "test-bucket"}
                }
            )
            response = await handle_tool_call(req, "test-id")
            
            assert response["jsonrpc"] == "2.0"
            assert "result" in response

    @pytest.mark.asyncio
    async def test_invalid_tool_call(self):
        """Test handling of invalid tool calls."""
        req = CallToolRequest(name="nonexistent_tool", arguments={})
        response = await handle_tool_call(req, "test-id")
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-id"
        assert "error" in response
        assert response["error"]["code"] == -32000

    @pytest.mark.asyncio
    async def test_tool_call_error_handling(self):
        """Test error handling in tool calls."""
        with patch('macfonts.discovery.list_families') as mock_list:
            mock_list.side_effect = Exception("Test error")
            
            req = CallToolRequest(name="list_families", arguments={})
            response = await handle_tool_call(req, "test-id")
            
            assert response["jsonrpc"] == "2.0"
            assert "error" in response
            assert "Test error" in response["error"]["message"]

class TestEndToEndWorkflow:
    @pytest.mark.asyncio
    async def test_complete_font_workflow(self):
        """Test complete workflow from discovery to publishing."""
        with patch('macfonts.discovery.list_families') as mock_families, \
             patch('macfonts.discovery.faces_for_family') as mock_faces, \
             patch('macfonts.metadata.enrich_face') as mock_enrich, \
             patch('macfonts.metadata.face_by_postscript') as mock_face_lookup, \
             patch('macfonts.convert.convert_to_woff2') as mock_convert, \
             patch('macfonts.s3publish.upload_woff2') as mock_upload:
            
            from macfonts.models import FontFace, PublishResult
            
            # Setup mocks
            mock_families.return_value = ["Arial", "Helvetica"]
            
            mock_face = FontFace(
                postScriptName="Arial-Regular",
                family="Arial",
                path="/System/Library/Fonts/Arial.ttf",
                format="ttf"
            )
            
            mock_faces.return_value = [mock_face]
            mock_enrich.return_value = mock_face
            mock_face_lookup.return_value = mock_face
            mock_convert.return_value = ("/tmp/Arial-Regular.woff2", 2048, "sha256hash")
            mock_upload.return_value = PublishResult(
                woff2_url="https://bucket.s3.amazonaws.com/Arial-Regular.woff2",
                css="@font-face{font-family:'Arial';src:url('...');}",
                size_bytes=2048,
                sha256="sha256hash",
                sample_html="<html>Sample</html>"
            )
            
            # Test workflow
            # 1. List families
            families_req = CallToolRequest(name="list_families", arguments={})
            families_response = await handle_tool_call(families_req, "1")
            assert "result" in families_response
            
            # 2. Get faces for family
            faces_req = CallToolRequest(name="faces_for_family", arguments={"family": "Arial"})
            faces_response = await handle_tool_call(faces_req, "2")
            assert "result" in faces_response
            
            # 3. Get font overview
            overview_req = CallToolRequest(name="font_overview", arguments={"postScriptName": "Arial-Regular"})
            overview_response = await handle_tool_call(overview_req, "3")
            assert "result" in overview_response
            
            # 4. Publish font
            publish_req = CallToolRequest(
                name="publish_font",
                arguments={
                    "postScriptName": "Arial-Regular",
                    "convert": {"subset_mode": "text", "text": "Hello World"},
                    "publish": {"bucket": "test-bucket", "prefix": "fonts/"}
                }
            )
            publish_response = await handle_tool_call(publish_req, "4")
            assert "result" in publish_response
            
            # Verify the result contains expected data
            result_content = json.loads(publish_response["result"]["content"][0]["text"])
            assert result_content["woff2_url"] == "https://bucket.s3.amazonaws.com/Arial-Regular.woff2"
            assert result_content["size_bytes"] == 2048