from pathlib import Path
import json
import http.server, threading, functools
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE="http://127.0.0.1:"+str(server.server_address[1])
checks=[]
def check(name,value):
 assert value,name
 checks.append(name)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'],env={'XDG_CONFIG_HOME':'/tmp/fusion-pw-config','XDG_CACHE_HOME':'/tmp/fusion-pw-cache'})
 page=b.new_page(viewport={'width':1440,'height':1000},accept_downloads=True); errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE+'/资源融合实验室.html')
 check('Seven recipes and 23 priority sources',page.locator('[data-recipe]').count()==7 and page.locator('.source-card').count()==23)
 for recipe in page.evaluate('DATA.blueprints.map(x=>x.id)'):
  page.locator(f'[data-recipe="{recipe}"]').click()
  for tab in ['overview','blueprint','meeting','radar','recovery','sources']:
   page.locator(f'[data-tab="{tab}"]').click()
   check(recipe+': '+tab+' renders',page.locator('.panel.active').inner_text().strip())
 page.locator('[data-recipe="goal"]').click();page.locator('[data-tab="blueprint"]').click()
 page.locator('#c-placeholders').check();page.locator('#compile').click()
 check('G1 placeholders block compilation',page.evaluate('state.compiled===null'))
 page.locator('#c-placeholders').uncheck();page.locator('#compile').click()
 with page.expect_download() as d:page.locator('#export').click()
 result=json.loads(Path(d.value.path()).read_text())
 check('Download contains typed source and generation contracts',result['simulation'] and result['source_ids'] and result['audit_contract']['generation']==page.evaluate('state.generation'))
 page.locator('[data-tab="meeting"]').click();page.locator('#round1').click()
 page.locator('#reviewer').select_option('author');page.locator('#structureAudit').click()
 check('Author review rejected',not page.evaluate('state.reviews.structure'))
 page.locator('#oldReport').click();page.locator('#silentReport').click()
 check('Old and silent reports do not advance gate',not page.evaluate('state.reviews.structure'))
 page.locator('#reviewer').select_option('shared-reviewer');page.locator('#structureAudit').click()
 page.locator('#reviewer').select_option('shared-reviewer');page.locator('#goalAudit').click()
 check('Same reviewer cannot pass both dimensions',not page.evaluate('state.reviews.goal'))
 page.locator('#reviewer').select_option('independent');page.locator('#goalAudit').click();page.locator('#humanGate').click()
 check('Two distinct current reports allow human gate',page.evaluate('state.human'))
 page.locator('[data-tab="radar"]').click();page.locator('#paramValue').fill('100');page.locator('#applyChange').click()
 check('Parameter change selectively invalidates evidence',page.evaluate("radarStatus('literature')==='valid' && radarStatus('requirement_contract')==='stale' && !state.human"))
 page.locator('#recheck').click();check('Recheck alone cannot accept new generation',page.locator('#acceptChange').is_disabled())
 page.locator('[data-tab="blueprint"]').click();page.locator('#compile').click()
 check('Recompiled goal uses changed response target',page.evaluate('state.compiled.goal_contract.response_limit_ms===100'))
 page.locator('[data-tab="meeting"]').click();page.locator('#round1').click()
 check('Meeting uses current 100ms target', 'response_limit_ms=100' in page.locator('#meeting').inner_text())
 page.locator('#structureAudit').click();page.locator('#goalAudit').click()
 page.locator('[data-tab="radar"]').click();page.locator('#acceptChange').click()
 check('Current dual reports allow accepting changed evidence',page.evaluate('state.radar.accepted'))
 page.locator('[data-tab="recovery"]').click();page.locator('#failAPI').click()
 check('API simulation stops at shared three-attempt budget',page.evaluate('state.api.attempts===3 && state.api.state==="awaiting_human"'))
 page.reload();check('Checkpoint survives browser reload',page.evaluate('state.api.checkpoint.attempts===3'))
 page.locator('#resume').click();check('Manual matching-version resume completes simulation',page.evaluate('state.api.state==="completed"'))
 page.locator('[data-tab="overview"]').click();page.screenshot(path=str(ROOT/'资源融合实验室预览.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844})
 for tab in ['overview','blueprint','meeting','radar','recovery','sources']:
  page.locator(f'[data-tab="{tab}"]').click()
  width=page.evaluate('document.documentElement.scrollWidth')
  check('390px '+tab+' fits viewport',width<=391)
 check('No JavaScript errors',not errors)
 b.close()
report={'status':'passed','checks':checks,'javascript_errors':errors,'scope':'Offline design simulation; real runtime is separately verified in runtime-browser-validation.json'}
(ROOT/'research/fusion-browser-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
old=ROOT/'research/fusion-review.json'
if old.exists():
 data=json.loads(old.read_text());data['superseded_by']='fusion-browser-validation.json';old.write_text(json.dumps(data,ensure_ascii=False,indent=2))
print('Fusion browser checks passed:',len(checks))
