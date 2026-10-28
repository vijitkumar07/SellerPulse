"""Compare logical contents from two isolated same-seed SQLite runs."""
import hashlib, json, os, sqlite3, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
 c=sqlite3.connect(path)
 try:
  result={}
  tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  for t in tables:
   cols=[r[1] for r in c.execute(f'PRAGMA table_info("{t}")')]
   rows=c.execute(f'SELECT * FROM "{t}" ORDER BY '+', '.join('"'+x+'"' for x in cols)).fetchall()
   result[t]={'columns':cols,'rows':rows}
  raw=json.dumps(result,sort_keys=True,default=str,separators=(',',':')).encode()
  return hashlib.sha256(raw).hexdigest(),{t:len(v['rows']) for t,v in result.items()}
 finally: c.close()
with tempfile.TemporaryDirectory(prefix='sellerpulse_repro_') as d:
 hashes=[]; counts=[]
 for label in ('a','b'):
  db=str(Path(d)/(label+'.db')); env=os.environ.copy(); env['SELLERPULSE_DATABASE_PATH']=db
  p=subprocess.run([sys.executable,'-m','backend.app.seed','--scale','starter','--seed','4242'],cwd=ROOT,env=env,text=True,capture_output=True)
  if p.returncode: print(p.stdout); print(p.stderr); raise SystemExit('FAIL: isolated seed run failed')
  h,n=digest(db); hashes.append(h); counts.append(n); print(f'{label}: {h}')
 if hashes[0]==hashes[1] and counts[0]==counts[1]: print('PASS: identical logical data in two isolated same-seed runs.'); print(counts[0])
 else: print('FAIL: runs differ',counts); raise SystemExit(1)
