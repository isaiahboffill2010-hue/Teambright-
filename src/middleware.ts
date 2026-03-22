import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  // Protected routes — redirect to auth if not signed in
  const advisorRoutes = ['/dashboard', '/prospects', '/outreach', '/compliance', '/templates', '/tax-planning'];
  const complianceRoutes = ['/review'];

  const isAdvisorRoute = advisorRoutes.some((r) => pathname.startsWith(r));
  const isComplianceRoute = complianceRoutes.some((r) => pathname.startsWith(r));

  if (!user && (isAdvisorRoute || isComplianceRoute)) {
    const role = isComplianceRoute ? 'compliance-officer' : 'advisor';
    const url = request.nextUrl.clone();
    url.pathname = '/auth';
    url.searchParams.set('role', role);
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|auth|api|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
