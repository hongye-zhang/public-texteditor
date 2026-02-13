// This file handles the Chrome DevTools JSON request
// It returns an empty JSON object to prevent 404 errors in the console

/** @type {import('./$types').RequestHandler} */
export function GET() {
  return new Response(JSON.stringify({}), {
    headers: {
      'Content-Type': 'application/json'
    }
  });
}
