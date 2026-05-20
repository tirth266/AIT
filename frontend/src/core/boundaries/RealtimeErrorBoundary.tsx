import React, { Component, ReactNode } from 'react';
import { ErrorClassifier, AppError } from '../errors';

interface Props {
  children: ReactNode;
}

interface State {
  error: AppError | null;
}

export class RealtimeErrorBoundary extends Component<Props, State> {
  public state: State = {
    error: null,
  };

  public static getDerivedStateFromError(error: unknown): State {
    return { error: ErrorClassifier.classify(error) };
  }

  public render() {
    if (this.state.error) {
      return (
        <div className="relative group overflow-hidden rounded-lg">
          {this.props.children}
          <div className="absolute inset-0 bg-red-900/40 backdrop-blur-[1px] flex items-center justify-center transition-opacity opacity-100">
            <div className="bg-slate-900 border border-red-500/50 p-2 rounded shadow-lg text-[10px] text-red-400 flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              REALTIME DATA SUSPENDED
              <button 
                onClick={() => this.setState({ error: null })}
                className="ml-2 hover:text-white underline"
              >
                RECONNECT
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
