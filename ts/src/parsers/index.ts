/**
 * API document parser module
 * Supports parsing different formats of API documents
 */

import axios from "axios";
import * as fs from "fs-extra";
import * as yaml from "js-yaml";
import { getLogger } from "../utils/logger";
import { CrawlerParser } from "./crawler";
import { MarkdownParser } from "./markdown";
import { OpenAPIParser } from "./openapi";
import { SwaggerParser } from "./swagger";

/**
 * Parse an API document
 * @param inputPath Document path, can be a URL or file path
 * @param formatType Document format, can be 'swagger', 'openapi', 'markdown', 'html', or 'auto'
 * @returns Parsed API data
 */
const logger = getLogger();
export async function parseDocument(
  inputPath: string,
  formatType: string = "auto"
): Promise<any> {
  // Select appropriate parser based on document format
  if (formatType === "auto") {
    // Auto-detect document format
    formatType = await detectFormat(inputPath);
  }

  const parserMap: Record<string, any> = {
    swagger: SwaggerParser,
    openapi: OpenAPIParser,
    markdown: MarkdownParser,
    html: CrawlerParser,
    crawler: CrawlerParser,
  };

  if (!(formatType in parserMap)) {
    logger.warning(
      `⚠️ Unsupported document format: ${formatType}, trying crawler parser`
    );
    formatType = "crawler";
  }

  logger.info(`📄 Using ${formatType} parser to parse document`);
  const ParserClass = parserMap[formatType];
  const parser = new ParserClass();

  try {
    // Parse document
    const result = await parser.parse(inputPath);

    // Check if parsing was successful
    if (
      result &&
      ((typeof result === "object" &&
        ("paths" in result || "endpoints" in result)) ||
        (Array.isArray(result) && result.length > 0))
    ) {
      logger.info(`✅ Successfully parsed document using ${formatType} format`);
      return result;
    } else {
      // If parsing result is empty, try using crawler parser
      if (formatType !== "crawler") {
        logger.warning(
          `⚠️ ${formatType} parser result is empty, trying crawler parser`
        );
        const crawler = new CrawlerParser();
        const crawlerResult = await crawler.parse(inputPath);

        // Check if crawler parsing was successful
        if (
          crawlerResult &&
          "paths" in crawlerResult &&
          Object.keys(crawlerResult.paths).length > 0
        ) {
          logger.info("✅ Successfully parsed document using crawler");
          return crawlerResult;
        }
      }

      logger.warning("⚠️ Parse result is empty");
      return result;
    }
  } catch (e) {
    const error = e as Error;
    logger.error(`❌ Error parsing document: ${error.message}`);

    // If not crawler parsing, try using crawler parser
    if (formatType !== "crawler") {
      logger.info("🔄 Trying to parse document using crawler");
      try {
        const crawler = new CrawlerParser();
        const crawlerResult = await crawler.parse(inputPath);

        // Check if crawler parsing was successful
        if (
          crawlerResult &&
          "paths" in crawlerResult &&
          Object.keys(crawlerResult.paths).length > 0
        ) {
          logger.info("✅ Successfully parsed document using crawler");
          return crawlerResult;
        }
      } catch (crawlerError) {
        logger.error(
          `❌ Crawler parsing error: ${(crawlerError as Error).message}`
        );
      }
    }

    // Re-throw original exception
    throw error;
  }
}

/**
 * Auto-detect document format
 * @param inputPath Document path
 * @returns Detected document format
 */
export async function detectFormat(inputPath: string): Promise<string> {
  // Determine document format based on file extension or content
  if (
    inputPath.toLowerCase().endsWith(".json") ||
    inputPath.toLowerCase().endsWith(".yaml") ||
    inputPath.toLowerCase().endsWith(".yml")
  ) {
    // Try to distinguish between Swagger and OpenAPI
    try {
      let content: string;
      let data: any;

      // Load document content
      if (inputPath.startsWith("http://") || inputPath.startsWith("https://")) {
        const response = await axios.get(inputPath);
        content = response.data;
      } else {
        content = await fs.readFile(inputPath, "utf-8");
      }

      // Parse content
      if (inputPath.toLowerCase().endsWith(".json")) {
        data = JSON.parse(content);
      } else {
        data = yaml.load(content);
      }

      // Check if Swagger 2.0
      if ("swagger" in data && data.swagger === "2.0") {
        return "swagger";
      }

      // Check if OpenAPI 3.x
      if ("openapi" in data && data.openapi.startsWith("3.")) {
        return "openapi";
      }

      // Return default value
      return "openapi";
    } catch (e) {
      // Parsing failed, return default value
      return "openapi";
    }
  } else if (inputPath.toLowerCase().endsWith(".md")) {
    return "markdown";
  } else if (
    inputPath.toLowerCase().endsWith(".html") ||
    inputPath.toLowerCase().endsWith(".htm")
  ) {
    return "html";
  } else if (
    inputPath.startsWith("http://") ||
    inputPath.startsWith("https://")
  ) {
    // For URLs, try to detect content type
    try {
      const response = await axios.head(inputPath);
      const contentType = response.headers["content-type"] || "";

      if (contentType.includes("json")) {
        // Try to get and parse JSON
        const jsonResponse = await axios.get(inputPath);
        const data = jsonResponse.data;

        // Check if Swagger 2.0 or OpenAPI 3.x
        if ("swagger" in data && data.swagger === "2.0") {
          return "swagger";
        } else if ("openapi" in data && data.openapi.startsWith("3.")) {
          return "openapi";
        }

        return "openapi";
      } else if (contentType.includes("text/html")) {
        return "html";
      } else if (contentType.includes("text/markdown")) {
        return "markdown";
      }
    } catch (e) {
      // If detection fails, default to crawler parsing
      return "crawler";
    }
  }

  // Default to using crawler to try parsing
  return "crawler";
}
