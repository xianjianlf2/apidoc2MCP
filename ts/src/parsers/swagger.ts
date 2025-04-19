/**
 * Swagger Parser
 * Parses API documentation in Swagger 2.0 format
 */

import axios from 'axios';
import * as fs from 'fs-extra';
import * as yaml from 'js-yaml';
import logger from '../utils/logger';
import { BaseParser } from './base';

/**
 * Swagger Parser class
 * Parses API documentation in Swagger 2.0 format
 */
export class SwaggerParser extends BaseParser {
  /**
   * Parse document at the given path
   * @param inputPath Document path, can be a URL or file path
   * @returns Parsed API data
   */
  async parse(inputPath: string): Promise<any> {
    logger.info(`📙 Parsing Swagger document at ${inputPath}`);

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

      // Validate that it's a Swagger document
      if (!data.swagger || data.swagger !== '2.0') {
        logger.warning('⚠️ Document does not appear to be a Swagger 2.0 specification');
      }

      // Return the parsed Swagger document
      return data;
    } catch (e) {
      const error = e as Error;
      logger.error(`❌ Swagger parsing error: ${error.message}`);
      throw error;
    }
  }
} 