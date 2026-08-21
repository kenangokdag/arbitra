"use client";

import { NavigationProvider } from "@/lib/navigation-context";
import { ChatboxPanel } from "./ChatboxPanel";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { PaywallModal } from "./PaywallModal";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <NavigationProvider>
      <div className="min-h-screen bg-white">
        <Topbar />
        <div className="flex">
          <Sidebar />
          <main className="min-w-0 flex-1 overflow-y-auto" style={{ height: "calc(100vh - 60px)" }}>
            <div className="mx-auto max-w-[1200px] px-6 pb-16 pt-6 md:px-8">
              {children}
            </div>
          </main>
        </div>
        <PaywallModal />
        <ChatboxPanel />
      </div>
    </NavigationProvider>
  );
}
