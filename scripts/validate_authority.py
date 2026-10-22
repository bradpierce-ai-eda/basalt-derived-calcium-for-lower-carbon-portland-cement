import json, hashlib, re, unicodedata
from bs4 import BeautifulSoup
import pymupdf
def validate_authority(root):
 a=json.loads((root/'source/paper.json').read_text());s=json.loads((root/'source/supplement.json').read_text());z=json.loads((root/'source/zenodo-metadata.json').read_text());inv=json.loads((root/'source/invariants.json').read_text());m=z['metadata']
 assert hashlib.sha256((root/'source/zenodo-metadata.json').read_bytes()).hexdigest()==inv['zenodo_metadata_sha256'],'frozen Zenodo metadata hash'
 assert a['title']==m['title']==a['blocks'][0]['text'],'title authority'
 assert a['subtitle']==m['additional_titles'][0]['title']==a['blocks'][1]['text'],'subtitle authority'
 expected=[]
 for c in m['creators']:
  p=c['person_or_org'];expected.append({'name':p['given_name']+' '+p['family_name'],'given':p['given_name'],'family':p['family_name'],'orcid':'https://orcid.org/'+next(i['identifier'] for i in p['identifiers'] if i['scheme']=='orcid')})
 assert a['authors']==expected==s['authors'],'actual human creator and ORCID authority'
 assert a['publication_date']==m['publication_date']==s['publication_date'],'publication date authority'
 assert a['doi']==z['pids']['doi']['identifier']==s['doi'],'version DOI authority'
 assert a['concept_doi']==z['parent']['pids']['doi']['identifier']==s['concept_doi'],'concept DOI authority'
 assert a['zenodo_record']==z['links']['self_html']==s['zenodo_record'],'record URL authority'
 assert a['abstract']==BeautifulSoup(m['description'],'html.parser').get_text()==a['blocks'][6]['text'],'complete abstract authority'
 assert a['keywords']==[x['subject'] for x in m['subjects'] if 'id' not in x]==a['blocks'][7]['text'].removeprefix('Keywords: ').split(', '),'ordered keywords authority'
 assert a['rights']==m['copyright']==s['rights'],'copyright authority'
 assert a['license'].lower()==m['rights'][0]['id']==s['license'].lower(),'license authority'
 compact=lambda x:re.sub(r'\s+','',unicodedata.normalize('NFC',x).replace('\u2060',''))
 for key,record in [('paper',a),('supplement',s)]:
  digest=hashlib.sha256(json.dumps(record['blocks'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  assert digest==record['canonical_blocks_sha256']==inv['canonical_blocks_sha256' if key=='paper' else 'supplement_blocks_sha256'],'frozen '+key+' block hash'
  path=root/record['pdf_filename'];entry=z['files']['entries'][path.name]
  assert path.stat().st_size==entry['size'] and 'md5:'+hashlib.md5(path.read_bytes()).hexdigest()==entry['checksum'],'deposited '+key+' PDF identity'
  doc=pymupdf.open(path);text='\n'.join(p.get_text() for p in doc)
  text=re.sub(r'^\d+\s*$','',re.sub(r'© 2026 Brad Pierce\s*·\s*CC BY-NC 4\.0','',text),flags=re.M);text=compact(text);cursor=0
  for b in record['blocks']:
   for chunk in ([v for row in b['rows'] for v in row] if b['type']=='table' else [b.get('text','')]):
    if not chunk:continue
    pos=text.find(compact(chunk),cursor);assert pos>=0,'ordered '+key+' paragraph/table cell against exact deposited PDF: '+chunk[:80];
    if b['type']!='table':cursor=pos+len(compact(chunk))
