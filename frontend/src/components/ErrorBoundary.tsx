'use client';

import React, { ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Suppress MetaMask and extension errors silently
    if (error.message?.includes('MetaMask') || error.message?.includes('connect')) {
      console.debug('Extension error suppressed:', error.message);
      return { hasError: false };
    }
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Suppress MetaMask connection errors
    if (!error.message?.includes('MetaMask')) {
      console.error('Application error:', error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError && this.state.error && !this.state.error.message?.includes('MetaMask')) {
      return (
        <div className="flex items-center justify-center h-screen bg-red-50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h1>
            <p className="text-red-700 mb-4">{this.state.error.message}</p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
