# Public source: https://github.com/varnishcache/varnish-cache/blob/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e/bin/varnishd/builtin.vcl
# Exact vcl_hash and vcl_builtin_hash excerpt (BSD-2-Clause).
sub vcl_hash {
	call vcl_builtin_hash;
	return (lookup);
}

sub vcl_builtin_hash {
	hash_data(req.url);
	if (req.http.host) {
		hash_data(req.http.host);
	} else {
		hash_data(server.ip);
	}
}

