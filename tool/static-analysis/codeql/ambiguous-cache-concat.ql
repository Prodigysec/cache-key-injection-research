/**
 * @name Multiple request flows through an unseparated APR join to a cache key
 * @description Candidate only: verify distinct variable-length fields and reachable key use.
 * @kind problem
 * @problem.severity warning
 * @id cache-key-research/ambiguous-apr-join
 */
import CacheKeyFlow

from FunctionCall join, int i, int j, DataFlow::Node a, DataFlow::Node b, DataFlow::Node sink
where
  join.getTarget().hasName("apr_pstrcat") and i >= 1 and j = i + 1 and
  a != b and CacheKeyConfig::isSource(a) and CacheKeyConfig::isSource(b) and
  CacheFlow::flow(a, DataFlow::exprNode(join.getArgument(i))) and
  CacheFlow::flow(b, DataFlow::exprNode(join.getArgument(j))) and
  not join.getArgument(i) instanceof StringLiteral and
  not join.getArgument(j) instanceof StringLiteral and
  CacheKeyConfig::isKeySink(sink) and
  TaintTracking::localTaint(DataFlow::exprNode(join), sink)
select join, "Two distinct modeled request sources are adjacent in an APR concatenation reaching cache-key material; manual review required."
