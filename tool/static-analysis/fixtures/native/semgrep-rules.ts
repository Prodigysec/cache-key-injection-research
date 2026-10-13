function vulnerable(req: any, cache: any) {
  const a = req.path;
  const b = req.headers['accept'];
  const key = a + b;
  // ruleid: cache-key-js-no-delimiter
  cache.get(key);
  // ruleid: cache-key-js-no-delimiter
  cache.set(`${a}${b}`, 'value');
  // ruleid: cache-key-js-weak-delimiter
  cache.delete(a + '|' + b);
  // ruleid: cache-key-js-weak-delimiter
  cache.get(`${a}:${b}`);
  // ruleid: cache-key-js-no-delimiter
  cache.get(crypto.createHash('sha256').update(a + b).digest('hex'));
  // ruleid: cache-key-js-no-delimiter
  unstable_cache(() => 'value', [a + b]);
}
function safe(req: any, cache: any) {
  const a = req.query.tenant;
  const b = req.cookies.user;
  // ok: cache-key-js-no-delimiter, cache-key-js-weak-delimiter
  cache.get(a + a);
  // ok: cache-key-js-no-delimiter, cache-key-js-weak-delimiter
  cache.get(JSON.stringify([a, b]));
  // ok: cache-key-js-no-delimiter, cache-key-js-weak-delimiter
  cache.get(crypto.createHash('sha256').update(a).digest('hex') + crypto.createHash('sha256').update(b).digest('hex'));
  // ok: cache-key-js-no-delimiter, cache-key-js-weak-delimiter
  cache.get(encodeURIComponent(a) + '|' + encodeURIComponent(b));
  // ok: cache-key-js-no-delimiter, cache-key-js-weak-delimiter
  cache.get(a + 'fixed-suffix');
  // ok: cache-key-js-no-delimiter, cache-key-js-weak-delimiter
  cache.set('fixed-key', a + b);
}
function koa(ctx: any, cache: any) {
  // ruleid: cache-key-js-no-delimiter
  cache.get(ctx.request.url + ctx.request.headers['accept']);
}
function fastify(request: any, redis: any) {
  // ruleid: cache-key-js-no-delimiter
  redis.get(request.query.tenant + request.headers['accept']);
}
