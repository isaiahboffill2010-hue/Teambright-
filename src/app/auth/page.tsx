'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { createClient } from '@/lib/supabase/client';

type Role = 'advisor' | 'compliance-officer';

const ROLE_LABELS: Record<Role, string> = {
  advisor: 'Financial Advisor',
  'compliance-officer': 'Compliance Officer',
};

const ROLE_REDIRECT: Record<Role, string> = {
  advisor: '/dashboard',
  'compliance-officer': '/review',
};

function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();

  const initialRole = (searchParams.get('role') as Role) ?? 'advisor';
  const [role, setRole] = useState<Role>(initialRole);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        const existingRole = session.user.user_metadata?.role as Role | undefined;
        if (!existingRole) {
          await supabase.auth.updateUser({ data: { role } });
        }
        router.push(ROLE_REDIRECT[existingRole ?? role] ?? '/dashboard');
      }
    });

    return () => subscription.unsubscribe();
  }, [role, router, supabase]);

  const accentColor = role === 'advisor' ? '#3b82f6' : '#f5a623';
  const accentDark = role === 'advisor' ? '#2563eb' : '#d97706';

  return (
    <main className="min-h-screen bg-white flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-md">
        {/* Heading */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-black mb-1">AdvisorFlow</h1>
          <p className="text-slate-500 text-sm">AI-powered compliance for financial advisors</p>
        </div>

        {/* Role selector */}
        <div className="flex rounded-lg overflow-hidden border border-slate-200 mb-6">
          {(['advisor', 'compliance-officer'] as Role[]).map((r) => (
            <button
              key={r}
              onClick={() => setRole(r)}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                role === r
                  ? r === 'advisor'
                    ? 'bg-blue-500 text-white'
                    : 'bg-brand-gold text-white'
                  : 'bg-white text-slate-500 hover:text-black'
              }`}
            >
              {ROLE_LABELS[r]}
            </button>
          ))}
        </div>

        {/* Supabase Auth UI */}
        <div className="bg-white rounded-xl p-6 border border-slate-200">
          <Auth
            supabaseClient={supabase}
            appearance={{
              theme: ThemeSupa,
              variables: {
                default: {
                  colors: {
                    brand: accentColor,
                    brandAccent: accentDark,
                    inputBackground: '#ffffff',
                    inputBorder: '#e2e8f0',
                    inputText: '#0f172a',
                    inputPlaceholder: '#94a3b8',
                    messageText: '#64748b',
                    anchorTextColor: accentColor,
                    dividerBackground: '#e2e8f0',
                  },
                  radii: {
                    borderRadiusButton: '6px',
                    inputBorderRadius: '6px',
                  },
                },
              },
              style: {
                button: { fontWeight: '600' },
                container: { color: '#0f172a' },
                label: { color: '#64748b', fontSize: '12px' },
                anchor: { color: accentColor },
              },
            }}
            providers={[]}
            redirectTo={`${typeof window !== 'undefined' ? window.location.origin : ''}/auth/callback`}
          />
        </div>
      </div>
    </main>
  );
}

export default function AuthPage() {
  return (
    <Suspense>
      <AuthForm />
    </Suspense>
  );
}
