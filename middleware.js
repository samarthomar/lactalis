// Vercel Routing Middleware: asks for a password before the demo loads.
// The password lives in the Vercel environment variable DEMO_PASSWORD (never in this repo).
// Any username is accepted; only the password is checked.

export const config = { matcher: "/:path*" };

const ask = (status, text) =>
  new Response(text, {
    status,
    headers: { "WWW-Authenticate": 'Basic realm="Demand Supply Control Tower", charset="UTF-8"', "Cache-Control": "no-store" },
  });

export default function middleware(request) {
  const expected = process.env.DEMO_PASSWORD;
  // fail closed: without a password configured, nobody gets in
  if (!expected) return new Response("Site locked: set DEMO_PASSWORD in Vercel and redeploy.", { status: 503 });

  const header = request.headers.get("authorization") || "";
  if (!header.startsWith("Basic ")) return ask(401, "Password required.");

  let decoded = "";
  try { decoded = atob(header.slice(6)); } catch { return ask(401, "Password required."); }
  const password = decoded.slice(decoded.indexOf(":") + 1);
  if (password !== expected) return ask(401, "Wrong password.");
  // no return value: the request continues to the demo
}
