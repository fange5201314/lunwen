"""Use an already-started local service to exercise real UI and persisted files."""
from pathlib import Path
import json
import re
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = 'http://127.0.0.1:8765'
checks = []
def check(name, condition):
    assert condition, name
    checks.append(name)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                               args=['--no-sandbox'], env={'XDG_CONFIG_HOME':'/tmp/runtime-pw-config', 'XDG_CACHE_HOME':'/tmp/runtime-pw-cache'})
    context = browser.new_context(viewport={'width':1440,'height':1000}, accept_downloads=True)
    page = context.new_page(); errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE); page.wait_for_selector('#createProject')
    page.locator('#newTitle').fill('浏览器工具链验证')
    page.locator('#createProject').click(); page.wait_for_selector('#approve')
    page.locator('#seedTasks').click(); page.wait_for_function('snapshot?.tasks.length===2')
    first = page.evaluate('snapshot.tasks.find(t=>t.kind==="source_manifest").id')
    second = page.evaluate('snapshot.tasks.find(t=>t.kind==="architecture_render").id')
    page.locator(f'[data-dispatch="{first}"]').click()
    page.wait_for_selector('#alert', state='visible')
    check('Unapproved UI dispatch rejected by server', '确认' in page.locator('#alert').inner_text())
    page.locator('#approve').click(); page.wait_for_function('snapshot.project.approved_version===1')
    def wait_checking(task):
        page.wait_for_function('(id)=>snapshot.tasks.find(t=>t.id===id)?.status==="checking"', arg=task, timeout=15000)
    page.locator(f'[data-dispatch="{first}"]').click(); wait_checking(first)
    check('Real source bytes collected via UI', len(page.evaluate('snapshot.artifacts')) == 1)
    def register_review(task, dimension, reviewer):
        answers = iter([reviewer, 'PASS'])
        def handler(dialog): dialog.accept(next(answers))
        page.on('dialog', handler)
        page.locator(f'[data-review="{task}"][data-dimension="{dimension}"]').click()
        page.wait_for_function('(id)=>snapshot.reviews.some(r=>r.reviewer===id)', arg=reviewer)
        page.remove_listener('dialog', handler)
    register_review(first, 'engineering_quality', 'browser-quality-a')
    check('One report does not mark complete', page.evaluate('snapshot.tasks.find(t=>t.kind==="source_manifest").status') == 'checking')
    register_review(first, 'original_goal_alignment', 'browser-goal-b')
    page.wait_for_function('snapshot.tasks.find(t=>t.kind==="source_manifest").status==="checked"')
    page.locator(f'[data-dispatch="{second}"]').click(); wait_checking(second)
    check('Archify CLI real HTML appears', 'architecture.html' in page.locator('#workspace').inner_text())
    register_review(second, 'engineering_quality', 'browser-quality-c')
    register_review(second, 'original_goal_alignment', 'browser-goal-d')
    page.wait_for_function('snapshot.tasks.find(t=>t.kind==="architecture_render").status==="checked"')
    with page.expect_download() as event:
        page.locator('#accept').click()
    data = event.value.path().read_text() if isinstance(event.value.path(), Path) else Path(event.value.path()).read_text()
    manifest = json.loads(data)
    check('User acceptance downloads frozen real-file manifest', len(manifest['files']) >= 4 and len(manifest['manifest_hash']) == 64)
    page.reload(); page.wait_for_selector('#approve')
    check('Browser reload retains accepted project', all(x['status']=='accepted' for x in page.evaluate('snapshot.tasks')))
    page.screenshot(path=str(ROOT/'deliverables/v2.0/开发验证工作台预览.png'), full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    check('390px runtime UI fits viewport', page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
    check('No browser JavaScript errors', not errors)
    browser.close()
(ROOT/'deliverables/v2.0/research/runtime-browser-validation.json').write_text(json.dumps({'status':'passed','checks':checks,'javascript_errors':errors,'scope':'Real FastAPI/SQLite/files/Archify; reviews entered by test driver, not LLM'},ensure_ascii=False,indent=2))
print('Runtime browser checks passed:', len(checks))
