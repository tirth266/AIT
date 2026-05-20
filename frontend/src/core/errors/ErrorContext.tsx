import React, { createContext, useContext, useCallback, ReactNode } from 'react';
import { AppError } from './AppError';
import { ErrorTelemetry } from './ErrorTelemetry';
import { ErrorClassifier } from './ErrorClassifier';

interface ErrorContextValue {
  reportError: (error: unknown, context?: Record<string, unknown>) => AppError;
}

const ErrorContext = createContext<ErrorContextValue | undefined>(undefined);

export const ErrorProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const reportError = useCallback((error: unknown, context?: Record<string, unknown>) => {
    const classified = ErrorClassifier.classify(error);
    
    if (context) {
      Object.assign(classified.context || {}, context);
    }

    ErrorTelemetry.log(classified);
    return classified;
  }, []);

  return (
    <ErrorContext.Provider value={{ reportError }}>
      {children}
    </ErrorContext.Provider>
  );
};

export const useErrorReporting = () => {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error('useErrorReporting must be used within an ErrorProvider');
  }
  return context;
};
