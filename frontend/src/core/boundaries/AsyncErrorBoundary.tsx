import React, { Component, ReactNode, Suspense } from 'react';
import { ErrorClassifier, AppError, ErrorCode } from '../errors';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: AppError | null;
}

export class AsyncErrorBoundary extends Component<Props, State> {
  public state: State = {
    error: null,
  };

  public static getDerivedStateFromError(error: unknown): State {
    return { error: ErrorClassifier.classify(error) };
  }

  private handleRetry = () => {
    this.setState({ error: null });
  };

  public render() {
    if (this.state.error) {
      const isChunkError = this.state.error.code === ErrorCode.CHUNCK_LOAD_FAILURE;

      return (
        <div className="p-6 bg-slate-800 border border-slate-700 rounded-lg text-center">
          <h3 className="text-lg font-bold text-white mb-2">
            {isChunkError ? 'Component Load Failure' : 'Something went wrong'}
          </h3>
          <p className="text-slate-400 mb-4">
            {isChunkError 
              ? 'Failed to download application parts. This usually happens after an update.' 
              : 'An unexpected error occurred while loading this section.'}
          </p>
          <button
            onClick={isChunkError ? () => window.location.reload() : this.handleRetry}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium transition-colors"
          >
            {isChunkError ? 'Refresh Application' : 'Retry'}
          </button>
        </div>
      );
    }

    return <Suspense fallback={this.props.fallback || <div className="animate-pulse bg-slate-800 h-40 rounded-lg w-full" />}>{this.props.children}</Suspense>;
  }
}
