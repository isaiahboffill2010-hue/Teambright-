import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white  flex flex-col items-center justify-center px-6">
      {/* Tag */}
      {/* AI AGENTS NEGOTIATING ON YOUR BEHALF */}
      {/*<div className="mb-14 border border-brand-green text-brand-green px-5 py-2 text-xs tracking-widest">
        AI AGENTS NEGOTIATING ON YOUR BEHALF
      </div>/*}

      {/* Heading */}
      <h1 className="text-center font-bold leading-tight m-0">
        <span className="block text-black text-5xl sm:text-7xl">Complaint outreach</span>
        <span className="block text-blue-500 text-5xl sm:text-7xl">clear path</span>
        <span className="block text-black text-5xl sm:text-7xl">to growth</span>
      </h1>

      {/* CTA Buttons */}
      <div className="flex flex-wrap justify-center gap-6 mt-16">
        <Link
          href="/auth?role=advisor"
          className="bg-blue-500 text-white font-semibold px-9 py-4 text-sm tracking-wide hover:opacity-90 transition-opacity"
        >
          Financial Advisor →
        </Link>
        <Link
          href="/auth?role=compliance-officer"
          className="border border-brand-gold text-brand-gold font-semibold px-9 py-4 text-sm tracking-wide hover:opacity-90 transition-opacity"
        >
          Compliance Officer →
        </Link>
      </div>
    </main>
  );
}
