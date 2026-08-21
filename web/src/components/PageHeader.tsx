export function PageHeader({
  title,
  lede,
}: {
  title: string;
  lede?: string;
}) {
  return (
    <header className="mb-[22px]">
      <h1 className="serif mb-1.5 mt-1 text-[28px] font-medium italic leading-tight tracking-[-0.015em]">
        {title}
      </h1>
      {lede ? <p className="max-w-[720px] text-[14px] leading-relaxed text-ink-mute">{lede}</p> : null}
    </header>
  );
}
