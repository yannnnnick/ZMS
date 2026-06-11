import { useCallback, useState } from "react";
import { ApiError } from "../api";

export interface MutationState {
  isSubmitting: boolean;
  error: string | null;
  /**
   * Runs an async mutation while guarding against concurrent/duplicate submits.
   * Returns true on success and false if the action threw, so callers can decide
   * whether to reset a form or keep the user's input for a retry.
   */
  run: (action: () => Promise<unknown>) => Promise<boolean>;
  clearError: () => void;
}

export function useMutation(): MutationState {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (action: () => Promise<unknown>): Promise<boolean> => {
    setIsSubmitting(true);
    setError(null);
    try {
      await action();
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Aktion fehlgeschlagen");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { isSubmitting, error, run, clearError };
}
