/**
 * The API always returns errors in the same envelope:
 *   { success: false, error: { code, message, details }, request_id }
 * These helpers turn that into something a component can render.
 */

export const getErrorMessage = (error, fallback = 'Something went wrong. Please try again.') => {
  if (!error) return fallback;
  if (typeof error === 'string') return error;

  const payload = error.data ?? error.response?.data ?? error;
  if (payload?.error?.message) return payload.error.message;
  if (payload?.detail) return payload.detail;

  // DRF field errors that escaped the envelope, e.g. { email: ["..."] }
  const details = payload?.error?.details ?? payload;
  if (details && typeof details === 'object') {
    const first = Object.values(details).find(
      (value) => Array.isArray(value) && value.length > 0,
    );
    if (first) return String(first[0]);
  }

  return error.message || fallback;
};

export const getFieldErrors = (error) => {
  const payload = error?.data ?? error?.response?.data ?? {};
  const details = payload?.error?.details;
  if (!details || typeof details !== 'object') return {};

  return Object.entries(details).reduce((accumulator, [field, messages]) => {
    accumulator[field] = Array.isArray(messages) ? messages.join(' ') : String(messages);
    return accumulator;
  }, {});
};

/**
 * Push server-side field errors into a react-hook-form instance so they appear
 * beneath the offending input rather than only in a toast.
 */
export const applyFieldErrors = (error, setError) => {
  const fields = getFieldErrors(error);
  Object.entries(fields).forEach(([field, message]) => {
    setError(field, { type: 'server', message });
  });
  return Object.keys(fields).length > 0;
};
