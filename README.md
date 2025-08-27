# macOS Fonts MCP Server (v0.2)

A high-performance Model Context Protocol (MCP) server for macOS font discovery, webfont conversion, and cloud publishing. Built with async/await, comprehensive caching, and production-ready error handling.

## ✨ Features

### Core Tools
- **`list_families()`** - Enumerate all macOS font families with caching
- **`faces_for_family({ "family": "..." })`** - Get detailed font face information
- **`font_overview({ "postScriptName": "..." })`** - Font Book-style metadata overview
- **`publish_font({ "postScriptName": "...", "convert": {...}, "publish": {...} })`** - Complete font publishing pipeline

### Performance & Reliability
- **⚡ Async Operations**: All font processing wrapped with `asyncio.to_thread()`
- **🚀 Smart Caching**: Multi-level caching for font metadata and family listings
- **🔍 O(1) Lookups**: PostScript name index for instant font resolution  
- **🔄 S3 Retry Logic**: Exponential backoff with connection pooling
- **🧹 Auto Cleanup**: Background cleanup of generated files and cache
- **📊 Structured Logging**: JSON logging with comprehensive error tracking

### Production Ready
- **✅ Input Validation**: Pydantic models for all tool inputs
- **🛡️ Error Handling**: Graceful degradation with detailed error reporting
- **🧪 Comprehensive Tests**: Unit and integration test coverage
- **📈 Resource Management**: Memory-efficient font processing with cleanup

## 🚀 Quick Start

```bash
# Setup environment
uv venv
source .venv/bin/activate

# Install with development tools
uv pip install -e .[dev]

# Run all checks
make check

# Start the server
make run
```

## 🛠️ Development

```bash
# Setup development environment
make setup-dev

# Run tests with coverage
make test-coverage

# Format and lint code
make format
make lint

# Type checking
make type-check

# Clean up generated files
make clean
```

## 📊 Publishing Workflow

The `publish_font` tool provides a complete pipeline:

1. **Font Resolution** - Fast PostScript name lookup via indexed cache
2. **Optional Processing** - Subsetting, variable font instancing, hint dropping
3. **WOFF2 Conversion** - Industry-standard web font generation
4. **S3 Upload** - Reliable cloud storage with retry logic
5. **CSS Generation** - Production-ready @font-face rules
6. **Sample HTML** - Instant preview generation

## 🏗️ Architecture

- **Async-First Design**: Non-blocking I/O for all operations
- **Layered Caching**: In-memory cache + PostScript index + S3 deduplication
- **Resource Cleanup**: Automatic cleanup of temporary files and memory
- **Error Recovery**: Comprehensive error handling with fallback strategies
- **Production Logging**: Structured JSON logs for monitoring and debugging
