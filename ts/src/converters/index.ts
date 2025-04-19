/**
 * API data converter module
 * Converts parsed API data to standard format (OpenAPI)
 */

import * as crypto from 'crypto';
import * as fs from 'fs-extra';
import * as path from 'path';
import logger from '../utils/logger';

// Cache directory
const CACHE_DIR = path.join(__dirname, '..', '..', 'cache');
fs.ensureDirSync(CACHE_DIR);

/**
 * Convert parsed API data to standard format (OpenAPI)
 * @param apiData Parsed API data
 * @returns Standard format API data
 */
export async function convertToStandardFormat(apiData: any): Promise<any> {
  // Check if input data is valid
  if (!apiData) {
    logger.warning("⚠️ Input API data is empty, cannot convert");
    return null;
  }

  // Generate cache key
  const cacheKey = generateCacheKey(apiData);
  const cacheFile = path.join(CACHE_DIR, `${cacheKey}.json`);

  // Check cache
  if (await fs.pathExists(cacheFile)) {
    logger.info("🔄 Loading conversion result from cache");
    try {
      return await fs.readJson(cacheFile, { encoding: 'utf-8' });
    } catch (e) {
      const error = e as Error;
      logger.warning(`⚠️ Cache loading failed: ${error.message}`);
    }
  }

  // Detect data format
  const dataFormat = detectFormat(apiData);
  logger.info(`🔍 Detected API data format: ${dataFormat}`);

  // Convert based on detected format
  let result: any;
  if (dataFormat === 'openapi') {
    // Data is already OpenAPI format, return directly
    result = apiData;
    logger.info("✅ Data is already OpenAPI format, no conversion needed");
  } else if (dataFormat === 'swagger') {
    // Convert Swagger to OpenAPI 3.0
    result = convertSwaggerToOpenapi(apiData);
    logger.info("🔄 Swagger data converted to OpenAPI format");
  } else if (dataFormat === 'custom') {
    // Convert custom format to OpenAPI
    result = convertCustomToOpenapi(apiData);
    logger.info("🔄 Custom format data converted to OpenAPI format");
  } else if (dataFormat === 'unstructured') {
    // Unstructured data requires LLM processing
    logger.warning("⚠️ Detected unstructured data, marking as TODO");
    console.log(apiData);
    result = markUnstructuredAsTodo(apiData);
  } else {
    // Unknown format
    logger.warning(`⚠️ Unknown API data format: ${dataFormat}, trying generic conversion`);
    result = convertToOpenapiGeneric(apiData);
  }

  // Validate conversion result against OpenAPI specification
  if (validateOpenapi(result)) {
    // Cache conversion result
    try {
      await fs.writeJson(cacheFile, result, { encoding: 'utf-8', spaces: 2 });
      logger.info("💾 Conversion result cached");
    } catch (e) {
      const error = e as Error;
      logger.warning(`⚠️ Cache writing failed: ${error.message}`);
    }
  } else {
    logger.warning("⚠️ Conversion result does not conform to OpenAPI specification, skipping cache");
  }

  return result;
}

/**
 * Generate cache key for API data
 * @param apiData API data
 * @returns Cache key string
 */
function generateCacheKey(apiData: any): string {
  // Convert API data to JSON string
  let dataStr: string;
  try {
    dataStr = JSON.stringify(apiData, Object.keys(apiData).sort());
  } catch {
    // If serialization fails, use string representation
    dataStr = String(apiData);
  }

  // Calculate MD5 hash as cache key
  return crypto.createHash('md5').update(dataStr).digest('hex');
}

/**
 * Detect API data format
 * @param apiData API data
 * @returns Data format string: 'openapi', 'swagger', 'custom', 'unstructured'
 */
function detectFormat(apiData: any): string {
  // Check if it's an object
  if (typeof apiData !== 'object' || apiData === null) {
    return 'unstructured';
  }

  // Check OpenAPI 3.x
  if ('openapi' in apiData && String(apiData.openapi).startsWith('3.')) {
    return 'openapi';
  }

  // Check Swagger 2.0
  if ('swagger' in apiData && apiData.swagger === '2.0') {
    return 'swagger';
  }

  // Check if it's our custom intermediate format
  if ('endpoints' in apiData && Array.isArray(apiData.endpoints)) {
    return 'custom';
  }

  // Other cases treated as unstructured data
  return 'unstructured';
}

/**
 * Convert Swagger 2.0 data to OpenAPI 3.0 format
 * @param swaggerData Swagger 2.0 data
 * @returns OpenAPI 3.0 format data
 */
function convertSwaggerToOpenapi(swaggerData: any): any {
  // Create OpenAPI 3.0 basic structure
  const openapiData: any = {
    'openapi': '3.0.0',
    'info': swaggerData.info || { 'title': 'API', 'version': '1.0.0' },
    'paths': {},
    'components': {
      'schemas': swaggerData.definitions || {},
      'parameters': swaggerData.parameters || {},
      'responses': swaggerData.responses || {}
    }
  };

  // Convert paths
  const paths = swaggerData.paths || {};
  for (const [path, pathItem] of Object.entries(paths)) {
    openapiData.paths[path] = {};
    const pathObj = pathItem as any;

    for (const method of ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']) {
      if (method in pathObj) {
        const operation = pathObj[method];
        
        // Convert parameters
        const parameters: any[] = [];
        for (const param of operation.parameters || []) {
          if (param.in !== 'body') {
            // Non-body parameters added directly
            parameters.push(param);
          } else {
            // Body parameters converted to requestBody
            const schema = param.schema || {};
            openapiData.paths[path][method] = {
              ...operation,
              'requestBody': {
                'content': {
                  'application/json': {
                    'schema': schema
                  }
                },
                'required': param.required || false
              }
            };
          }
        }

        // Update operation definition
        if (!openapiData.paths[path][method]) {
          openapiData.paths[path][method] = {
            ...operation,
            'parameters': parameters
          };
        } else {
          openapiData.paths[path][method].parameters = parameters;
        }

        // Remove old parameters field
        if ('parameters' in operation && parameters.length === 0) {
          delete openapiData.paths[path][method].parameters;
        }
      }
    }
  }

  return openapiData;
}

/**
 * Convert custom format data to OpenAPI 3.0 format
 * @param customData Custom format data
 * @returns OpenAPI 3.0 format data
 */
function convertCustomToOpenapi(customData: any): any {
  // Create OpenAPI 3.0 basic structure
  const openapiData: any = {
    'openapi': '3.0.0',
    'info': {
      'title': customData.title || 'API',
      'version': customData.version || '1.0.0',
      'description': customData.description || ''
    },
    'paths': {}
  };

  // Convert endpoints
  for (const endpoint of customData.endpoints || []) {
    const path = endpoint.path;
    const method = (endpoint.method || 'get').toLowerCase();

    if (!path) {
      continue;
    }

    // Ensure path exists
    if (!openapiData.paths[path]) {
      openapiData.paths[path] = {};
    }

    // Create operation object
    const operation: any = {
      'summary': endpoint.summary || '',
      'description': endpoint.description || '',
      'operationId': endpoint.operationId || '',
      'parameters': [],
      'responses': {
        '200': {
          'description': 'Successful operation',
          'content': {}
        }
      }
    };

    // Convert parameters
    for (const param of endpoint.parameters || []) {
      operation.parameters.push({
        'name': param.name || '',
        'in': param.in || 'query',
        'description': param.description || '',
        'required': param.required || false,
        'schema': param.schema || { 'type': 'string' }
      });
    }

    // Convert request body if present
    if (endpoint.requestBody) {
      operation.requestBody = {
        'content': {
          [endpoint.requestBody.content_type || 'application/json']: {
            'schema': endpoint.requestBody.schema || {}
          }
        },
        'required': endpoint.requestBody.required || false
      };
    }

    // Convert responses
    if (endpoint.responses && endpoint.responses.length > 0) {
      operation.responses = {};

      for (const response of endpoint.responses) {
        const statusCode = response.status_code || '200';
        operation.responses[statusCode] = {
          'description': response.description || 'Response',
          'content': {}
        };

        if (response.content_type) {
          operation.responses[statusCode].content[response.content_type] = {
            'schema': response.schema || {}
          };
        }
      }
    }

    // Add operation to path
    openapiData.paths[path][method] = operation;
  }

  return openapiData;
}

/**
 * Mark unstructured data as TODO
 * @param unstructuredData Unstructured data
 * @returns Minimal OpenAPI structure with TODO markers
 */
function markUnstructuredAsTodo(unstructuredData: any): any {
  return {
    'openapi': '3.0.0',
    'info': {
      'title': 'Unstructured API',
      'version': '1.0.0',
      'description': 'This API was parsed from unstructured data and requires further processing.'
    },
    'paths': {},
    'x-unstructured-data': unstructuredData
  };
}

/**
 * Convert unknown format data to OpenAPI format using generic approach
 * @param unknownData Unknown format data
 * @returns Best-effort OpenAPI conversion
 */
function convertToOpenapiGeneric(unknownData: any): any {
  // Create basic OpenAPI structure
  const openapiData: any = {
    'openapi': '3.0.0',
    'info': {
      'title': 'Generic API',
      'version': '1.0.0'
    },
    'paths': {}
  };

  // Try to extract API information
  if (typeof unknownData === 'object' && unknownData !== null) {
    // Try to find title
    if ('title' in unknownData) {
      openapiData.info.title = unknownData.title;
    } else if ('name' in unknownData) {
      openapiData.info.title = unknownData.name;
    }

    // Try to find version
    if ('version' in unknownData) {
      openapiData.info.version = unknownData.version;
    }

    // Try to find description
    if ('description' in unknownData) {
      openapiData.info.description = unknownData.description;
    }

    // Try to extract endpoints from various formats
    if ('paths' in unknownData && typeof unknownData.paths === 'object') {
      openapiData.paths = unknownData.paths;
    } else if ('endpoints' in unknownData && Array.isArray(unknownData.endpoints)) {
      // Convert endpoints to paths
      for (const endpoint of unknownData.endpoints) {
        // Skip if no path
        if (!endpoint.path) continue;

        const path = endpoint.path;
        const method = (endpoint.method || 'get').toLowerCase();

        if (!openapiData.paths[path]) {
          openapiData.paths[path] = {};
        }

        openapiData.paths[path][method] = {
          'summary': endpoint.summary || endpoint.title || '',
          'description': endpoint.description || '',
          'parameters': endpoint.parameters || []
        };
      }
    }
  }

  return openapiData;
}

/**
 * Validate OpenAPI data against specification
 * @param openapiData OpenAPI data to validate
 * @returns Whether the data is valid OpenAPI
 */
function validateOpenapi(openapiData: any): boolean {
  // Basic validation checks
  if (typeof openapiData !== 'object' || openapiData === null) {
    return false;
  }

  // Check required fields
  if (!openapiData.openapi || !openapiData.info || !openapiData.paths) {
    return false;
  }

  // Check version format
  if (!String(openapiData.openapi).match(/^3\.\d+\.\d+$/)) {
    return false;
  }

  // Check info object
  if (!openapiData.info.title || !openapiData.info.version) {
    return false;
  }

  // For a more thorough validation, we would use a JSON schema validator
  // But this basic check is sufficient for our caching purposes
  return true;
} 