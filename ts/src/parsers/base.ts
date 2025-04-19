/**
 * Base Parser class
 * Abstract base class for all document parsers
 */

/**
 * Base Parser abstract class
 * Provides common functionality for all parsers
 */
export abstract class BaseParser {
  /**
   * Parse document at the given path
   * @param inputPath Document path, can be a URL or file path
   * @returns Parsed API data
   */
  abstract parse(inputPath: string): Promise<any>;

  /**
   * Extract path parameters from a URL path
   * @param path URL path with parameters (e.g., /user/{id})
   * @returns Array of parameter names
   */
  protected extractPathParams(path: string): string[] {
    const paramRegex = /{([^}]+)}/g;
    const params: string[] = [];
    let match;

    while ((match = paramRegex.exec(path)) !== null) {
      params.push(match[1]);
    }

    return params;
  }

  /**
   * Generate a reasonable operation ID from method and path
   * @param method HTTP method
   * @param path URL path
   * @returns Generated operation ID
   */
  protected generateOperationId(method: string, path: string): string {
    // Remove URL parameters and split by path segments
    const cleanPath = path.replace(/{[^}]+}/g, '');
    const segments = cleanPath.split('/').filter(s => s.length > 0);
    
    if (segments.length === 0) {
      return `${method.toLowerCase()}Root`;
    }
    
    // Generate camelCase operation ID
    let opId = method.toLowerCase();
    
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
   * Normalize URL path (replace path parameters with standard format)
   * @param path URL path
   * @returns Normalized path
   */
  protected normalizePath(path: string): string {
    // Replace various parameter formats with OpenAPI format: {paramName}
    const normalizedPath = path
      // Swagger paths: {paramName}
      // Express-style paths: :paramName
      .replace(/:([a-zA-Z0-9_]+)(?=\/|$)/g, '{$1}')
      // Sometimes parameters are marked with <param>
      .replace(/<([a-zA-Z0-9_]+)>/g, '{$1}')
      // Or with [param]
      .replace(/\[([a-zA-Z0-9_]+)\]/g, '{$1}');
    
    return normalizedPath;
  }
} 