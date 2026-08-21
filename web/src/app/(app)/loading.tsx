export default function Loading() {
  return (
    <div role="status" aria-busy="true" aria-live="polite" className="space-y-3">
      <div className="h-8 w-1/3 animate-pulse rounded-md bg-bg-soft" />
      <div className="h-4 w-2/3 animate-pulse rounded-md bg-bg-soft" />
      <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-[10px] border border-rule bg-bg-card" />
        ))}
      </div>
      <span className="sr-only">Yükleniyor…</span>
    </div>
  );
}
