/**
 * OpenAPI Parser
 * Parses API documentation in OpenAPI 3.x format
 */

import axios from 'axios';
import * as fs from 'fs-extra';
import * as yaml from 'js-yaml';
import { getLogger } from '../utils/logger';
import { BaseParser } from './base';

const logger = getLogger();
/**
 * OpenAPI Parser class
 * Parses API documentation in OpenAPI 3.x format
 */
export class OpenAPIParser extends BaseParser {
  /**
   * Parse document at the given path
   * @param inputPath Document path, can be a URL or file path
   * @returns Parsed API data
   */

  async parse(inputPath: string): Promise<any> {
    logger.info(`📘 Parsing OpenAPI document at ${inputPath}`);

    try {
      // Read content from file or URL
      let content: string;
      if (inputPath.startsWith('http://') || inputPath.startsWith('https://')) {
        const response = await axios.get(inputPath);
        content = response.data;
        
        // If response is already an object (JSON API), return it
        if (typeof content === 'object') {
          return content;
        }
      } else {
        content = await fs.readFile(inputPath, 'utf-8');
      }

      // Parse JSON or YAML
      let data: any;
      try {
        if (inputPath.toLowerCase().endsWith('.json')) {
          data = JSON.parse(content);
        } else {
          data = yaml.load(content);
        }
      } catch (e) {
        logger.error(`❌ Failed to parse document content: ${(e as Error).message}`);
        throw e;
      }

      // Validate that it's an OpenAPI document
      if (!data.openapi || !data.openapi.startsWith('3.')) {
        logger.warning('⚠️ Document does not appear to be an OpenAPI 3.x specification');
      }

      // Return the parsed OpenAPI document
      return data;
    } catch (e) {
      const error = e as Error;
      logger.error(`❌ OpenAPI parsing error: ${error.message}`);
      throw error;
    }
  }
} 