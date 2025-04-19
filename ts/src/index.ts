#!/usr/bin/env node
/**
 * apidoc2MCP main program
 * For converting API documentation to MCP services
 */

import { Command } from 'commander';
import { runPipeline } from './pipeline';
import { getLogger, initLogger } from './utils/logger';

// Initialize logger
initLogger();
const logger = getLogger();

/**
 * Main program entry point
 */
async function main() {
  const program = new Command();

  program
    .name('apidoc2mcp')
    .description('Convert API documentation to MCP services')
    .version('1.0.0')
    .argument('<input>', 'Input document path, can be a URL or file path')
    .option('--format <format>', 'Input document format', /^(swagger|openapi|markdown|html|auto)$/i, 'auto')
    .option('--output <path>', 'Output directory', './O_MCP_SERVER_LIST')
    .option('--name <name>', 'MCP service name, if specified, will be used as service name and added to output directory');

  program.parse(process.argv);

  const options = program.opts();
  const input = program.args[0];

  try {
    // Use pipeline to execute complete conversion process
    const [success, outputDir, metrics] = await runPipeline(
      input,
      options.format,
      options.output,
      options.name
    );

    // Return exit code based on execution result
    process.exit(success ? 0 : 1);
  } catch (e) {
    const error = e as Error;
    logger.error(`❌ Error: ${error.message}`);
    logger.debug(error.stack || "No stack trace available");
    process.exit(1);
  }
}

// Run main function if this script is executed directly
if (require.main === module) {
  main().catch(error => {
    console.error(`Unhandled error: ${error.message}`);
    process.exit(1);
  });
}

export { runPipeline } from './pipeline';
