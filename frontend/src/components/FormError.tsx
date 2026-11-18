/** An error from the API, shown as the API wrote it. Announced to screen readers. */
export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="rounded border border-red-300 bg-red-50 px-3 py-2 text-red-900"
    >
      {message}
    </p>
  );
}
