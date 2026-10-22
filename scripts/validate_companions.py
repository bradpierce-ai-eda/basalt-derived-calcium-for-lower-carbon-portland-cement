from pathlib import Path
import json, hashlib, zipfile, subprocess, sys, tempfile
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
def validate_companions(root):
 root=Path(root);s=json.loads((root/'source/supplement.json').read_text());inv=json.loads((root/'source/invariants.json').read_text())
 page=BeautifulSoup((root/'supplement.html').read_text(),'html.parser');nodes=page.select('[data-block]')
 assert [int(x['data-block']) for x in nodes]==list(range(len(s['blocks'])))
 normal=lambda x:' '.join(x.split())
 for b,n in zip(s['blocks'],nodes):
  if b['type']=='figure':assert n.img['src']==b['asset'] and n.img['alt']==b['alt']
  elif b['type']=='table':assert [[normal(c.get_text()) for c in row.find_all(['td','th'],recursive=False)] for row in n.find_all('tr')]==[[normal(c) for c in row] for row in b['rows']]
  else:
   assert normal(n.get_text())==normal(b['text'])
   if b['type']=='heading':assert n.name=='h'+str(min(b['level']+1,6)),'supplement heading role'
 assert 'Manuscript date:' not in page.get_text(),'supplement has no manuscript date field'
 md=BeautifulSoup(MarkdownIt('commonmark').enable('table').render((root/'supplement.md').read_text()),'html.parser')
 def semantic(n):
  if n.name=='table':return ('table',[[normal(c.get_text()) for c in row.find_all(['td','th'],recursive=False)] for row in n.find_all('tr')])
  if n.find('img'):return ('figure',n.img['src'],n.img['alt'])
  return ('text',normal(n.get_text()))
 assert [semantic(n) for n in md.find_all(recursive=False)]==[semantic(n) for n in nodes]
 assert len(page.select('table'))==3 and len(page.select('figure'))==2
 assert not page.select('meta[name^="citation_"]'),'Supplement must not masquerade as a second scholarly record'
 for a in page.select('a[href*="#ref-"]'):assert a['href'].startswith('./#ref-') and 1<=int(a['href'].split('#ref-')[1])<=15
 for name,record in inv['companions'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==record['sha256'] and (root/name).stat().st_size==record['bytes']
 with zipfile.ZipFile(root/'basalt-derived-calcium-calculation-package.zip') as z:
  assert z.testzip() is None
  entries={p.split('/',1)[1]:z.read(p) for p in z.namelist() if not p.endswith('/')}
 actual={str(p.relative_to(root/'calculation')):p.read_bytes() for p in (root/'calculation').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 # The generated run report is not part of the published input package.
 actual.pop('results/publication-verification.json',None)
 assert actual==entries,'Extracted runnable package must exactly equal the deposited ZIP'
 with tempfile.TemporaryDirectory() as td:
  with zipfile.ZipFile(root/'basalt-derived-calcium-calculation-package.zip') as z:z.extractall(td)
  p=Path(td)/'basalt-derived-calcium-calculation-package'
  x=subprocess.run([sys.executable,'-B',str(p/'verify_publication.py')],cwd=td,capture_output=True,text=True)
  assert x.returncode==0,x.stderr
 return {'status':'PASS','supplement_blocks':len(s['blocks']),'tables':3,'figures':2,'extracted_files':len(entries),'replay':x.stdout.strip()}
if __name__=='__main__':print(json.dumps(validate_companions(Path(__file__).resolve().parents[1]),indent=2))
