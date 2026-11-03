from typing import Literal
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from .core import judge, Rejected
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
def main(): mcp.run(transport='stdio')
if __name__=='__main__':main()
