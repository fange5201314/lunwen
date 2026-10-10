"""Fixed capability adapters. No commands supplied by UI or model are executed."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
import httpx

ARCHIFY_COMMIT = '7f483b61e8f68d0d5c3219d2c943c5381c8db0b1'
REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGN_ROOT = REPO_ROOT / 'deliverables/v2.0'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def capabilities():
    path = os.environ.get('THESIS_ARCHIFY_DIR', '')
    commit = ''
    if path:
        try:
            result = subprocess.run(['git', '-C', path, 'rev-parse', 'HEAD'], capture_output=True,
                                    text=True, timeout=5, check=True)
            commit = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return {
        'source_manifest': {'ready': True, 'type': 'deterministic_local_file_check'},
        'integrity_check': {'ready': True, 'type': 'deterministic_local_file_check'},
        'architecture_render': {'ready': commit == ARCHIFY_COMMIT,
                                'commit': commit, 'required_commit': ARCHIFY_COMMIT},
        'model_draft': {'ready': bool(os.environ.get('THESIS_MODEL_BASE_URL') and
                                     os.environ.get('THESIS_MODEL_API_KEY')),
                        'type': 'configured_gateway_required'},
        'cad_plc': {'ready': False, 'reason': 'Windows worker and native software self-test required'},
        'mobile_notifications': {'ready': False, 'reason': 'Local pending center works; no channel connected'},
        'github_issue_sync': {'ready': False, 'reason': 'Local deduplicated issue outbox only'}
    }


def ask_gateway(messages, alias, *, base_url=None, api_key=None, retry_owner=None, transport=None):
    """Gateway owns retries by default; direct mode has a single global bounded budget.

    Server config chooses endpoint/alias. API key never enters logs or results.
    """
    base_url = base_url or os.environ.get('THESIS_MODEL_BASE_URL')
    api_key = api_key or os.environ.get('THESIS_MODEL_API_KEY')
    if not base_url or not api_key:
        raise RuntimeError('模型网关尚未配置，保留任务并等待人工配置。')
    owner = retry_owner or os.environ.get('THESIS_RETRY_OWNER', 'gateway')
    if owner not in ('gateway', 'client'):
        raise ValueError('THESIS_RETRY_OWNER must be gateway or client')
    attempts = 1 if owner == 'gateway' else 3
    deadline = time.monotonic() + 90
    with httpx.Client(transport=transport, follow_redirects=False) as client:
        for attempt in range(1, attempts + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError('模型请求总时间预算耗尽。')
            try:
                response = client.post(base_url.rstrip('/') + '/chat/completions',
                    headers={'Authorization': 'Bearer ' + api_key}, timeout=min(30, remaining),
                    json={'model': alias, 'messages': messages, 'stream': False,
                          'response_format': {'type': 'json_object'}})
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == attempts:
                    raise RuntimeError('模型连接失败；请求预算已耗尽。') from None
                time.sleep(min(.1 * 2 ** (attempt - 1), max(0, deadline - time.monotonic())))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == attempts:
                    raise RuntimeError(f'模型返回HTTP {response.status_code}；请求预算已耗尽。')
                retry_after = response.headers.get('Retry-After', '0')
                try:
                    delay = max(0, float(retry_after))
                except ValueError:
                    delay = 1
                if delay >= deadline - time.monotonic():
                    raise RuntimeError('Retry-After exceeds remaining request budget')
                time.sleep(min(max(.1, delay), deadline - time.monotonic()))
                continue
            if not response.is_success:
                raise RuntimeError(f'模型返回HTTP {response.status_code}；不重试认证/协议错误。')
            try:
                body = response.json()
                content = body['choices'][0]['message']['content']
                parsed = json.loads(content)
                if not isinstance(parsed, dict) or not isinstance(parsed.get('goals'), list) or not parsed['goals']:
                    raise ValueError('goals required')
                if any(not isinstance(goal, str) or not goal.strip() for goal in parsed['goals']):
                    raise ValueError('goal text required')
            except (ValueError, KeyError, IndexError, TypeError):
                raise RuntimeError('模型返回内容不符合目标草案JSON契约；未提交部分结果。') from None
            return {'draft': parsed, 'model_alias': alias, 'client_attempts': attempt,
                    'retry_owner': owner, 'status': 'draft_requires_review'}


def run_adapter(kind, project, config, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    project_dir = directory.parent.parent
    if kind == 'source_manifest':
        items = []
        for path in sorted((project_dir / 'inputs').glob('*')):
            if path.is_file():
                raw = path.read_bytes()
                items.append({'name': path.name, 'bytes': len(raw), 'sha256': digest(raw)})
        if not items:
            raise RuntimeError('输入资料为空。')
        output = directory / 'source-manifest.json'
        output.write_text(json.dumps({'project_id': project['id'], 'plan_version': project['version'],
                                     'sources': items, 'content_review': 'pending'}, ensure_ascii=False, indent=2))
        return [output], '真实读取输入文件并计算SHA-256；内容审查尚待独立报告。'
    if kind == 'integrity_check':
        name = config.get('required_input', 'requirements.md')
        if Path(name).name != name:
            raise ValueError('Only input filenames are accepted')
        path = project_dir / 'inputs' / name
        if not path.is_file():
            raise RuntimeError('实际缺少输入文件：' + name)
        data = path.read_bytes()
        if config.get('expected_sha256') and config['expected_sha256'] != digest(data):
            raise RuntimeError('输入哈希与冻结要求不一致。')
        output = directory / 'integrity-report.json'
        output.write_text(json.dumps({'file': name, 'sha256': digest(data), 'bytes': len(data),
                                     'check': 'passed'}, ensure_ascii=False, indent=2))
        return [output], '真实文件存在性与指定哈希检查通过。'
    if kind == 'architecture_render':
        if not capabilities()['architecture_render']['ready']:
            raise RuntimeError('Archify固定版本未配置；先完成工具能力自测。')
        tool_dir = Path(os.environ['THESIS_ARCHIFY_DIR']).resolve()
        candidate = json.loads((REPO_ROOT / 'config/runtime-architecture.json').read_text(encoding='utf-8'))
        candidate['meta']['output'] = 'architecture.html'
        input_path = directory / 'candidate.json'
        input_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2))
        # Pinned CLI command is verified by the setup self-test. No shell expansion.
        command = ['node', str(tool_dir / 'archify/bin/archify.mjs'), 'render', 'architecture',
                   str(input_path), 'architecture.html']
        result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=90)
        (directory / 'tool.log').write_text(result.stdout + '\n' + result.stderr)
        if result.returncode != 0:
            raise RuntimeError('Archify退出码非零；详细记录保存在本次运行tool.log。')
        output = directory / 'architecture.html'
        if not output.is_file() or '<svg' not in output.read_text(encoding='utf-8'):
            raise RuntimeError('Archify未产生含SVG的完整HTML产物。')
        return [input_path, output, directory / 'tool.log'], 'Archify固定提交CLI实际执行，退出码与HTML/SVG结构检查通过。'
    if kind == 'model_draft':
        bindings = json.loads((REPO_ROOT / 'config/model-bindings.example.json').read_text(encoding='utf-8'))
        profile = config.get('profile', 'planning')
        if profile not in bindings['profiles']:
            raise ValueError('Unknown model capability profile')
        alias = bindings['profiles'][profile]['alias']
        messages = [{'role': 'system', 'content': '返回JSON对象，goals为非空字符串列表。仅整理提供的要求；不编造学校、导师、实测数据或文献。'},
                    {'role': 'user', 'content': json.dumps(project['requirements'], ensure_ascii=False)}]
        response = ask_gateway(messages, alias)
        output = directory / 'goal-draft.json'
        output.write_text(json.dumps(response, ensure_ascii=False, indent=2))
        return [output], '已通过配置网关取得结构化目标草案，仍须独立审查。'
    raise ValueError('Unknown or unverified capability: ' + kind)
