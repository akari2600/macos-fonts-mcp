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
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel

# Install with development tools
pip install -e .[dev]

# Run all checks
make check

# Start the server
make run
```

### Alternative Installation Methods

**With uv (if available):**
```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
```

**With requirements files:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

**Production only:**
```bash
pip install -e .
# or
pip install -r requirements.txt
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

## 🔧 Troubleshooting

### Installation Issues

**"pip install -e .[dev]" doesn't work:**
```bash
# Try upgrading pip first
pip install --upgrade pip setuptools wheel
pip install -e .[dev]

# Or use requirements files
pip install -r requirements-dev.txt

# Or install dependencies separately
pip install -e .
pip install pytest pytest-asyncio pytest-mock pytest-cov rich loguru mypy black isort flake8
```

**Missing PyObjC on non-macOS systems:**
The server requires macOS and PyObjC frameworks. For development on other systems:
```bash
# Install without macOS-specific dependencies
pip install mcp fonttools boto3 pydantic pytest
```

**Virtual environment issues:**
```bash
# On Ubuntu/Debian, install venv support
sudo apt install python3-venv python3-pip

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate
```

### Runtime Issues

**CoreText import errors:**
This is expected on non-macOS systems. The server is designed to run on macOS only.

**S3 upload failures:**
Ensure AWS credentials are configured:
```bash
aws configure
# or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```
