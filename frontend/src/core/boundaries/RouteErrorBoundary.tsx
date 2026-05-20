import React, { Component, ReactNode } from 'react';
import { useRouteError, isRouteErrorResponse } from 'react-router-dom';

export const RouteErrorBoundary: React.FC = () => {
  const error = useRouteError();
  console.error('Route error:', error);

  let title = 'Navigation Error';
  let message = 'Failed to load the requested page.';

  if (isRouteErrorResponse(error)) {
    if (error.status === 404) {
      title = 'Page Not Found';
      message = "The page you're looking for doesn't exist.";
    } else if (error.status === 401) {
      title = 'Unauthorized';
      message = 'You do not have permission to view this page.';
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] p-8 text-white">
      <div className="text-slate-500 mb-6">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-20 w-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 20l-6-6m0 0l6-6m-6 6h18" />
        </svg>
      </div>
      <h2 className="text-3xl font-bold mb-4">{title}</h2>
      <p className="text-slate-400 mb-8">{message}</p>
      <button
        onClick={() => window.history.back()}
        className="px-8 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg font-medium transition-all"
      >
        Go Back
      </button>
    </div>
  );
};
