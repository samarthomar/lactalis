// Vercel Routing Middleware: a password page in front of the demo.
// The password lives in the Vercel environment variable DEMO_PASSWORD (never in this repo).
// After the right password, a signed cookie lets the page load for 30 seconds only,
// so every new visit, tab or refresh asks for the password again.

export const config = { matcher: "/:path*" };

const COOKIE = "dsct_pass";
const PASS_SECONDS = 30;
const UNLOCK = "/__unlock";

const enc = new TextEncoder();
async function sign(secret, text) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(text)));
  return Array.from(mac, b => b.toString(16).padStart(2, "0")).join("");
}
function sameText(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
function readCookie(request, name) {
  const all = request.headers.get("cookie") || "";
  for (const part of all.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return v.join("=");
  }
  return "";
}

const page = (message = "") => new Response(`<!doctype html>
<html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Demand Supply Control Tower</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px; background: #F6F2EA; color: #29251D;
         font-family: "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif; }
  form { width: 100%; max-width: 360px; background: #fff; border: 1px solid #E9E4DA; border-radius: 14px; padding: 28px;
         box-shadow: 0 4px 16px rgba(41,37,29,.08); display: flex; flex-direction: column; gap: 12px; }
  .bar { width: 40px; height: 6px; background: #E31837; border-radius: 3px; }
  h1 { font-size: 20px; margin: 0; }
  p { margin: 0; color: #7A746A; font-size: 14px; }
  label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; font-weight: 600; color: #4A453D; }
  input { font: inherit; padding: 10px 12px; border: 1px solid #E5DFD3; border-radius: 8px; }
  input:focus { outline: 2px solid #E31837; border-color: #E31837; }
  button { font: inherit; font-weight: 600; padding: 11px; border: 0; border-radius: 8px; background: #E31837; color: #fff; cursor: pointer; }
  .err { color: #B3122B; font-size: 13px; font-weight: 600; min-height: 1em; }
</style></head><body>
<form method="post" action="${UNLOCK}" autocomplete="off">
  <div class="bar"></div>
  <h1>Demand Supply Control Tower</h1>
  <p>Tech Mahindra · Prepared for Lactalis Australia. Enter the password to open the demo.</p>
  <label>Password<input type="password" name="password" autofocus required></label>
  <div class="err" role="alert">${message}</div>
  <button type="submit">Open the demo</button>
</form></body></html>`, {
  status: 401,
  headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" },
});

export default async function middleware(request) {
  const secret = process.env.DEMO_PASSWORD;
  // fail closed: without a password configured, nobody gets in
  if (!secret) return new Response("Site locked: set DEMO_PASSWORD in Vercel and redeploy.", { status: 503, headers: { "Cache-Control": "no-store" } });

  const url = new URL(request.url);

  if (url.pathname === UNLOCK) {
    if (request.method !== "POST") return Response.redirect(new URL("/", url), 303);
    let given = "";
    try { given = String((await request.formData()).get("password") || ""); } catch { /* empty form */ }
    if (!sameText(given, secret)) return page("Wrong password. Try again.");
    const until = Math.floor(Date.now() / 1000) + PASS_SECONDS;
    const value = `${until}.${await sign(secret, String(until))}`;
    return new Response(null, {
      status: 303,
      headers: {
        Location: "/",
        "Cache-Control": "no-store",
        "Set-Cookie": `${COOKIE}=${value}; Max-Age=${PASS_SECONDS}; Path=/; HttpOnly; Secure; SameSite=Strict`,
      },
    });
  }

  const [until, mac] = readCookie(request, COOKIE).split(".");
  const fresh = until && Number(until) >= Date.now() / 1000;
  if (fresh && mac && sameText(mac, await sign(secret, until))) return; // let the demo load
  return page();
}
