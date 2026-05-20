import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorClassifier, ErrorTelemetry, AppError } from '../errors';

interface Props {
  children: ReactNode;
  title?: string;
}

interface State {
  error: AppError | null;
}

export class WidgetErrorBoundary extends Component<Props, State> {
  public state: State = {
    error: null,
  };

  public static getDerivedStateFromError(error: unknown): State {
    return { error: ErrorClassifier.classify(error) };
  }

  public componentDidCatch(error: unknown, errorInfo: ErrorInfo) {
    const classified = ErrorClassifier.classify(error);
    ErrorTelemetry.log(classified);
    console.error(`Widget crash [${this.props.title || 'Unknown'}]:`, error, errorInfo);
  }

  public render() {
    if (this.state.error) {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-center">
          <div className="text-red-500 mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-slate-300 mb-1">
            {this.props.title || 'Widget'} Failed
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            className="text-xs text-blue-400 hover:text-blue-300 underline"
          >
            Reset Widget
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
