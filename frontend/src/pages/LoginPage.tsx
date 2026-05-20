import React from 'react';
import { AngelOneLoginForm } from '../components/AngelOneLoginForm';

export const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
            Trading Platform
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Professional algorithmic trading interface
          </p>
        </div>
        <AngelOneLoginForm />
      </div>
    </div>
  );
};
