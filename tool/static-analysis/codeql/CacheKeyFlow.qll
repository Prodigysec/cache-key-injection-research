/** Request-to-cache flow model. This is not a proof of boundary ambiguity. */
import cpp
import semmle.code.cpp.dataflow.new.DataFlow
import semmle.code.cpp.dataflow.new.TaintTracking

module CacheKeyConfig implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    exists(FieldAccess field |
      source.asExpr() = field and
      field.getTarget().getName() in ["uri", "unparsed_uri", "args", "query", "headers_in", "url"] and
      field.getQualifier().toString().regexpMatch("(r|req|sp)(->|\\.).*|r|req|sp")
    )
    or
    exists(FunctionCall call |
      source.asExpr() = call and
      (call.getTarget().getName() in ["VRT_r_req_url", "VRT_GetHdr"] or
       call.getTarget().hasName("apr_table_get") and call.getArgument(0).toString().matches("%headers_in%"))
    )
  }

  predicate isKeySink(DataFlow::Node sink) {
    exists(FunctionCall call, int index |
      (call.getTarget().getName() in ["ngx_md5_update", "VSHA256_Update"] and index = 1
       or call.getTarget().hasName("HSH_AddString") and index = 2) and
      sink.asExpr() = call.getArgument(index)
    )
    or
    exists(AssignExpr assignment |
      assignment.getEnclosingFunction().getName() in ["cache_generate_key_default", "cache_canonicalise_key"] and
      assignment.getLValue().toString().regexpMatch(".*key.*") and
      sink.asExpr() = assignment.getRValue()
    )
  }

  predicate isSink(DataFlow::Node sink) {
    isKeySink(sink) or
    exists(FunctionCall join |
      join.getTarget().hasName("apr_pstrcat") and
      (sink.asExpr() = join or sink.asExpr() = join.getAnArgument())
    )
  }

  predicate isAdditionalFlowStep(DataFlow::Node before, DataFlow::Node after) {
    exists(FunctionCall call, int i |
      call.getTarget().getName() in ["apr_pstrcat", "apr_psprintf"] and i >= 1 and
      before.asExpr() = call.getArgument(i) and after.asExpr() = call
    )
    or
    exists(FunctionCall call, int i |
      call.getTarget().getName() in ["ngx_sprintf", "ngx_snprintf", "ngx_slprintf"] and i >= 2 and
      before.asExpr() = call.getArgument(i) and after.asExpr() = call.getArgument(0)
    )
  }
}

module CacheFlow = TaintTracking::Global<CacheKeyConfig>;
