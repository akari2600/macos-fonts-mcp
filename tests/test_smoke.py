import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock

from macfonts import discovery, metadata, convert, s3publish
from macfonts.models import FontFace, ConvertOptions, PublishOptions
from macfonts.cache import cache

@pytest.fixture
def mock_font_face():
    return FontFace(
        postScriptName="TestFont-Regular",
        family="Test Font",
        subfamily="Regular",
        path="/System/Library/Fonts/TestFont.ttf",
        format="ttf"
    )

@pytest.fixture
def sample_convert_options():
    return ConvertOptions(
        subset_mode="text",
        text="Hello World",
        drop_hints=True
    )

@pytest.fixture
def sample_publish_options():
    return PublishOptions(
        bucket="test-bucket",
        prefix="fonts/",
        region="us-east-1"
    )

class TestDiscovery:
    @pytest.mark.asyncio
    async def test_list_families(self):
        """Test that list_families returns a list of strings."""
        with patch('macfonts.discovery.CoreText') as mock_ct:
            mock_ct.CTFontManagerCopyAvailableFontFamilyNames.return_value = ["Arial", "Helvetica"]
            families = await discovery.list_families()
            assert isinstance(families, list)
            assert all(isinstance(f, str) for f in families)

    @pytest.mark.asyncio
    async def test_faces_for_family(self):
        """Test that faces_for_family returns FontFace objects."""
        with patch('macfonts.discovery.CoreText') as mock_ct:
            # Mock CoreText responses
            mock_descriptor = Mock()
            mock_ct.CTFontDescriptorCreateWithAttributes.return_value = mock_descriptor
            mock_ct.CTFontCollectionCreateWithFontDescriptors.return_value = Mock()
            mock_ct.CTFontCollectionCreateMatchingFontDescriptors.return_value = []
            
            faces = await discovery.faces_for_family("Arial")
            assert isinstance(faces, list)

    @pytest.mark.asyncio
    async def test_face_by_postscript(self):
        """Test PostScript name lookup."""
        with patch('macfonts.discovery._build_postscript_index') as mock_build:
            mock_face = FontFace(
                postScriptName="Arial-Regular",
                family="Arial",
                path="/test/path",
                format="ttf"
            )
            mock_build.return_value = {"Arial-Regular": mock_face}
            
            result = await discovery.face_by_postscript("Arial-Regular")
            assert result.postScriptName == "Arial-Regular"

class TestMetadata:
    @pytest.mark.asyncio
    async def test_enrich_face(self, mock_font_face):
        """Test font face enrichment."""
        with patch('macfonts.metadata.TTFont') as mock_ttfont:
            mock_font = Mock()
            mock_font.keys.return_value = ["name", "maxp"]
            mock_font.__getitem__.return_value = Mock()
            mock_font.close = Mock()
            mock_ttfont.return_value = mock_font
            
            enriched = await metadata.enrich_face(mock_font_face)
            assert enriched.postScriptName == mock_font_face.postScriptName

    @pytest.mark.asyncio
    async def test_face_by_postscript(self):
        """Test face lookup by PostScript name."""
        with patch('macfonts.discovery.face_by_postscript') as mock_lookup, \
             patch('macfonts.metadata.enrich_face') as mock_enrich:
            
            mock_face = FontFace(postScriptName="Test", family="Test", path="/test", format="ttf")
            mock_lookup.return_value = mock_face
            mock_enrich.return_value = mock_face
            
            result = await metadata.face_by_postscript("Test")
            assert result.postScriptName == "Test"

class TestConvert:
    @pytest.mark.asyncio
    async def test_convert_to_woff2(self, mock_font_face, sample_convert_options):
        """Test WOFF2 conversion."""
        with patch('macfonts.convert.TTFont') as mock_ttfont, \
             patch('macfonts.convert.save_font') as mock_save, \
             patch('macfonts.convert.os.path.exists') as mock_exists, \
             patch('macfonts.convert.os.path.getsize') as mock_size, \
             patch('macfonts.convert._sha256') as mock_sha:
            
            mock_exists.return_value = True
            mock_size.return_value = 1024
            mock_sha.return_value = "abcd1234"
            
            mock_font = Mock()
            mock_font.close = Mock()
            mock_ttfont.return_value = mock_font
            
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch('macfonts.convert.DEFAULT_OUT_DIR', tmpdir):
                    result = await convert.convert_to_woff2(
                        "/test/font.ttf", 
                        sample_convert_options, 
                        "TestFont"
                    )
                    
                    assert len(result) == 3  # path, size, sha
                    assert result[1] == 1024  # size
                    assert result[2] == "abcd1234"  # sha

class TestS3Publish:
    @pytest.mark.asyncio
    async def test_upload_woff2(self, sample_publish_options):
        """Test S3 upload."""
        with patch('macfonts.s3publish.boto3') as mock_boto3, \
             patch('macfonts.s3publish.os.path.exists') as mock_exists, \
             patch('macfonts.s3publish.os.path.getsize') as mock_size, \
             patch('macfonts.s3publish._hash') as mock_hash:
            
            mock_exists.return_value = True
            mock_size.return_value = 1024
            mock_hash.return_value = "abcd1234567890"
            
            mock_s3 = Mock()
            mock_s3.upload_file = Mock()
            mock_boto3.client.return_value = mock_s3
            
            result = await s3publish.upload_woff2("/test/font.woff2", sample_publish_options)
            
            assert result.size_bytes == 1024
            assert "test-bucket" in result.woff2_url
            assert result.css.startswith("@font-face")

class TestCache:
    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """Test cache set/get operations."""
        await cache.clear()
        
        # Test set and get
        await cache.set("test_key", "test_value", ttl=60)
        result = await cache.get("test_key")
        assert result == "test_value"
        
        # Test cache miss
        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        """Test cache expiration."""
        await cache.clear()
        
        # Set with very short TTL
        await cache.set("expire_test", "value", ttl=0.1)
        
        # Should still be there immediately
        result = await cache.get("expire_test")
        assert result == "value"
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        result = await cache.get("expire_test")
        assert result is None

def test_placeholder():
    """Keep original test for backwards compatibility."""
    assert True
