export const withRetry = async <T>(
  fn: () => Promise<T>,
  retries: number = 3,
  delay: number = 1000,
  shouldRetry: (error: any) => boolean = () => true
): Promise<T> => {
  let attempt = 0;
  while (attempt < retries) {
    try {
      return await fn();
    } catch (error: any) {
      attempt++;
      if (attempt >= retries || !shouldRetry(error)) {
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  throw new Error('Retry failed');
};
