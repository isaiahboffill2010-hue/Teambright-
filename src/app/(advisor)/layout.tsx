import { Sidebar } from '@/components/layout/Sidebar';

export default function AdvisorLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar role="advisor" />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
