import { AppError } from './AppError';

export class ErrorTelemetry {
  public static log(error: AppError): void {
    const errorData = error.toJSON();

    // In a real production app, this would send to Sentry, LogRocket, or a custom ELK endpoint.
    console.error(`[TELEMETRY][${error.severity.toUpperCase()}] ${error.code}: ${error.message}`, {
      context: error.context,
      timestamp: error.timestamp,
      stack: error.stack,
    });

    // Example: Integration with a hypothetical monitoring service
    if (error.severity === 'critical') {
      this.notifyUrgent(error);
    }
  }

  private static notifyUrgent(error: AppError): void {
    // Send to high-priority alert system
    console.warn(`[URGENT] Critical system failure detected: ${error.code}`);
  }
}
