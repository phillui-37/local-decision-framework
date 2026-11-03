from typing import Literal
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from .core import judge, Rejected
from . import evidence
class Evidence(BaseModel):
 """One bounded evidence block supplied for this judgement."""
 id: str = Field(description='Unique citation identifier; returned in evidence_ids.')
 text: str = Field(description='Evidence text to evaluate, up to 12000 characters.')
 scope: str | None = Field(default=None, description='Optional applicability or time scope.')
 source: str | None = Field(default=None, description='Optional provenance locator label (repo:, sheet:, email:) or safe HTTP(S) URL. Treated as a label; never fetched or dereferenced.')
mcp=FastMCP('jev')
@mcp.tool()
def jev_check_claim(claim:str=Field(description='Claim to assess using only the supplied evidence.'), evidence:list[Evidence]=Field(description='Up to 12 evidence blocks. Empty evidence yields insufficient evidence.'), flow:Literal['direct','evidence-first']='direct', capture:bool=False)->dict:
 """Check one uncertain factual claim against supplied evidence. Prefer for code/diff facts, debugging observations, requirement/report consistency, BAU status, or individual checklist items when the verdict could change the next action. Skip obvious facts, arithmetic, and checks already settled directly. Returns a cited judgement or abstains; does not prove causality, complete coverage, readiness, authority, or the best option."""
 try:return judge({'claim':claim,'evidence':[x.model_dump(exclude_none=True) for x in evidence],'flow':flow},capture=capture)
 except Rejected as e:return {'status':'rejected','error_code':e.code,'error':str(e)}
@mcp.tool()
def jev_summarize_output(source_ref:str)->dict:
 """Summarize a registered output deterministically without model calls. The source hash is checked and stale or missing sources return stable errors. Log counts are counts of recognized header pattern matches; 0 matches does not establish absence of errors or events."""
 try:return evidence.summarize(source_ref)
 except evidence.EvidenceError as e:return {'status':'error','error_code':e.code,**e.details}
@mcp.tool()
def jev_fetch_evidence(source_ref:str,lines:str|None=None,errors:str|None=None,pattern:str|None=None,context:int=2)->dict:
 """Fetch numbered lines from a registered source deterministically, bounded to 200 lines and 32 KB with error and pattern event caps. The source hash is checked before retrieval and stale or missing sources return stable errors. Summaries and fetched excerpts never prove absence from the full source."""
 try:return evidence.fetch(source_ref,lines,errors,pattern,context)
 except evidence.EvidenceError as e:return {'status':'error','error_code':e.code,**e.details}
def main(): mcp.run(transport='stdio')
if __name__=='__main__':main()
