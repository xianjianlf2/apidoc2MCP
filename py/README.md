# apidoc2MCP

Convert API Documentation to Model Context Protocol (MCP) Services

## Introduction

apidoc2MCP is a tool that converts various formats of API documentation (such as OpenAPI/Swagger, Markdown, HTML, etc.) into MCP service definitions.
MCP (Model Context Protocol) is a protocol for communication between Large Language Models (LLMs) and applications, enabling models to leverage tools, resources, and prompts provided by applications.

## Project Structure

```
py/
├── main.py              # Main program entry
├── pipeline.py          # Processing pipeline
├── requirements.txt     # Dependencies file
├── parsers/             # Parser modules
│   ├── __init__.py      # Parser entry
│   ├── base.py          # Base parser class
│   ├── swagger.py       # Swagger 2.0 parser
│   ├── openapi.py       # OpenAPI 3.x parser
│   ├── markdown.py      # Markdown parser
│   └── crawler.py       # HTML web crawler parser
├── converters/          # Converter modules
│   └── __init__.py      # Standard format conversion
├── generators/          # Generator modules
│   ├── __init__.py      # Generator entry
│   └── mcp_generator.py # MCP service generator
└── utils/               # Utility modules
    └── logger.py        # Logging utilities
```

## Installation

### Using pip

```bash
pip install -r requirements.txt
```

### Using uv to create environment and install dependencies (recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager and environment manager. Using uv can create virtual environments and install dependencies more quickly:

```bash
# Install uv (if not already installed)
pip install uv

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Activate virtual environment
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

## Usage

### Command Line Usage

```bash
python py/main.py <input_doc_path> [--format <doc_format>] [--output <output_dir>] [--name <service_name>]
```

Parameters:
- `<input_doc_path>`: Path to the input API documentation, can be a local file path or URL
- `--format`: Format of the input document, options are `swagger`, `openapi`, `markdown`, `html`, `auto`, default is `auto` (auto-detect)
- `--output`: Output directory, default is `./O_MCP_SERVER_LIST`
- `--name`: MCP service name, if specified, it will be used as the service name and automatically appended to the output directory, e.g., `./O_MCP_SERVER_LIST/my_service`

Examples:

```bash
# Basic usage
python py/main.py api.json

# Specify document format and output directory
python py/main.py api.json --format openapi --output ./my_output

# Specify service name
python py/main.py api.json --name weather_api
# Output directory will be: ./O_MCP_SERVER_LIST/weather_api

# Parse API information from HTML web pages
python py/main.py https://example.com/api-docs.html --format html
```

### Processing Pipeline

apidoc2MCP implements a three-stage pipeline processing:

1. **Parsing Stage** - Parse different formats of API documentation:
   - OpenAPI 3.x
   - Swagger 2.0
   - Markdown
   - HTML web pages (via crawler parser)

2. **Conversion Stage** - Convert parsed data to a unified OpenAPI format:
   - Standardize API data from various formats
   - Validate data completeness
   - Cache parsing results to improve efficiency for repeated processing

3. **Generation Stage** - Generate MCP services from standardized data:
   - Generate MCP service definition file (`mcp-service.json`)
   - Generate directly runnable Python implementation code (`mcp_server.py`)
   - Generate simple API documentation (`README.md`)

### Output Files

The tool generates the following files in the output directory:
- `mcp-service.json`: MCP service definition file conforming to the MCP protocol specification
- `mcp_server.py`: Directly runnable MCP service Python code based on the MCP Python SDK
- `README.md`: Simple API documentation

## Starting and Using the MCP Service

The generated MCP service is implemented based on the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) and can be started in several ways:

### 1. Run the Python File Directly

```bash
python <output_dir>/mcp_server.py
```

### 2. Run with the MCP CLI Tool

```bash
# Run in development mode
mcp dev <output_dir>/mcp_server.py

# Or run directly
mcp run <output_dir>/mcp_server.py
```

### 3. Use Environment Variables to Customize API Base URL

If you need to connect to a specific API server, you can set the base URL through environment variables:

```bash
# Windows
set API_BASE_URL=https://your-api-base-url
python <output_dir>/mcp_server.py

# Linux/macOS
API_BASE_URL=https://your-api-base-url python <output_dir>/mcp_server.py
```

### 4. Deploy as a Service

For production environments, you can deploy the generated MCP service as a resident service:

```bash
# Use nohup to run in the background
nohup python <output_dir>/mcp_server.py > mcp_service.log 2>&1 &

# Or use pm2 for management (requires pm2 to be installed)
pm2 start <output_dir>/mcp_server.py --name "mcp-service" --interpreter python
```

### After Service Startup

Once the MCP service starts, it can be used in large language models or tools that support the MCP protocol. The service will automatically provide the following MCP features based on the API characteristics:

1. **Tools**: All API interfaces are implemented as tool interfaces by default, using asynchronous programming to communicate with backend APIs
   ```python
   @mcp.tool()
   async def search_users(query: str, limit: int) -> str:
       """Search users"""
       async with httpx.AsyncClient() as client:
           response = await client.get(f"{BASE_URL}/users/search", params={"q": query, "limit": limit})
           return response.text
   ```

## Key Features

### HTML Document Crawler Parser

apidoc2MCP supports extracting API information from ordinary HTML web pages, even without standard OpenAPI/Swagger documentation. The crawler parser will:

- Automatically identify code blocks, tables, and specific structures in the page
- Extract possible API paths, HTTP methods, and parameter information
- Support extraction of command line interface information
- Adapt to pages with various HTML structures

For unstructured API documentation, use the `--format html` parameter to specify using the crawler parser.

### Automatic Type Conversion

The system automatically converts different formats of API documentation to the standard OpenAPI 3.0 format:

- Support upgrading from Swagger 2.0 to OpenAPI 3.0
- Support extracting API information from Markdown tables
- Support extracting API information from HTML pages
- Support caching conversion results to improve efficiency

### Performance Metrics

The system records processing time and related metrics for each stage:

- Parsing stage duration
- Conversion stage duration
- Generation stage duration
- Total processing time
- Number of successfully processed endpoints

## Troubleshooting

If you encounter issues during service generation or startup:

1. **Check API Documentation Completeness**: Ensure the documentation includes complete path, method, and parameter definitions
2. **Check Log Output**: The program outputs detailed logs indicating which endpoints were not implemented due to incomplete information
3. **Check the Generated README.md**: Contains information about the generated API and reasons for unimplemented endpoints
4. **Verify API Base URL**: Ensure the environment variable `API_BASE_URL` is set correctly, or modify it in the code
5. **Check Dependencies**: Ensure all necessary dependencies are installed, especially `beautifulsoup4` and `httpx`

## Example

Input OpenAPI document:
```yaml
openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
paths:
  /users/{id}:
    get:
      summary: Get user information
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        200:
          description: Success
```

Generated MCP service code:
```python
from mcp.server.fastmcp import FastMCP
import httpx
import json
import os

mcp = FastMCP("User API", dependencies=["httpx"])

# Configure base URL, can be overridden by environment variable
BASE_URL = os.environ.get('API_BASE_URL', '')

@mcp.tool()
async def get_user(id: int) -> str:
    """Get user information"""
    # Build request URL
    url = BASE_URL + f"/users/{id}"
    
    # Send request to get resource
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

if __name__ == "__main__":
    # Start MCP server
    mcp.run()
```

## License

MIT 