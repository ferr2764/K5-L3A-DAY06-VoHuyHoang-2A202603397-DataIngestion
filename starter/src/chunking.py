"""Deterministic chunks with source offsets."""
import hashlib
import re
from .models import Chunk,DocumentPage

def _chunk(page,text,a,b,method):
    key=f'{page.document_id}:{page.page}:{page.metadata.get("part",0)}:{method}:{a}:{b}:{text}'
    return Chunk(hashlib.sha256(key.encode()).hexdigest(),page.document_id,page.source,page.page,text,{**page.metadata,'start':a,'end':b,'method':method})

def fixed_size(page:DocumentPage,size:int,overlap:int)->list[Chunk]:
    if size<=0 or not 0<=overlap<size:
        raise ValueError('Require size > 0 and 0 <= overlap < size')
    chunks=[]
    for a in range(0,len(page.text),size-overlap):
        b=min(a+size,len(page.text))
        if page.text[a:b].strip():
            chunks.append(_chunk(page,page.text[a:b],a,b,f'fixed-{size}-{overlap}'))
        if b==len(page.text): break
    return chunks

def by_paragraph(page:DocumentPage,max_size:int)->list[Chunk]:
    if max_size<=0: raise ValueError('max_size must be positive')
    # PDF wraps are not paragraphs: prefer blank lines, bullets and sentence ends.
    boundaries=[0]+[m.end() for m in re.finditer(r'\n\s*\n|(?<=[.!?:])\n|\n(?=\d+\. )',page.text)]+[len(page.text)]
    spans=[]
    start=end=0
    for a,b in zip(boundaries,boundaries[1:]):
        if b-start>max_size and end>start:
            spans.append((start,end)); start=a
        while b-start>max_size:
            cut=page.text.rfind(' ',start+max_size//2,start+max_size)
            cut=cut+1 if cut>=0 else start+max_size
            spans.append((start,cut)); start=cut
        end=b
    if end>start: spans.append((start,end))
    return [_chunk(page,page.text[a:b],a,b,f'paragraph-{max_size}') for a,b in spans if page.text[a:b].strip()]
