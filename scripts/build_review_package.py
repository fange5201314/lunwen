"""Generate review documents and a portable, source-inclusive release archive."""
from pathlib import Path
import importlib.util,json,subprocess,http.server,threading,functools,zipfile,hashlib
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'deliverables/v2.0'
spec=importlib.util.spec_from_file_location('renderer',OUT/'research/render_documents.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
for name in ['开发实施方案-v3.0','运行与验证']:
 text=(ROOT/'docs'/f'{name}.md').read_text();body,toc=renderer.convert(text)
 doc=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name}</title><style>{renderer.style}</style><main><div class="tag">THESIS ATELIER / DEVELOPMENT v3.0</div><p><a href="../开始评审.html">返回评审入口</a></p>{body}</main></html>'
 (ROOT/'docs'/f'{name}.html').write_text(doc)
# Pinned Archify rendering; output path must match its declared relative meta.output.
source=json.loads((ROOT/'config/runtime-architecture.json').read_text())
source['meta']['output']='开发验证架构.html'
source_path=OUT/'开发验证架构源.json';source_path.write_text(json.dumps(source,ensure_ascii=False,indent=2))
import os
archify=Path(os.environ.get('THESIS_ARCHIFY_DIR',ROOT/'.tools/archify'))
subprocess.run(['node',str(archify/'archify/bin/archify.mjs'),'render','architecture',str(source_path),'开发验证架构.html'],cwd=OUT,check=True,timeout=90)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(server.server_address[1])
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'],env={'XDG_CONFIG_HOME':'/tmp/package-pw-config','XDG_CACHE_HOME':'/tmp/package-pw-cache'})
 page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 for rel in ['docs/开发实施方案-v3.0','docs/运行与验证','deliverables/v2.0/111重点资源融合方案']:
  page.goto(base+'/'+rel+'.html');page.wait_for_load_state('networkidle');page.evaluate('document.fonts.ready')
  assert page.locator('h1').count()==1
  page.pdf(path=str(ROOT/(rel+'.pdf')),print_background=True,prefer_css_page_size=True)
 page.goto(base+'/deliverables/v2.0/开发验证架构.html');page.wait_for_load_state('networkidle')
 assert page.locator('svg').count()>0
 svg=max(page.locator('svg').all(),key=lambda x:len(x.evaluate('(el)=>el.outerHTML')))
 source=svg.evaluate("""(el)=>{const clone=el.cloneNode(true),a=[el,...el.querySelectorAll('*')],b=[clone,...clone.querySelectorAll('*')];for(let i=0;i<a.length;i++){const st=getComputedStyle(a[i]);for(const k of ['fill','stroke','stroke-width','font-size','font-family','font-weight','opacity','text-anchor','marker-end']){let v=st.getPropertyValue(k);if(v)b[i].style.setProperty(k,v)}}clone.setAttribute('xmlns','http://www.w3.org/2000/svg');clone.style.removeProperty('transform');return clone.outerHTML}""")
 (OUT/'开发验证架构.svg').write_text(source)
 printable='<!doctype html><meta charset="utf-8"><style>@page{size:A3 portrait;margin:14mm}body{font:13px "Noto Sans CJK SC",sans-serif}svg{width:100%;height:auto;max-height:345mm}h1{font-size:22px}</style><h1>开发验证核心与后续接缝 v3.0</h1><p>本机Core、文件与Archify已验证；外部宿主、模型、文档和专业Worker仍需接入。</p>'+source
 (OUT/'开发验证架构打印版.html').write_text(printable)
 printpage=b.new_page();printpage.goto(base+'/deliverables/v2.0/开发验证架构打印版.html');printpage.wait_for_load_state('networkidle')
 printpage.pdf(path=str(OUT/'开发验证架构.pdf'),prefer_css_page_size=True,print_background=True)
 printpage.close()
 page.screenshot(path=str(OUT/'开发验证架构预览.png'),full_page=True)
 page.goto(base+'/开始评审.html');page.wait_for_load_state('networkidle')
 assert page.locator('a[href="../../docs/开发实施方案-v3.0.html"]').count()==1
 # Validate every local portal destination, retaining correct directory structure.
 from urllib.parse import unquote,urlsplit
 for href in page.locator('a[href]').evaluate_all('(xs)=>xs.map(x=>x.getAttribute("href"))'):
  if urlsplit(href).scheme or href.startswith('#'):continue
  assert (OUT/unquote(href.split('#')[0])).resolve().is_file(),href
 assert not errors,errors
 b.close()
server.shutdown()
report={'version':'3.0','checks':{'control_plane':14,'runtime_browser':8,'fusion_browser':64,'main_prototype':42},'actual_runtime':['FastAPI/SQLite','real file bytes/SHA256','pinned Archify CLI','manual scoped review reports','bounded retry HTTP fixtures','local Issue outbox'],'unverified':['paid/live model gateway','external Agent hosts','multi-laptop transport/auth/heartbeat','GitHub Issue API','Windows professional tools','real paper/translation chain','mobile delivery'],'sources':{'original_attachments':8,'additional_pdf_pages':34,'catalog':884,'priority_entries':23,'priority_topics':22},'private_originals_published':False}
(OUT/'research/v3-validation-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Explicit inclusions prevent local user data, credentials, dependencies, and raw attachments entering the archive.
files=[ROOT/'README.md',ROOT/'开始评审.html',ROOT/'requirements.txt',ROOT/'requirements.lock',ROOT/'.gitignore']
for directory in ['docs','config','workstation','scripts','tests','deliverables/v2.0']:
 files.extend(f for f in (ROOT/directory).rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.name.endswith('.pyc'))
archive=ROOT/'downloads/thesis-workstation-v3.0.zip';archive.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for f in sorted(files):z.write(f,f.relative_to(ROOT))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert all('/.local/' not in n and '/.venv/' not in n and 'attachments/' not in n for n in z.namelist())
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(files)},ensure_ascii=False))
