export function Hint({ children }: { children: React.ReactNode }) {
  return (
    <div
      role="status"
      className="mb-[18px] rounded-md border border-[#F1DEB3] bg-[#FFF8E9] px-3.5 py-2.5 text-[13px] text-[#7C4F12]"
    >
      {children}
    </div>
  );
}
