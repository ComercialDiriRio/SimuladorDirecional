/**
 * Adia trabalho não crítico para depois do paint (fallback: setTimeout).
 */
export function scheduleIdle(fn, timeoutMs = 400) {
  if (typeof requestIdleCallback !== "undefined") {
    requestIdleCallback(
      () => {
        try {
          fn();
        } catch {
          /* noop */
        }
      },
      { timeout: timeoutMs }
    );
  } else {
    setTimeout(() => {
      try {
        fn();
      } catch {
        /* noop */
      }
    }, 0);
  }
}
