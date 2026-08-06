export async function onRequest(context) {
  const url = new URL(context.request.url);
  const targetPath = url.pathname.replace(/^\/api/, '') || '/';
  const backendUrl = 'http://100.26.51.167' + targetPath + url.search;

  const modifiedHeaders = new Headers(context.request.headers);
  modifiedHeaders.set('Host', '100.26.51.167');

  return fetch(backendUrl, {
    method: context.request.method,
    headers: modifiedHeaders,
    body: ['GET', 'HEAD'].includes(context.request.method) ? null : context.request.body,
  });
}
