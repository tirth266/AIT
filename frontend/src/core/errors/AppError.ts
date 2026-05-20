import { ErrorCode, ErrorSeverity } from './ErrorCodes';

export class AppError extends Error {
  public readonly code: ErrorCode;
  public readonly severity: ErrorSeverity;
  public readonly recoverable: boolean;
  public readonly context?: Record<string, unknown>;
  public readonly timestamp: string;

  constructor(
    message: string,
    options: {
      code?: ErrorCode;
      severity?: ErrorSeverity;
      recoverable?: boolean;
      context?: Record<string, unknown>;
    } = {}
  ) {
    super(message);
    this.name = 'AppError';
    this.code = options.code || ErrorCode.UNKNOWN_ERROR;
    this.severity = options.severity || 'medium';
    this.recoverable = options.recoverable ?? true;
    this.context = options.context;
    this.timestamp = new Date().toISOString();

    // Fix prototype chain for custom Error in TS
    Object.setPrototypeOf(this, AppError.prototype);

    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, AppError);
    }
  }

  public toJSON() {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      severity: this.severity,
      recoverable: this.recoverable,
      context: this.context,
      timestamp: this.timestamp,
      stack: this.stack,
    };
  }
}
