import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorClassifier, ErrorTelemetry, AppError, ErrorRecovery } from '../errors';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onRecover?: () => void;
}

interface State {
  error: AppError | null;
  isRecovering: boolean;
}

export class GlobalErrorBoundary extends Component<Props, State> {
  public state: State = {
    error: null,
    isRecovering: false,
  };

  public static getDerivedStateFromError(error: unknown): State {
    return { error: ErrorClassifier.classify(error), isRecovering: false };
  }

  public componentDidCatch(error: unknown, errorInfo: ErrorInfo) {
    const classified = ErrorClassifier.classify(error);
    ErrorTelemetry.log(classified);
    console.error('Uncaught error:', error, errorInfo);
  }

  private handleRetry = async () => {
    if (!this.state.error) return;

    this.setState({ isRecovering: true });
    const recovered = await ErrorRecovery.recover(this.state.error);

    if (recovered) {
      this.setState({ error: null, isRecovering: false });
      this.props.onRecover?.();
    } else {
      this.setState({ isRecovering: false });
    }
  };

  public render() {
    if (this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-white p-6">
          <div className="max-w-md w-full bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-8 text-center">
            <div className="w-16 h-16 bg-red-500/20 text-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold mb-4">Application Error</h1>
            <p className="text-slate-400 mb-6">
              Something went wrong. The system is attempting to recover or you can try refreshing the page.
            </p>
            <div className="bg-slate-900/50 rounded p-4 mb-6 text-left overflow-auto max-h-40">
              <code className="text-xs text-red-400">
                [{this.state.error.code}] {this.state.error.message}
              </code>
            </div>
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 rounded-md font-medium transition-colors"
              >
                Reload Page
              </button>
              <button
                onClick={this.handleRetry}
                disabled={this.state.isRecovering}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-md font-medium transition-colors"
              >
                {this.state.isRecovering ? 'Recovering...' : 'Try Again'}
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
