import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "una_clave_secreta_muy_larga_y_segura_123",
);

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("session_token")?.value;
  const isLoginPage = pathname.includes("/Login") || pathname === "/";

  if (!isLoginPage) {
    if (!token) {
      return NextResponse.redirect(
        new URL("/SchedulerAgent/Login", request.url),
      );
    }

    try {
      await jwtVerify(token, JWT_SECRET);
      return NextResponse.next();
    } catch (error) {
      const response = NextResponse.redirect(
        new URL("/SchedulerAgent/Login", request.url),
      );
      response.cookies.delete("session_token");
      return response;
    }
  }

  if (isLoginPage && token) {
    try {
      await jwtVerify(token, JWT_SECRET);
      return NextResponse.redirect(
        new URL("/SchedulerAgent/CallsStatusLogger", request.url),
      );
    } catch (error) {
      return NextResponse.next();
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
