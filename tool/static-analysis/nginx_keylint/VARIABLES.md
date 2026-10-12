# Variable model and boundary scores

Definitions are from [Nginx core embedded variables](https://nginx.org/en/docs/http/ngx_http_core_module.html#variables) and [proxy module variables](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#variables). Charset and control columns are conservative analysis assumptions, not promises made by those docs.

| Variable | Attacker influence | Bounded charset model | Variable length | Definition/source |
|---|---|---|---|---|
| $request_uri | yes | unknown | yes | Original URI with arguments; core variables |
| $uri | yes | unknown | yes | Normalized URI, may change internally; core variables |
| $args / $arg_* | yes | unknown | yes | Request arguments; core variables |
| $http_* | yes | unknown | yes | Request headers; core variables |
| $cookie_* | yes | unknown | yes | Cookie values; core variables |
| $scheme | transport selection | h,t,p,s | yes (http/https) | Request scheme; core variables |
| $host | request or configured fallback | unknown | yes | Request-line host, Host header, server-name fallback; core variables |
| $proxy_host | configuration (dynamic proxy_pass needs review) | unknown | yes | Name and port of proxied server; proxy variables |
| $server_port | listener selection | digits | yes | Server accepting port; core variables |
| $request_method | yes | HTTP token characters (conservative) | yes | Request method; core variables |
| $is_args | depends on args | ? or empty | yes | ? if arguments present, empty otherwise; core variables |
| custom / map / set variables | unknown | unknown | unknown | Not resolved by this linter |

NONE means confirmed unframed *construction*, not a confirmed exploitable collision. Even scheme/http and https are constrained, equal fixed-length fields can be unambiguously split, and sources can be dependent (uri/is_args/args). WEAK recognizes common separators | : / - when a strong bound cannot be proved. STRONG requires a character excluded by both modeled charsets. UNKNOWN means further modeling is needed, not safe. The current model deliberately does not infer normalization, map/set definitions, include expansion, cache enablement or variable correlations. Crossplane parses one file without following includes, making public snippets and the lab reproducible without system configuration files.
