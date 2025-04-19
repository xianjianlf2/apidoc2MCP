/**
 * MCP service generator module
 * Generates MCP services based on OpenAPI specification
 */

import * as fs from 'fs-extra';
import * as path from 'path';
import logger from '../utils/logger';
import { MCPGenerator } from './mcp-generator';

/**
 * Generate MCP service
 * @param apiData OpenAPI specification API data
 * @param outputDir Output directory
 * @returns Whether generation was successful
 */
export async function generateMcpService(apiData: any, outputDir: string): Promise<boolean> {
  // Ensure output directory exists
  await fs.ensureDir(outputDir);

  // Create MCP generator instance
  const generator = new MCPGenerator(apiData);

  // Generate MCP service definition
  const mcpService = generator.generate();

  // If there are no valid endpoints, print warning
  if (!mcpService.functions || mcpService.functions.length === 0) {
    logger.warning("⚠️ No valid API endpoints found, cannot generate MCP service");
    return false;
  }

  // Write MCP service definition file
  const serviceJsonPath = path.join(outputDir, 'mcp-service.json');
  await fs.writeJson(serviceJsonPath, mcpService, { spaces: 2, encoding: 'utf-8' });

  // Generate JavaScript code implementation
  const jsCodePath = path.join(outputDir, 'mcp_server.js');
  const pythonCodeResult = await generator.generateJsCode(jsCodePath);

  // If JavaScript code generation failed, notify user
  if (pythonCodeResult === false) {
    logger.warning("⚠️ JavaScript code generation failed, check API documentation completeness");
  }

  // Generate simple documentation
  const docPath = path.join(outputDir, 'README.md');
  await generateDocumentation(apiData, generator, docPath);

  // Output summary information
  const incompleteCount = generator.incompleteEndpoints.length;
  const completeCount = mcpService.functions.length;

  if (completeCount > 0) {
    logger.info("✅ MCP service generation complete");
    logger.info(`- Successfully converted endpoints: ${completeCount}`);
    
    if (incompleteCount > 0) {
      logger.info(`- Unimplemented endpoints: ${incompleteCount} (see logs and README file)`);
    }

    return true;
  } else {
    logger.error("❌ MCP service generation failed: No valid endpoints generated");
    return false;
  }
}

/**
 * Generate MCP service documentation
 * @param apiData OpenAPI specification API data
 * @param generator MCP generator instance
 * @param outputPath Output file path
 */
async function generateDocumentation(apiData: any, generator: MCPGenerator, outputPath: string): Promise<void> {
  // Get API information
  const info = apiData.info || {};
  const title = info.title || 'Unnamed API';
  const description = info.description || '';
  const version = info.version || '1.0.0';

  // Generate document title
  let doc = `# ${title}\n\n`;

  // Add description
  if (description) {
    doc += `${description}\n\n`;
  }

  // Add version information
  doc += `Version: ${version}\n\n`;

  // Add server information
  const servers = apiData.servers || [];
  if (servers.length > 0) {
    doc += "## Servers\n\n";
    for (const server of servers) {
      doc += `- ${server.url}: ${server.description || ''}\n`;
    }
    doc += "\n";
  }

  // Add available functions
  doc += "## Available Functions\n\n";

  // Get endpoint information from generator
  for (const endpoint of generator.endpoints) {
    if (!generator.validateEndpoint(endpoint)) {
      continue;
    }

    const operationId = endpoint.operationId || generator.generateOperationId(endpoint);
    const summary = endpoint.summary || '';

    doc += `### ${operationId}\n\n`;

    if (summary) {
      doc += `${summary}\n\n`;
    }

    if (endpoint.description) {
      doc += `${endpoint.description}\n\n`;
    }

    doc += `**Request Method:** ${(endpoint.method || '').toUpperCase()}\n\n`;
    doc += `**Request Path:** ${endpoint.path || ''}\n\n`;

    // Parameters table
    const params = endpoint.parameters || [];
    if (params.length > 0) {
      doc += "**Parameters:**\n\n";
      doc += "| Name | Location | Type | Required | Description |\n";
      doc += "|------|----------|------|----------|-------------|\n";

      for (const param of params) {
        const name = param.name || '';
        const inType = param.in || '';
        const paramType = (param.schema?.type || 'string');
        const required = param.required ? 'Yes' : 'No';
        const description = param.description || '';

        doc += `| ${name} | ${inType} | ${paramType} | ${required} | ${description} |\n`;
      }

      doc += "\n";
    }

    // Request body
    const requestBody = endpoint.requestBody;
    if (requestBody) {
      doc += "**Request Body:**\n\n";
      doc += `Content-Type: ${requestBody.content_type || 'application/json'}\n\n`;

      const schema = requestBody.schema || {};
      if (Object.keys(schema).length > 0) {
        doc += "Schema:\n\n```json\n";
        doc += JSON.stringify(schema, null, 2);
        doc += "\n```\n\n";
      }
    }

    // Responses
    const responses = endpoint.responses || [];
    if (responses.length > 0) {
      doc += "**Responses:**\n\n";

      for (const response of responses) {
        const statusCode = response.status_code || '';
        const description = response.description || '';

        doc += `**Status Code:** ${statusCode} - ${description}\n\n`;

        const contentType = response.content_type || '';
        if (contentType) {
          doc += `Content-Type: ${contentType}\n\n`;
        }

        const schema = response.schema || {};
        if (Object.keys(schema).length > 0) {
          doc += "Schema:\n\n```json\n";
          doc += JSON.stringify(schema, null, 2);
          doc += "\n```\n\n";
        }
      }
    }

    doc += "---\n\n";
  }

  // Add unimplemented endpoints explanation
  if (generator.incompleteEndpoints.length > 0) {
    doc += "## Unimplemented Endpoints\n\n";
    doc += "The following endpoints were not implemented due to incomplete information:\n\n";

    for (const endpoint of generator.incompleteEndpoints) {
      const method = endpoint.method || 'unknown';
      const path = endpoint.path || 'unknown path';
      const reason = generator.getIncompletenessReason(endpoint);
      doc += `- **${method.toUpperCase()} ${path}**: ${reason}\n`;
    }

    doc += "\n";
  }

  // Add startup instructions
  doc += "## Startup and Usage\n\n";
  doc += "### Method 1: Direct Run\n\n";
  doc += "```bash\n";
  doc += "node mcp_server.js\n";
  doc += "```\n\n";

  doc += "### Method 2: Using MCP CLI Tool\n\n";
  doc += "```bash\n";
  doc += "mcp run mcp_server.js\n";
  doc += "```\n\n";

  doc += "### Method 3: Setting API Base URL\n\n";
  doc += "```bash\n";
  doc += "API_BASE_URL=https://api.example.com node mcp_server.js\n";
  doc += "```\n\n";

  // Write file
  await fs.writeFile(outputPath, doc, 'utf-8');
} 