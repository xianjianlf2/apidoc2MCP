/**
 * MCP service generation pipeline
 * Integrates parsers, converters and generators to provide a complete
 * API documentation to MCP service conversion workflow
 */

import * as path from 'path';
import { convertToStandardFormat } from './converters';
import { generateMcpService } from './generators';
import { parseDocument } from './parsers';
import logger from './utils/logger';

/**
 * Metrics about the pipeline execution
 */
interface PipelineMetrics {
  parseTime: number;
  convertTime: number;
  generateTime: number;
  totalTime: number;
  endpointsCount: number;
  incompleteEndpoints: number;
}

/**
 * MCP service generation pipeline class
 */
export class MCPPipeline {
  private outputDir: string;
  private metrics: PipelineMetrics;

  /**
   * Initialize the MCP pipeline
   * @param outputDir Default output directory
   */
  constructor(outputDir: string = "./O_MCP_SERVER_LIST") {
    this.outputDir = outputDir;
    this.metrics = {
      parseTime: 0,
      convertTime: 0,
      generateTime: 0,
      totalTime: 0,
      endpointsCount: 0,
      incompleteEndpoints: 0
    };
  }

  /**
   * Run the complete MCP service generation pipeline
   * @param inputPath Input document path, can be a URL or file path
   * @param format Input document format, can be 'swagger', 'openapi', 'markdown', 'auto'
   * @param serviceName MCP service name, if specified, will be used as service name and added to output directory
   * @returns Tuple of (success, output directory path, metrics data)
   */
  async run(
    inputPath: string, 
    format: string = "auto", 
    serviceName?: string
  ): Promise<[boolean, string | null, PipelineMetrics]> {
    const startTime = Date.now();

    try {
      // 1. Parse phase
      logger.info(`📄 [1/3] Parsing document: ${inputPath}, format: ${format}`);
      const parseStart = Date.now();
      const apiData = await this._parse(inputPath, format);
      const parseEnd = Date.now();
      this.metrics.parseTime = (parseEnd - parseStart) / 1000;

      if (!apiData) {
        logger.error("❌ Document parsing failed, process terminated");
        return [false, null, this.metrics];
      }

      // 2. Convert phase
      logger.info("🔄 [2/3] Converting to OpenAPI standard format...");
      const convertStart = Date.now();
      const standardFormat = await this._convert(apiData);
      const convertEnd = Date.now();
      this.metrics.convertTime = (convertEnd - convertStart) / 1000;

      if (!standardFormat) {
        logger.error("❌ Format conversion failed, process terminated");
        return [false, null, this.metrics];
      }

      // 3. Process service name
      const outputDir = this._processServiceName(standardFormat, serviceName);

      // 4. Generate phase
      logger.info(`🚀 [3/3] Generating MCP service to: ${outputDir}`);
      const generateStart = Date.now();
      const [success, generatorMetrics] = await this._generate(standardFormat, outputDir);
      const generateEnd = Date.now();
      this.metrics.generateTime = (generateEnd - generateStart) / 1000;

      // Update metrics
      this.metrics = { ...this.metrics, ...generatorMetrics };
      this.metrics.totalTime = (Date.now() - startTime) / 1000;

      if (success) {
        logger.info(`✅ MCP service generation complete, written to directory: ${outputDir}`);
        this._showMetrics();
        this._showStartupGuide(outputDir);
        return [true, outputDir, this.metrics];
      } else {
        logger.error("❌ MCP service generation failed");
        return [false, outputDir, this.metrics];
      }
    } catch (e) {
      const error = e as Error;
      logger.error(`❌ Pipeline execution error: ${error.message}`);
      logger.debug(error.stack || "No stack trace available");

      this.metrics.totalTime = (Date.now() - startTime) / 1000;
      return [false, null, this.metrics];
    }
  }

  /**
   * Parse phase
   * @param inputPath Input document path
   * @param format Document format
   * @returns Parsed API data
   */
  private async _parse(inputPath: string, format: string): Promise<any> {
    try {
      return await parseDocument(inputPath, format);
    } catch (e) {
      const error = e as Error;
      logger.error(`❌ Parse phase error: ${error.message}`);
      return null;
    }
  }

  /**
   * Convert phase
   * @param apiData API data to convert
   * @returns Standard format data
   */
  private async _convert(apiData: any): Promise<any> {
    try {
      return await convertToStandardFormat(apiData);
    } catch (e) {
      const error = e as Error;
      logger.error(`❌ Convert phase error: ${error.message}`);
      return null;
    }
  }

  /**
   * Process service name
   * @param standardFormat Standard format data
   * @param serviceName Service name
   * @returns Output directory path
   */
  private _processServiceName(standardFormat: any, serviceName?: string): string {
    let outputDir: string;

    if (serviceName) {
      logger.info(`🏷️ Using specified service name: ${serviceName}`);
      
      // Set service name
      if (!standardFormat.title) {
        standardFormat.title = serviceName;
      } else {
        standardFormat.originalTitle = standardFormat.title;
        standardFormat.title = serviceName;
      }

      // Add service name to output directory
      outputDir = path.join(this.outputDir, serviceName);
    } else {
      // Try to get service name from standard format
      if (standardFormat.title && typeof standardFormat.title === 'string') {
        const serviceTitle = standardFormat.title.replace(/\s+/g, '_').toLowerCase();
        outputDir = path.join(this.outputDir, serviceTitle);
        logger.info(`🏷️ Using API title as service name: ${serviceTitle}`);
      } else {
        outputDir = this.outputDir;
      }
    }

    // Handle Windows paths
    if (process.platform === 'win32') {
      outputDir = outputDir.replace(/\\/g, '/');
    }
    
    return outputDir;
  }

  /**
   * Generate phase
   * @param standardFormat Standard format data
   * @param outputDir Output directory
   * @returns Tuple of (success, metrics)
   */
  private async _generate(standardFormat: any, outputDir: string): Promise<[boolean, Partial<PipelineMetrics>]> {
    try {
      const success = await generateMcpService(standardFormat, outputDir);

      // Get generated information
      const metrics: Partial<PipelineMetrics> = {
        endpointsCount: 0,
        incompleteEndpoints: 0
      };

      // If OpenAPI format, count endpoints from paths
      if (standardFormat.paths) {
        let endpointCount = 0;
        for (const pathItem of Object.values(standardFormat.paths)) {
          const pathObj = pathItem as any;
          for (const method of ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']) {
            if (method in pathObj) {
              endpointCount += 1;
            }
          }
        }
        metrics.endpointsCount = endpointCount;
      } else if (standardFormat.endpoints) {
        metrics.endpointsCount = standardFormat.endpoints.length;
      }

      return [success, metrics];
    } catch (e) {
      const error = e as Error;
      logger.error(`❌ Generate phase error: ${error.message}`);
      return [false, {}];
    }
  }

  /**
   * Show performance metrics
   */
  private _showMetrics(): void {
    // Combine metrics data into a single info log
    logger.info(
      "\n📊 Pipeline execution metrics:" +
      `\nTotal execution time: ${this.metrics.totalTime.toFixed(2)} seconds` +
      `\nParse phase: ${this.metrics.parseTime.toFixed(2)} seconds` +
      `\nConvert phase: ${this.metrics.convertTime.toFixed(2)} seconds` +
      `\nGenerate phase: ${this.metrics.generateTime.toFixed(2)} seconds` +
      `\nTotal endpoints: ${this.metrics.endpointsCount}`
    );
  }

  /**
   * Show startup guide
   * @param outputDir Output directory
   */
  private _showStartupGuide(outputDir: string): void {
    const mcpServerPath = path.join(outputDir, 'mcp_server.js');
    // Handle Windows paths
    const formattedPath = process.platform === 'win32' ? 
      mcpServerPath.replace(/\\/g, '/') : 
      mcpServerPath;

    logger.info(
      `\n🚀 Start MCP service:\n
1. Run the generated JavaScript file
> node ${formattedPath}

2. Use MCP CLI tool to run tests
> mcp dev ${formattedPath}

3. Customize API base URL with environment variables
> API_BASE_URL=https://your-api-base-url node ${formattedPath}`
    );
  }
}

/**
 * Convenience function to run the MCP service generation pipeline
 * @param inputPath Input document path, can be a URL or file path
 * @param format Input document format, can be 'swagger', 'openapi', 'markdown', 'auto'
 * @param outputDir Output directory
 * @param serviceName MCP service name, if specified, will be used as service name and added to output directory
 * @returns Tuple of (success, output directory path, metrics data)
 */
export async function runPipeline(
  inputPath: string, 
  format: string = "auto", 
  outputDir: string = "./O_MCP_SERVER_LIST", 
  serviceName?: string
): Promise<[boolean, string | null, PipelineMetrics]> {
  const pipeline = new MCPPipeline(outputDir);
  return await pipeline.run(inputPath, format, serviceName);
} 