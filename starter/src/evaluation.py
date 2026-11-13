"""Evidence matching does not infer human coherence or grounding labels."""
from collections import defaultdict
import unicodedata

def _norm(t): return ' '.join(unicodedata.normalize('NFC',t).split())

def evaluate_query(question,hits):
    golds=[question]+question.get('alternative_gold',[])
    flags=[any(h['document_id']==g['gold_source_id'] and h['page']==g['gold_page'] and _norm(g['evidence_quote']) in _norm(h['text']) for g in golds) for h in hits[:3]]
    return {**question,'hits':hits[:3],'evidence_matches':flags,'hit_at_1':bool(flags and flags[0]),'hit_at_3':any(flags),'scoring':'literal; equivalent evidence needs human audit'}

def summarize(traces):
    groups=defaultdict(list)
    for t in traces: groups[t['strategy'],t['split']].append(t)
    return [dict(strategy=s,split=p,total=len(ts),hit_at_1_n=sum(t['hit_at_1'] for t in ts),hit_at_3_n=sum(t['hit_at_3'] for t in ts),hit_at_1=sum(t['hit_at_1'] for t in ts)/len(ts),hit_at_3=sum(t['hit_at_3'] for t in ts)/len(ts)) for (s,p),ts in sorted(groups.items())]
