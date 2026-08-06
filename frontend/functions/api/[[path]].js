export async function onRequest(context) {
  const url = new URL(context.request.url);
  const targetPath = url.pathname.replace(/^\/api/, '') || '/';
  const backendUrl = 'http://100.26.51.167' + targetPath + url.search;

  const response = await fetch(backendUrl, {
    method: context.request.method,
    headers: {
      'Accept': 'application/json, text/plain, */*',
      'Content-Type': context.request.headers.get('Content-Type') || 'application/json',
    },
    body: ['GET', 'HEAD'].includes(context.request.method) ? null : context.request.body,
  });

  const resHeaders = new Headers(response.headers);
  resHeaders.set('Access-Control-Allow-Origin', '*');
  return new Response(response.body, {
    status: response.status,
    headers: resHeaders,
  });
}
