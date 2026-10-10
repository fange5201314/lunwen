from pathlib import Path
from playwright.sync_api import sync_playwright
import json,html
root=Path(__file__).parent.parent
import http.server, threading, functools
class QuietHandler(http.server.SimpleHTTPRequestHandler):
 def log_message(self, format, *args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE='http://127.0.0.1:'+str(server.server_address[1])
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'],env={'XDG_CONFIG_HOME':'/tmp/thesis-pw-config','XDG_CACHE_HOME':'/tmp/thesis-pw-cache'})
 c=b.new_context(viewport={'width':1440,'height':1000});page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE+'/架构图.html');page.wait_for_timeout(600)
 # Freeze computed SVG styles so the standalone SVG does not depend on HTML stylesheets.
 svg=page.locator('svg').all();target=max(svg,key=lambda e:len(e.evaluate('(x)=>x.outerHTML')))
 source=target.evaluate('''(el)=>{const copy=el.cloneNode(true);const originals=[el,...el.querySelectorAll('*')];const clones=[copy,...copy.querySelectorAll('*')];const props=['fill','stroke','stroke-width','font-size','font-family','font-weight','opacity','fill-opacity','stroke-opacity','stroke-linecap','stroke-linejoin','text-anchor','dominant-baseline','marker-end','marker-start','filter'];for(let i=0;i<originals.length;i++){let st=getComputedStyle(originals[i]);for(let prop of props){let v=st.getPropertyValue(prop);v=v.replace(/url\\(["']?[^)#]*#([^)'" ]+)["']?\\)/g,'url(#$1)');if(v)clones[i].style.setProperty(prop,v)}}copy.setAttribute('xmlns','http://www.w3.org/2000/svg');copy.style.removeProperty('transform');return copy.outerHTML}''')
 (root/'架构图.svg').write_text(source)
 printable='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>毕设论文工作站 · 多Agent编排架构</title><style>@page{size:A3 portrait;margin:16mm}body{font-family:"Noto Sans CJK SC",sans-serif;color:#25283c;margin:0}h1{font-size:20px}p{font-size:11px;color:#777}svg{width:100%;height:auto;max-height:335mm}.note{margin-top:16px;padding:15px;background:#f4f2f8;font-size:11px;line-height:1.8}</style><h1>毕设论文工作站 · 多 Agent 编排架构</h1><p>设计方案 v2.0 / 前端、状态、执行器、文件、模型API与证据；非已运行拓扑。</p>'+source+'<div class="note">唯一业务状态源：工作站持有方案、任务关卡、决定、证据与验收；Paperclip复用团队与派发。<br>API故障：同能力渠道有限切换、完整响应才提交；工具副作用不自动重放。<br>业务失败：保存现场、停失败节点与依赖、通知人工恢复；其他独立项目继续。<br>文档链：Paper Search CLI → Docling → 翻译术语 → OfficeCLI → thesis-docx。<br>Archify开源CLI实际生成互动图；多Agent协作和恢复另有专图。</div></html>'
 (root/'架构图打印版.html').write_text(printable)
 page.goto(BASE+'/架构图打印版.html');page.wait_for_timeout(400);page.pdf(path=str(root/'架构图.pdf'),print_background=True,prefer_css_page_size=True)
 page.goto(BASE+'/多Agent协作与恢复图.html');page.wait_for_timeout(300)
 page.locator('[data-node="meeting"]').click();assert 'R006' in page.locator('#panel').inner_text();page.screenshot(path=str(root/'多Agent协作预览.png'),full_page=True);page.pdf(path=str(root/'多Agent协作与恢复图.pdf'),format='A3',print_background=True)
 page.get_by_role('button',name='失败与人工恢复').click();page.locator('[data-node="budget"]').click();assert '重试预算' in page.locator('#panel').inner_text();page.screenshot(path=str(root/'失败与恢复预览.png'),full_page=True);page.pdf(path=str(root/'失败与恢复图.pdf'),format='A3',print_background=True)
 page.goto(BASE+'/可点击原型.html');page.evaluate("go('architecture')");page.get_by_role('button',name='岗位协作与交接').click();page.wait_for_timeout(300);assert page.frame_locator('#diagramframe').locator('svg').count()==1
 page.get_by_role('button',name='API与人工恢复').click();page.wait_for_timeout(300);assert '两类失败' in page.frame_locator('#diagramframe').locator('#title').inner_text()
 # Proposal PDF and viewport check; fonts and source images loaded before print.
 page.goto(BASE+'/架构设计与方案说明.html');page.wait_for_load_state('networkidle');page.evaluate('document.fonts.ready');assert page.locator('h2').count()>=13
 page.pdf(path=str(root/'架构设计与方案说明.pdf'),print_background=True,prefer_css_page_size=True,display_header_footer=True,header_template='<span></span>',footer_template='<div style="font-size:8px;color:#999;width:100%;text-align:center">THESIS ATELIER / v2.0 · <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
 page.screenshot(path=str(root/'research/proposal-first-screen.png'),full_page=False)
 for img in page.locator('img').all():assert img.evaluate('(x)=>x.complete&&x.naturalWidth>0')
 page.goto(BASE+'/资源清单与使用说明.html');page.wait_for_load_state('networkidle');page.pdf(path=str(root/'资源清单与使用说明.pdf'),print_background=True,prefer_css_page_size=True)
 assert not errors,errors
 b.close()
(root/'research/final-browser-report.json').write_text(json.dumps({'status':'passed','checks':['computed-style standalone SVG export','single-page architecture PDF','multi-agent diagram node contract inspection','failure diagram budget inspection','prototype diagram switching','proposal HTML font/image load and PDF print','resource report PDF print'],'javascript_errors':errors,'browser':'system Chromium over allowed localhost HTTP; no browser policy changed'},ensure_ascii=False,indent=2))
print('Final diagrams, proposal PDF and browser checks passed')
