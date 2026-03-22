import { Sidebar } from '@/components/layout/Sidebar';

export default function OfficerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar role="compliance_officer" />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
