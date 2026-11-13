"""Persistent pgvector exact cosine search; no fallback."""
import math
import psycopg
from psycopg.types.json import Jsonb
from .models import Chunk

class PgVectorStore:
    def __init__(self,database_url:str,dimensions:int):
        if type(dimensions) is not int or not 1<=dimensions<=16000: raise ValueError('Invalid dimensions')
        self.database_url=database_url
        self.dimensions=dimensions
    def _vector(self,v):
        if len(v)!=self.dimensions or not any(v) or any(type(x) not in (float,int) or not math.isfinite(x) for x in v): raise ValueError('Invalid vector')
        return '['+','.join(str(float(x)) for x in v)+']'
    def create_schema(self):
        with psycopg.connect(self.database_url,connect_timeout=5) as c:
            c.execute('CREATE EXTENSION IF NOT EXISTS vector')
            c.execute(f'CREATE TABLE IF NOT EXISTS day6_chunks (strategy text NOT NULL,chunk_id text NOT NULL,document_id text NOT NULL,source text NOT NULL,page integer NOT NULL,text text NOT NULL,metadata jsonb NOT NULL,embedding vector({self.dimensions}) NOT NULL,PRIMARY KEY(strategy,chunk_id))')
            typ=c.execute("SELECT format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid='day6_chunks'::regclass AND attname='embedding'").fetchone()[0]
            if typ!=f'vector({self.dimensions})': raise ValueError('Existing schema dimensions differ')
    def upsert(self,strategy:str,chunks:list[Chunk],vectors:list[list[float]]):
        # Full snapshot replacement, atomic per strategy, removes obsolete IDs.
        if strategy not in ('A','B','C') or not chunks or len(chunks)!=len(vectors): raise ValueError('Invalid strategy or batch')
        if len({x.chunk_id for x in chunks})!=len(chunks): raise ValueError('Duplicate IDs')
        rows=[(strategy,x.chunk_id,x.document_id,x.source,x.page,x.text,Jsonb(x.metadata),self._vector(v)) for x,v in zip(chunks,vectors)]
        with psycopg.connect(self.database_url,connect_timeout=5) as c:
            c.execute('SELECT pg_advisory_xact_lock(6006)')
            c.execute('DELETE FROM day6_chunks WHERE strategy=%s',(strategy,))
            with c.cursor() as cur: cur.executemany('INSERT INTO day6_chunks VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)',rows)
    def count(self,strategy):
        with psycopg.connect(self.database_url,connect_timeout=5) as c:
            return c.execute('SELECT count(*) FROM day6_chunks WHERE strategy=%s',(strategy,)).fetchone()[0]
    def search(self,strategy,query_vector,top_k=3,filters=None):
        if strategy not in ('A','B','C') or type(top_k) is not int or top_k<1: raise ValueError('Invalid search')
        filters=filters or {}
        if set(filters)-{'section','language','year'}: raise ValueError('Unsupported filter')
        v=self._vector(query_vector)
        with psycopg.connect(self.database_url,connect_timeout=5) as c:
            rows=c.execute('SELECT chunk_id,document_id,source,page,text,metadata,1-(embedding <=> %s::vector) FROM day6_chunks WHERE strategy=%s AND metadata @> %s ORDER BY embedding <=> %s::vector,chunk_id LIMIT %s',(v,strategy,Jsonb(filters),v,top_k)).fetchall()
        return [dict(zip(('chunk_id','document_id','source','page','text','metadata','score'),r)) for r in rows]
