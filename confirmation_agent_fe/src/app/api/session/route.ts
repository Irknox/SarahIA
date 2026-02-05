import { NextResponse } from "next/server";
import { SignJWT } from "jose";

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "una_clave_secreta_muy_larga_y_segura_123",
);

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { access_key } = body;
    console.log("Intento de autenticación con clave:", access_key, "encontrada en env:", process.env.ACCESS_KEY);
    
    if (access_key === process.env.ACCESS_KEY) {
      const jwt = await new SignJWT({ role: "admin" }) 
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("24h") 
        .sign(JWT_SECRET);

      const response = NextResponse.json({ authenticated: true });
      response.cookies.set("session_token", jwt, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        path: "/",
        maxAge: 60 * 60 * 24,
        sameSite: "lax",
      });

      return response;
    }
    return NextResponse.json(
      { error: "Credenciales inválidas" },
      { status: 401 },
    );
  } catch (error) {
    return NextResponse.json(
      { error: "Error en el servidor" },
      { status: 500 },
    );
  }
}
