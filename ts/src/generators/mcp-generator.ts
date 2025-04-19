/**
 * MCP service generator
 * Generates MCP services based on OpenAPI specification data
 */

import * as fs from 'fs-extra';
import logger from '../utils/logger';

/**
 * Endpoint information from OpenAPI
 */
interface Endpoint {
  path: string;
  method: string;
  operationId?: string;
  summary?: string;
  description?: string;
  parameters?: any[];
  requestBody?: any;
  responses?: any[];
}

/**
 * MCP generator class
 * Generates MCP services from OpenAPI specifications
 */
export class MCPGenerator {
  private apiData: any;
  public endpoints: Endpoint[];
  public incompleteEndpoints: Endpoint[] = [];

  /**
   * Initialize MCP generator
   * @param apiData OpenAPI specification API data
   */
  constructor(apiData: any) {
    this.apiData = apiData;
    // Convert OpenAPI specification to standard intermediate format
    this.endpoints = this.extractEndpointsFromOpenapi();
  }

  /**
   * Extract endpoint information from OpenAPI specification
   * @returns Endpoints list
   */
  private extractEndpointsFromOpenapi(): Endpoint[] {
    const endpoints: Endpoint[] = [];
    
    // Check if already in our intermediate format (has endpoints field)
    if ('endpoints' in this.apiData && Array.isArray(this.apiData.endpoints)) {
      return this.apiData.endpoints;
    }
    
    // If it's OpenAPI specification, extract endpoints from paths
    const paths = this.apiData.paths || {};
    
    for (const [path, pathItem] of Object.entries(paths)) {
      const pathObj = pathItem as any;
      
      for (const method of ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']) {
        if (method in pathObj) {
          const operation = pathObj[method];
          
          // Create endpoint object
          const endpoint: Endpoint = {
            path,
            method,
            operationId: operation.operationId || '',
            summary: operation.summary || '',
            description: operation.description || '',
            parameters: []
          };
          
          // Process parameters
          if (operation.parameters) {
            for (const param of operation.parameters) {
              endpoint.parameters!.push({
                name: param.name || '',
                in: param.in || '',
                description: param.description || '',
                required: param.required || false,
                schema: param.schema || { type: 'string' }
              });
            }
          }
          
          // Process request body
          if ('requestBody' in operation) {
            const content = operation.requestBody.content || {};
            const contentType = Object.keys(content)[0] || 'application/json';
            const schema = content[contentType]?.schema || {};
            
            endpoint.requestBody = {
              content_type: contentType,
              required: operation.requestBody.required || false,
              schema
            };
            
            // If request body is object type, extract properties as parameters
            if (schema.type === 'object' && 'properties' in schema) {
              const requiredProps = schema.required || [];
              for (const [propName, propSchema] of Object.entries(schema.properties)) {
                endpoint.parameters!.push({
                  name: propName,
                  in: 'body',
                  description: (propSchema as any).description || '',
                  required: requiredProps.includes(propName),
                  schema: propSchema
                });
              }
            }
          }
          
          // Process responses
          const responses: any[] = [];
          for (const [statusCode, response] of Object.entries(operation.responses || {})) {
            const content = (response as any).content || {};
            const contentType = Object.keys(content)[0] || '';
            const schema = content[contentType]?.schema || {};
            
            responses.push({
              status_code: statusCode,
              description: (response as any).description || '',
              content_type: contentType,
              schema
            });
          }
          
          endpoint.responses = responses;
          endpoints.push(endpoint);
        }
      }
    }
    
    logger.info(`🔍 Extracted ${endpoints.length} endpoints from OpenAPI specification`);
    return endpoints;
  }

  /**
   * Generate MCP service definition
   * @returns MCP service definition object
   */
  public generate(): any {
    const mcpService: any = {
      functions: []
    };

    for (const endpoint of this.endpoints) {
      // Validate endpoint information completeness
      if (this.validateEndpoint(endpoint)) {
        const func = this.createFunction(endpoint);
        mcpService.functions.push(func);
      } else {
        logger.warning(
          `⚠️ Skipping incomplete endpoint: ${endpoint.path || 'unknown path'} [${endpoint.method || 'unknown method'}]`
        );
        this.incompleteEndpoints.push(endpoint);
      }
    }

    return mcpService;
  }

  /**
   * Generate JavaScript code for MCP service
   * @param outputPath Output file path
   * @returns Boolean indicating whether generation was successful
   */
  public async generateJsCode(outputPath: string): Promise<boolean> {
    // Generate import statements
    let code = "#!/usr/bin/env node\n\n";
    code += "const { McpServer } = require('@modelcontextprotocol/sdk/server/mcp.js');\n";
    code += "const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');\n";
    code += "const axios = require('axios');\n";
    code += "const fs = require('fs');\n";
    code += "const path = require('path');\n";
    code += "const { z } = require('zod');\n";

    // Create MCP service instance
    const appName = this.apiData.info?.title || 'API Service';
    const version = this.apiData.info?.version || '1.0.0';
    const description = this.apiData.info?.description || '';
    
    code += `\n// ${appName} v${version}\n`;
    if (description) {
      code += `// ${description}\n`;
    }
    
    code += `const server = new McpServer({\n`;
    code += `  name: "${appName}",\n`;
    code += `  version: "${version}"\n`;
    code += `});\n\n`;

    // Add base URL configuration
    code += "// Configure base URL, can be overridden with environment variables\n";
    code += "const BASE_URL = process.env.API_BASE_URL || '';\n\n";

    // Generate complete implementation for each endpoint
    let validEndpointsCount = 0;
    for (const endpoint of this.endpoints) {
      if (!this.validateEndpoint(endpoint)) {
        continue;
      }

      validEndpointsCount++;
      const operationId = endpoint.operationId || this.generateOperationId(endpoint);
      const path = endpoint.path;

      // All endpoints will be implemented as tools in this version
      code += this.generateToolCode(endpoint, operationId, path);
    }

    // If no valid endpoints, return false
    if (validEndpointsCount === 0) {
      logger.warning("⚠️ No valid endpoints found for JavaScript code generation");
      return false;
    }

    // Connect to MCP using stdio transport
    code += "\n// Connect to MCP using stdio transport\n";
    code += "const transport = new StdioServerTransport();\n";
    code += "server.connect(transport).catch(console.error);\n";

    // Write file
    try {
      await fs.writeFile(outputPath, code, 'utf-8');
      logger.info(`✅ Successfully generated JavaScript MCP service to: ${outputPath}`);
      return true;
    } catch (error) {
      logger.error(`❌ Error writing JavaScript file: ${(error as Error).message}`);
      return false;
    }
  }

  /**
   * Validate endpoint information completeness
   * @param endpoint Endpoint to validate
   * @returns Whether the endpoint is valid and complete
   */
  public validateEndpoint(endpoint: Endpoint): boolean {
    // Endpoint must have path
    if (!endpoint.path) {
      return false;
    }

    // Method must be valid
    const validMethods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head'];
    if (!endpoint.method || !validMethods.includes(endpoint.method.toLowerCase())) {
      return false;
    }

    // Either operationId or enough info to generate one is required
    if (!endpoint.operationId && !endpoint.path) {
      return false;
    }

    // Parameters must be well-defined
    if (endpoint.parameters) {
      for (const param of endpoint.parameters) {
        if (!param.name || !param.in) {
          return false;
        }
      }
    }

    return true;
  }

  /**
   * Get reason why an endpoint is incomplete
   * @param endpoint Incomplete endpoint
   * @returns Reason string
   */
  public getIncompletenessReason(endpoint: Endpoint): string {
    // Endpoint must have path
    if (!endpoint.path) {
      return "Missing path";
    }

    // Method must be valid
    const validMethods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head'];
    if (!endpoint.method || !validMethods.includes(endpoint.method.toLowerCase())) {
      return "Invalid or missing HTTP method";
    }

    // Either operationId or enough info to generate one is required
    if (!endpoint.operationId && !endpoint.path) {
      return "Missing operationId and insufficient info to generate one";
    }

    // Parameters must be well-defined
    if (endpoint.parameters) {
      for (const param of endpoint.parameters) {
        if (!param.name || !param.in) {
          return "Invalid parameter definition (missing name or location)";
        }
      }
    }

    return "Unknown incompleteness reason";
  }

  /**
   * Check if endpoint should be implemented as a resource
   * @param endpoint Endpoint to check
   * @returns Whether the endpoint should be a resource
   */
  private isResourceEndpoint(endpoint: Endpoint): boolean {
    // Resources are usually GET requests retrieving data
    if (endpoint.method.toLowerCase() !== 'get') {
      return false;
    }

    // Check if path looks like a resource path
    // E.g. /users/{id}, /products/{id}
    const resourcePattern = /\/[a-zA-Z0-9_]+\/\{[a-zA-Z0-9_]+\}$/;
    return resourcePattern.test(endpoint.path);
  }

  /**
   * Convert path to resource format
   * @param path Original path
   * @returns Resource path format
   */
  private convertPathToResource(path: string): string {
    // Extract resource type and ID parameter from path
    // E.g. /users/{id} -> users/{id}
    const segments = path.split('/').filter(s => s.length > 0);
    if (segments.length < 2) {
      return path;
    }

    // Get resource type (usually the plural noun)
    const resourceType = segments[0];
    
    // Collect all path parameters
    const params = [];
    for (const segment of segments) {
      if (segment.startsWith('{') && segment.endsWith('}')) {
        params.push(segment);
      }
    }

    if (params.length === 0) {
      return resourceType;
    }

    return `${resourceType}/${params.join('/')}`;
  }

  /**
   * Generate resource code for endpoint
   * @param endpoint Endpoint information
   * @param operationId Operation ID
   * @param path API path
   * @returns Generated code
   */
  private generateResourceCode(endpoint: Endpoint, operationId: string, path: string): string {
    const resourceName = this.convertPathToResource(path);
    const paramCode = this.replacedPathParams(path);
    const resourceParams = this.createParameters(endpoint);

    let code = `// Resource: ${operationId}\n`;
    code += `// TODO: Resources are not fully implemented in current MCP SDK version\n`;
    code += `// Converting to a tool instead\n`;
    
    // Convert to tool implementation instead
    return this.generateToolCode(endpoint, operationId, path);
  }

  /**
   * Generate tool code for endpoint
   * @param endpoint Endpoint information
   * @param operationId Operation ID
   * @param path API path
   * @returns Generated code
   */
  private generateToolCode(endpoint: Endpoint, operationId: string, path: string): string {
    const paramCode = this.replacedPathParams(path);
    const toolParams = this.createParameters(endpoint);

    let code = `// Tool: ${operationId}\n`;
    
    // Define tool parameters schema
    let paramDefs = '';
    if (toolParams && Object.keys(toolParams).length > 0) {
      for (const [paramName, paramDef] of Object.entries(toolParams)) {
        const type = (paramDef as any).type;
        const required = (paramDef as any).required;
        
        if (required) {
          paramDefs += `  ${paramName}: z.${type}(),\n`;
        } else {
          paramDefs += `  ${paramName}: z.${type}().optional(),\n`;
        }
      }
    }
    
    // Generate tool handler using the correct MCP SDK syntax
    code += `server.tool("${operationId}", {\n`;
    
    // Add parameter schema
    if (paramDefs) {
      code += `${paramDefs}`;
    }
    
    code += `}, async (params) => {\n`;
    code += `  try {\n`;
    code += `    const url = \`\${BASE_URL}${paramCode}\`;\n`;
    
    // For different HTTP methods, handle parameters differently
    if (endpoint.method.toLowerCase() === 'get' || endpoint.method.toLowerCase() === 'delete') {
      // Handle query parameters
      if (endpoint.parameters && endpoint.parameters.some(p => p.in === 'query')) {
        code += `    const queryParams = {};\n`;
        for (const param of endpoint.parameters.filter(p => p.in === 'query')) {
          if (param.required) {
            code += `    if (params.${param.name} !== undefined) queryParams.${param.name} = params.${param.name};\n`;
          } else {
            code += `    if (params.${param.name}) queryParams.${param.name} = params.${param.name};\n`;
          }
        }
        
        code += `    const response = await axios({\n`;
        code += `      method: '${endpoint.method.toUpperCase()}',\n`;
        code += `      url,\n`;
        code += `      params: queryParams\n`;
        code += `    });\n`;
      } else {
        code += `    const response = await axios({\n`;
        code += `      method: '${endpoint.method.toUpperCase()}',\n`;
        code += `      url\n`;
        code += `    });\n`;
      }
    } else {
      // POST, PUT, PATCH methods - handle request body
      if (endpoint.requestBody) {
        code += `    const requestData = {};\n`;
        
        // If we have parameters marked as 'body', use them for the request body
        const bodyParams = endpoint.parameters?.filter(p => p.in === 'body');
        if (bodyParams && bodyParams.length > 0) {
          for (const param of bodyParams) {
            if (param.required) {
              code += `    if (params.${param.name} !== undefined) requestData.${param.name} = params.${param.name};\n`;
            } else {
              code += `    if (params.${param.name}) requestData.${param.name} = params.${param.name};\n`;
            }
          }
        } else {
          // Otherwise, use all parameters
          for (const paramName of Object.keys(toolParams)) {
            code += `    if (params.${paramName}) requestData.${paramName} = params.${paramName};\n`;
          }
        }
        
        // Handle query parameters
        const queryParams = endpoint.parameters?.filter(p => p.in === 'query');
        if (queryParams && queryParams.length > 0) {
          code += `    const queryParams = {};\n`;
          for (const param of queryParams) {
            if (param.required) {
              code += `    if (params.${param.name} !== undefined) queryParams.${param.name} = params.${param.name};\n`;
            } else {
              code += `    if (params.${param.name}) queryParams.${param.name} = params.${param.name};\n`;
            }
          }
          
          code += `    const response = await axios({\n`;
          code += `      method: '${endpoint.method.toUpperCase()}',\n`;
          code += `      url,\n`;
          code += `      params: queryParams,\n`;
          code += `      headers: { 'Content-Type': '${endpoint.requestBody.content_type || 'application/json'}' },\n`;
          code += `      data: requestData\n`;
          code += `    });\n`;
        } else {
          code += `    const response = await axios({\n`;
          code += `      method: '${endpoint.method.toUpperCase()}',\n`;
          code += `      url,\n`;
          code += `      headers: { 'Content-Type': '${endpoint.requestBody.content_type || 'application/json'}' },\n`;
          code += `      data: requestData\n`;
          code += `    });\n`;
        }
      } else {
        // No request body
        code += `    const response = await axios({\n`;
        code += `      method: '${endpoint.method.toUpperCase()}',\n`;
        code += `      url\n`;
        code += `    });\n`;
      }
    }
    
    // Return result in MCP format
    code += `    return { content: [{ type: "text", text: JSON.stringify(response.data) }] };\n`;
    code += `  } catch (error) {\n`;
    code += `    return { content: [{ type: "text", text: \`Error calling ${operationId}: \${error.message}\` }] };\n`;
    code += `  }\n`;
    code += `});\n\n`;
    
    return code;
  }

  /**
   * Replace path parameters with template literals
   * @param path API path with parameters
   * @returns Path with template literals
   */
  private replacedPathParams(path: string): string {
    // Replace {paramName} with ${params.paramName}
    return path.replace(/{([^}]+)}/g, '${params.$1}');
  }

  /**
   * Get JavaScript type from API type
   * @param apiType API data type
   * @returns JavaScript type
   */
  private getJsType(apiType: string): string {
    switch (apiType.toLowerCase()) {
      case 'integer':
      case 'number':
        return 'number';
      case 'boolean':
        return 'boolean';
      case 'array':
        return 'array';
      case 'object':
        return 'object';
      case 'string':
      default:
        return 'string';
    }
  }

  /**
   * Create function definition for MCP service
   * @param endpoint Endpoint information
   * @returns Function definition
   */
  private createFunction(endpoint: Endpoint): any {
    const operationId = endpoint.operationId || this.generateOperationId(endpoint);
    
    // Create basic function definition
    const func: any = {
      name: operationId,
      description: endpoint.description || endpoint.summary || `${endpoint.method.toUpperCase()} ${endpoint.path}`,
      parameters: this.createParameters(endpoint)
    };

    // Check for response schema to infer return type
    if (endpoint.responses && endpoint.responses.length > 0) {
      const successResponse = endpoint.responses.find(r => r.status_code.startsWith('2')) || endpoint.responses[0];
      
      if (successResponse.schema) {
        // Add response schema hint
        func.response = successResponse.schema;
      }
    }

    return func;
  }

  /**
   * Generate operation ID from endpoint information
   * @param endpoint Endpoint information
   * @returns Generated operation ID
   */
  public generateOperationId(endpoint: Endpoint): string {
    // Remove URL parameters and split by path segments
    const cleanPath = endpoint.path.replace(/{[^}]+}/g, '');
    const segments = cleanPath.split('/').filter(s => s.length > 0);
    
    if (segments.length === 0) {
      return `${endpoint.method.toLowerCase()}Root`;
    }
    
    // Generate camelCase operation ID
    let opId = endpoint.method.toLowerCase();
    
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      
      if (segment.length > 0) {
        // Capitalize first letter and append to operation ID
        opId += segment.charAt(0).toUpperCase() + segment.slice(1);
      }
    }
    
    return opId;
  }

  /**
   * Create parameters from endpoint information
   * @param endpoint Endpoint information
   * @returns Parameters object
   */
  private createParameters(endpoint: Endpoint): any {
    const parameters: any = {};
    
    // Add path parameters
    const pathRegex = /{([^}]+)}/g;
    let match;
    
    while ((match = pathRegex.exec(endpoint.path)) !== null) {
      const paramName = match[1];
      parameters[paramName] = {
        type: 'string',
        description: `Path parameter: ${paramName}`,
        required: true
      };
    }
    
    // Add query parameters
    if (endpoint.parameters) {
      for (const param of endpoint.parameters) {
        if (param.in !== 'path' && !(param.in === 'body' && endpoint.requestBody)) {
          // Skip path parameters that were already added and body parameters if requestBody exists
          parameters[param.name] = {
            type: this.getJsonSchemaType(param.schema?.type || 'string'),
            description: param.description || `${param.in} parameter: ${param.name}`,
            required: !!param.required
          };
          
          // Add enum values if available
          if (param.schema?.enum) {
            parameters[param.name].enum = param.schema.enum;
          }
        }
      }
    }
    
    // Add body parameters
    if (endpoint.requestBody && endpoint.requestBody.schema && endpoint.requestBody.schema.properties) {
      const requiredProps = endpoint.requestBody.schema.required || [];
      
      for (const [propName, propSchema] of Object.entries(endpoint.requestBody.schema.properties)) {
        const schema = propSchema as any;
        parameters[propName] = {
          type: this.getJsonSchemaType(schema.type || 'string'),
          description: schema.description || `Request body property: ${propName}`,
          required: requiredProps.includes(propName)
        };
        
        // Add enum values if available
        if (schema.enum) {
          parameters[propName].enum = schema.enum;
        }
      }
    }
    
    return parameters;
  }

  /**
   * Convert API type to JSON Schema type
   * @param apiType API data type
   * @returns JSON Schema type
   */
  private getJsonSchemaType(apiType: string): string {
    switch (apiType.toLowerCase()) {
      case 'integer':
      case 'number':
        return 'number';
      case 'boolean':
        return 'boolean';
      case 'array':
        return 'array';
      case 'object':
        return 'object';
      case 'string':
      default:
        return 'string';
    }
  }
} 