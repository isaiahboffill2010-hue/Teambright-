import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AdvisorFlow — Financial Advisor Outreach Platform',
  description: 'FINRA-compliant outreach, tax planning, and compliance management for financial advisors.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  );
}
