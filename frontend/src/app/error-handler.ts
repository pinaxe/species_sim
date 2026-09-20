// Global error handler to suppress browser extension errors
if (typeof window !== 'undefined') {
  const originalError = window.onerror;

  window.onerror = function (message, url, line, column, error) {
    // Suppress MetaMask and other extension connection errors
    if (
      typeof message === 'string' &&
      (message.includes('MetaMask') ||
        message.includes('chrome-extension') ||
        message.includes('Failed to connect') ||
        message.includes('Object.connect'))
    ) {
      console.debug('Extension error suppressed:', message);
      return true; // Suppress the error
    }

    // Call original error handler for other errors
    if (originalError) {
      return originalError(message, url, line, column, error);
    }

    return false;
  };

  // Also suppress unhandled promise rejections from extensions
  window.addEventListener('unhandledrejection', (event) => {
    if (
      event.reason &&
      typeof event.reason === 'object' &&
      'message' in event.reason &&
      typeof event.reason.message === 'string'
    ) {
      const message = event.reason.message;
      if (message.includes('MetaMask') || message.includes('connect')) {
        console.debug('Extension rejection suppressed:', message);
        event.preventDefault();
      }
    }
  });
}
