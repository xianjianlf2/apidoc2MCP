/**
 * Logger utility for the application
 */

// Log level enum
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARNING = 2,
  ERROR = 3
}

// Current log level
let currentLogLevel = LogLevel.INFO;

/**
 * Initialize the logger with the specified log level
 * @param level The log level to set
 */
export function initLogger(level: LogLevel = LogLevel.INFO): void {
  currentLogLevel = level;
}

/**
 * Get the logger instance
 * @returns Logger object with logging methods
 */
export function getLogger() {
  return {
    debug: (message: string): void => {
      if (currentLogLevel <= LogLevel.DEBUG) {
        console.debug(`🔍 ${message}`);
      }
    },
    
    info: (message: string): void => {
      if (currentLogLevel <= LogLevel.INFO) {
        console.info(`ℹ️ ${message}`);
      }
    },
    
    warning: (message: string): void => {
      if (currentLogLevel <= LogLevel.WARNING) {
        console.warn(`⚠️ ${message}`);
      }
    },
    
    error: (message: string): void => {
      if (currentLogLevel <= LogLevel.ERROR) {
        console.error(`❌ ${message}`);
      }
    }
  };
}

// Export a singleton instance
export default getLogger(); 