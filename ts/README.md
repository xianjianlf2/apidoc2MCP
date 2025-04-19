# API Documentation Parser Debugging Guide

This project contains an API documentation parser that supports parsing different formats of API documentation, including Swagger, OpenAPI, Markdown, and HTML.

## Directory Structure

```
.
├── src/
│   ├── parsers/            # Parser implementations
│   │   ├── index.ts        # Main entry point
│   │   ├── swagger.ts      # Swagger parser
│   │   ├── openapi.ts      # OpenAPI parser
│   │   ├── markdown.ts     # Markdown parser
│   │   └── crawler.ts      # Generic web crawler parser
│   └── utils/              # Utility functions
├── examples/               # Example API documentation
│   ├── openapi.json        # OpenAPI 3.0 example
│   ├── swagger.json        # Swagger 2.0 example
│   └── api-docs.md         # Markdown format API documentation
└── debug-example.ts        # Debug example code
```

## How to Debug

We provide a debug example file `debug-example.ts` that demonstrates how to use the parser to handle different types of API documentation.

### Step 1: Install Dependencies

```bash
npm install
```

### Step 2: Run Debug Example

```bash
# Compile TypeScript
npx tsc

# Run example
node dist/debug-example.js
```

## Debug Case Descriptions

`debug-example.ts` includes the following debug cases:

1. **Parse OpenAPI Document** - Shows how to parse local OpenAPI 3.0 documentation
2. **Parse Swagger Document** - Shows how to parse local Swagger 2.0 documentation
3. **Parse API Documentation from URL** - Shows how to automatically detect and parse API documentation from a remote URL
4. **Parse Markdown Document** - Shows how to parse Markdown format API documentation
5. **Failure Scenarios and Error Handling** - Shows how to handle parsing failures

## Test with Your Own API Documentation

You can test with your own API documentation:

```typescript
import { parseDocument } from './src/parsers';

async function testWithYourDocument() {
  try {
    // Replace with your API documentation path
    const result = await parseDocument('./path/to/your/api-doc.json');
    console.log(result);
  } catch (error) {
    console.error('Parsing failed:', error);
  }
}

testWithYourDocument();
```

## Troubleshooting

If parsing fails, you can try:

1. Check if the document format is correct
2. Manually specify the parsing format (e.g., 'swagger', 'openapi', 'markdown', 'html')
3. Check the log output for detailed error information

## Supported Document Formats

- Swagger 2.0
- OpenAPI 3.x
- Markdown
- HTML (parsed via crawler)
- Web Scraping (fallback option when other methods fail) 