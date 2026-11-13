"""PDF extraction and corpus-specific section metadata."""
import logging
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
from .models import DocumentPage

def normalize_text(text):
    return '\n'.join(re.sub(r'[^\S\n]+', ' ', s).strip() for s in unicodedata.normalize('NFC', text).replace('\r', '').split('\n')).strip()

def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    pages=[]
    for n,p in enumerate(PdfReader(path).pages,1):
        try:
            text=normalize_text(p.extract_text() or '')
        except Exception:
            logging.error('Extraction failed: %s page %s', document_id,n)
            raise
        if not text:
            logging.warning('Empty page: %s page %s',document_id,n)
        pages.append(DocumentPage(document_id,source,n,text))
    return pages

def section_parts(page):
    n=page.page
    ranges=[(30,35,'1.2'),(36,39,'1.3'),(40,42,'1.4'),(52,60,'2.1'),(61,67,'2.2'),(68,71,'2.3'),(72,72,'2.4')]
    section=next((s for a,b,s in ranges if a<=n<=b),None)
    if section is None:
        raise ValueError(f'No section mapping for page {n}')
    # Retain content; split actual headings on mixed-section pages.
    transitions={36:('1.3 Connections between Information Systems and Information Technology','1.2','1.3'),40:('1.4 The Global Importance of Information Systems','1.3','1.4'),61:('2.2 Strategies to Improve the Value of Information Technology','2.1','2.2'),68:('2.3 Digital Business Models','2.2','2.3')}
    text=page.text
    spans=[(0,len(text),section)]
    if n in transitions:
        heading,previous,current=transitions[n]
        match=re.search(r'\s+'.join(map(re.escape,heading.split())),text)
        if not match:
            raise ValueError(f'Expected heading missing on page {n}')
        spans=[(0,match.start(),previous),(match.start(),len(text),current)]
    return [DocumentPage(page.document_id,page.source,n,text[a:b],{**page.metadata,'section':s,'part':i,'attribution':'Access for free at openstax.org.'}) for i,(a,b,s) in enumerate(spans) if text[a:b].strip()]
