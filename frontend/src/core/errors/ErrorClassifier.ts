import { ErrorCode, ErrorSeverity } from './ErrorCodes';
import { AppError } from './AppError';

export class ErrorClassifier {
  public static classify(error: unknown): AppError {
    if (error instanceof AppError) {
      return error;
    }

    if (error instanceof Error) {
      // Chunk load errors (Vite/Webpack)
      if (
        error.message.includes('Failed to fetch dynamically imported module') ||
        error.message.includes('Loading chunk')
      ) {
        return new AppError('Failed to load application component', {
          code: ErrorCode.CHUNCK_LOAD_FAILURE,
          severity: 'high',
          recoverable: true,
        });
      }

      // Network errors
      if (error.message.includes('Network Error') || !window.navigator.onLine) {
        return new AppError('Network connectivity lost', {
          code: ErrorCode.NETWORK_ERROR,
          severity: 'high',
          recoverable: true,
        });
      }

      return new AppError(error.message, {
        code: ErrorCode.RENDER_FAILURE,
        severity: 'medium',
        recoverable: true,
        context: { originalError: error.name },
      });
    }

    return new AppError(String(error), {
      code: ErrorCode.UNKNOWN_ERROR,
      severity: 'medium',
      recoverable: true,
    });
  }

  public static getSeverity(code: ErrorCode): ErrorSeverity {
    switch (code) {
      case ErrorCode.STORE_CORRUPTION:
      case ErrorCode.RISK_LIMIT_EXCEEDED:
      case ErrorCode.UNAUTHORIZED:
        return 'critical';
      case ErrorCode.NETWORK_ERROR:
      case ErrorCode.WEBSOCKET_CONNECTION_FAILED:
      case ErrorCode.CHUNCK_LOAD_FAILURE:
        return 'high';
      default:
        return 'medium';
    }
  }
}
