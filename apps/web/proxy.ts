import { NextResponse, type NextRequest } from "next/server";

// Optymistyczne sprawdzenie: tylko obecność ciasteczka sesji ustawionego przez API (w prod z
// Domain=.example.com, więc widoczne także tutaj). O ważności sesji decyduje API (401 -> /login).
const SESSION_COOKIE = process.env.SESSION_COOKIE_NAME ?? "ce_session";
const PUBLIC_PATHS = ["/login", "/register"];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const hasSession = request.cookies.has(SESSION_COOKIE);

  if (!isPublic && !hasSession) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|webp|ico|css|js)$).*)"],
};
