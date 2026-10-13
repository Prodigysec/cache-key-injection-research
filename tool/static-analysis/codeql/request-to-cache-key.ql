/**
 * @name Request data reaches a cache-key hash input
 * @description A dataflow lead requiring boundary and source-control review.
 * @kind problem
 * @problem.severity recommendation
 * @id cache-key-research/request-to-key
 */
import CacheKeyFlow

from DataFlow::Node source, DataFlow::Node sink
where CacheKeyConfig::isKeySink(sink) and CacheFlow::flow(source, sink)
select sink.asExpr(), "Request-derived value reaches key material from $@; inspect framing before claiming a collision.", source.asExpr(), "request field"
