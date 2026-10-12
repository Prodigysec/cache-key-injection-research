/** @name Cache key function extraction inventory
 * @description Verify that key construction functions survived extraction.
 * @kind table
 * @id cache-key-research/extraction-inventory
 */
import cpp
from Function f
where f.getName() in ["cache_generate_key_default", "cache_canonicalise_key", "ngx_http_proxy_create_key", "ngx_http_file_cache_create_key", "HSH_AddString", "VRT_hashdata"]
select f.getFile().getRelativePath(), f.getName(), f.getNumberOfParameters()
