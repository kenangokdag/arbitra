import { AppShell } from "@/components/AppShell";

export const metadata = { title: "Arbitra" };

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
