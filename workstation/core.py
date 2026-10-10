from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import os
import time
from .adapters import capabilities, run_adapter, digest
from .store import Store, encode, new_id


class Conflict(ValueError):
    pass


class Core:
    """One SQLite control plane per local service. Start with exactly one process.

    Review endpoints register independent workers' reports, not fake LLM reviews.
    """
    dimensions = {'engineering_quality', 'original_goal_alignment'}
    kinds = {'source_manifest', 'integrity_check', 'architecture_render', 'model_draft'}

    def __init__(self, root, worker_id=None):
        self.store = Store(root)
        self.worker_id = worker_id or os.environ.get('THESIS_WORKER_ID', 'local')
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='thesis-task')
        self.futures = {}
        # Startup never treats an interrupted run as success or blindly replays it.
        with self.store.transaction() as db:
            for row in db.execute("SELECT * FROM tasks WHERE status='running'").fetchall():
                db.execute("UPDATE tasks SET status='failed_waiting_user',error=? WHERE id=?",
                           ('服务重启：执行结果未提交，需核对现场后人工恢复。', row['id']))
                db.execute("UPDATE runs SET status='interrupted',ended=? WHERE id=?",
                           (time.time(), row['active_run']))
                # Keep lock until a human verifies any surviving child process.
                Store.event(db, row['project_id'], 'RunInterrupted', {'task_id': row['id']})

    def close(self):
        self.executor.shutdown(wait=True)

    @staticmethod
    def require(db, table, identifier):
        row = db.execute('SELECT * FROM ' + table + ' WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise Conflict('记录不存在：' + identifier)
        return dict(row)

    def create_project(self, title, requirements, worker_id=None):
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise Conflict('题目需要1–200个字符。')
        if not isinstance(requirements, dict) or not requirements:
            raise Conflict('需要结构化要求；示例与真实任务书要分别标记。')
        identity = new_id('project')
        payload = encode(requirements)
        project_dir = self.store.root / 'projects' / identity
        (project_dir / 'inputs').mkdir(parents=True)
        (project_dir / 'inputs/requirements.md').write_text(payload)
        with self.store.transaction() as db:
            db.execute('''INSERT INTO projects(id,title,worker_id,version,plan_hash,requirements,created)
                          VALUES(?,?,?,1,?,?,?)''',
                       (identity, title.strip(), worker_id or self.worker_id, digest(payload.encode()), payload, time.time()))
            Store.event(db, identity, 'ProjectCreated', {'worker_id': worker_id or self.worker_id,
                                                      'source_status': requirements.get('source_status', 'user_supplied')})
        return identity

    def approve(self, project_id, version, plan_hash):
        with self.store.transaction() as db:
            project = self.require(db, 'projects', project_id)
            if version != project['version'] or plan_hash != project['plan_hash']:
                raise Conflict('方案版本/哈希已改变，不能批准旧方案。')
            if project['approved_version'] == version:
                return
            db.execute('UPDATE projects SET approved_version=? WHERE id=?', (version, project_id))
            Store.event(db, project_id, 'PlanApproved', {'version': version, 'plan_hash': plan_hash})

    def revise(self, project_id, requirements, reason):
        if not isinstance(requirements, dict) or not requirements or not reason.strip():
            raise Conflict('修改方案需结构化要求及理由。')
        payload = encode(requirements)
        with self.store.transaction() as db:
            project = self.require(db, 'projects', project_id)
            running = db.execute("SELECT id FROM tasks WHERE project_id=? AND status='running'", (project_id,)).fetchone()
            if running:
                raise Conflict('有任务正在执行，请待其安全结束后修改方案。')
            db.execute('UPDATE projects SET version=version+1,approved_version=0,plan_hash=?,requirements=? WHERE id=?',
                       (digest(payload.encode()), payload, project_id))
            db.execute("UPDATE tasks SET status='pending',generation=generation+1,review_round=0 WHERE project_id=?", (project_id,))
            db.execute('UPDATE artifacts SET stale=1 WHERE project_id=?', (project_id,))
            Store.event(db, project_id, 'PlanRevised', {'version': project['version'] + 1, 'reason': reason})
        # Inputs are a projection of the authoritative DB, regenerated before execution.

    def add_input(self, project_id, name, content):
        if not isinstance(name, str) or Path(name).name != name or name in ('', '.', '..', 'requirements.md'):
            raise Conflict('仅允许普通输入文件名；任务要求通过方案修改。')
        if not isinstance(content, str) or len(content.encode()) > 2_000_000:
            raise Conflict('PoC输入仅支持不超过2MB的文本；PDF导入将在文档链接入。')
        with self.store.transaction() as db:
            self.require(db, 'projects', project_id)
            if db.execute("SELECT id FROM tasks WHERE project_id=? AND status='running'", (project_id,)).fetchone():
                raise Conflict('运行期间输入冻结，先等待任务结束。')
            if db.execute("SELECT id FROM tasks WHERE project_id=? AND status IN ('checking','checked','accepted')", (project_id,)).fetchone():
                raise Conflict('已有待审/已检查文件；先标记受影响证据过期后更新输入。')
            Store.event(db, project_id, 'InputAdded', {'name': name, 'sha256': digest(content.encode())})
            path = self.store.root / 'projects' / project_id / 'inputs' / name
            path.write_text(content)

    def add_task(self, project_id, node, kind, role='R009', dependencies=None, config=None, lock_key=None):
        if kind not in self.kinds:
            raise Conflict('工具能力未注册或尚未验证。')
        if not isinstance(node, str) or not node.strip() or len(node) > 100:
            raise Conflict('任务节点必须具名。')
        if not isinstance(role, str) or not role.strip():
            raise Conflict('需要有效岗位身份。')
        from .adapters import DESIGN_ROOT, REPO_ROOT
        registered = {r['id'] for r in json.loads((DESIGN_ROOT / 'config/agent-roles.json').read_text(encoding='utf-8'))}
        if role not in registered:
            raise Conflict('岗位身份不在已整理的96角色库。')
        config = dict(config or {})
        if kind == 'model_draft' and 'profile' not in config:
            bindings = json.loads((REPO_ROOT / 'config/model-bindings.example.json').read_text(encoding='utf-8'))
            config['profile'] = next((name for name, value in bindings['profiles'].items() if role in value['roles']), 'planning')
        dependencies = list(dict.fromkeys(dependencies or []))
        identifier = new_id('task')
        with self.store.transaction() as db:
            self.require(db, 'projects', project_id)
            for dependency in dependencies:
                dep = self.require(db, 'tasks', dependency)
                if dep['project_id'] != project_id:
                    raise Conflict('任务不能直接依赖其他项目。')
            if db.execute('SELECT id FROM tasks WHERE project_id=? AND node=?', (project_id, node)).fetchone():
                raise Conflict('该项目节点已存在。')
            db.execute('''INSERT INTO tasks(id,project_id,node,role,kind,dependencies,status,lock_key,config)
                          VALUES(?,?,?,?,?,?,'pending',?,?)''',
                       (identifier, project_id, node, role, kind, encode(dependencies),
                        lock_key or project_id + ':' + kind, encode(config or {})))
            Store.event(db, project_id, 'TaskAdded', {'task_id': identifier, 'kind': kind, 'dependencies': dependencies})
        return identifier

    def dispatch(self, task_id):
        with self.store.transaction() as db:
            task = self.require(db, 'tasks', task_id)
            project = self.require(db, 'projects', task['project_id'])
            if task['status'] == 'running':
                return task['active_run']  # idempotent duplicate dispatch
            if task['status'] not in ('pending', 'queued'):
                raise Conflict('当前状态不能派发：' + task['status'])
            if project['version'] != project['approved_version']:
                raise Conflict('方案尚未确认或已经改版。')
            if project['worker_id'] != self.worker_id:
                raise Conflict('该项目绑定另一台执行机，本机不能领取。')
            for identifier in json.loads(task['dependencies']):
                if self.require(db, 'tasks', identifier)['status'] not in ('checked', 'accepted'):
                    raise Conflict('上游任务未通过检查。')
            capability = capabilities().get(task['kind'], {})
            if not capability.get('ready'):
                raise Conflict('能力未就绪：' + task['kind'])
            if db.execute('SELECT key FROM resource_locks WHERE key=?', (task['lock_key'],)).fetchone():
                raise Conflict('所需资源正在被占用。')
            run_id = new_id('run')
            inputs = {'plan_hash': project['plan_hash'], 'generation': task['generation'],
                      'dependencies': json.loads(task['dependencies']), 'config': json.loads(task['config'])}
            # Include actual input bytes in the recorded input fingerprint.
            project_dir = self.store.root / 'projects' / project['id']
            (project_dir / 'inputs/requirements.md').write_text(project['requirements'])
            inputs['files'] = {p.name: digest(p.read_bytes()) for p in sorted((project_dir / 'inputs').glob('*')) if p.is_file()}
            db.execute('''INSERT INTO runs(id,task_id,project_version,generation,author,status,input_hash,started)
                          VALUES(?,?,?,?,?,'running',?,?)''',
                       (run_id, task_id, project['version'], task['generation'],
                        task['role'] + ':' + run_id, digest(encode(inputs).encode()), time.time()))
            db.execute('INSERT INTO resource_locks VALUES(?,?)', (task['lock_key'], run_id))
            db.execute("UPDATE tasks SET status='running',attempt=attempt+1,active_run=?,error=NULL,checkpoint=? WHERE id=?",
                       (run_id, encode({'inputs': inputs, 'run_id': run_id}), task_id))
            Store.event(db, project['id'], 'TaskDispatched', {'task_id': task_id, 'run_id': run_id})
        project['requirements'] = json.loads(project['requirements'])
        self.futures[run_id] = self.executor.submit(self._execute, task, project, run_id)
        return run_id

    def _execute(self, task, project, run_id):
        directory = self.store.root / 'projects' / project['id'] / 'runs' / run_id
        try:
            paths, log = run_adapter(task['kind'], project, json.loads(task['config']), directory)
            outputs = []
            for path in paths:
                path = Path(path).resolve()
                if not path.is_relative_to(directory.resolve()):
                    raise Conflict('工具输出路径越过本次运行目录。')
                data = path.read_bytes()
                if not data:
                    raise Conflict('工具返回空产物。')
                outputs.append({'name': path.name, 'path': str(path.relative_to(self.store.root)),
                                'sha256': digest(data), 'bytes': len(data)})
            with self.store.transaction() as db:
                current = self.require(db, 'tasks', task['id'])
                if current['active_run'] != run_id or current['generation'] != task['generation']:
                    raise Conflict('旧运行结果不能写入当前任务。')
                for output in outputs:
                    db.execute('''INSERT INTO artifacts(id,project_id,task_id,run_id,generation,name,path,sha256,bytes)
                                  VALUES(?,?,?,?,?,?,?,?,?)''',
                               (new_id('artifact'), project['id'], task['id'], run_id, task['generation'],
                                output['name'], output['path'], output['sha256'], output['bytes']))
                result = {'outputs': outputs, 'log': log}
                db.execute("UPDATE runs SET status='produced',result=?,ended=? WHERE id=?", (encode(result), time.time(), run_id))
                db.execute("UPDATE tasks SET status='checking' WHERE id=?", (task['id'],))
                db.execute('DELETE FROM resource_locks WHERE run_id=?', (run_id,))
                Store.event(db, project['id'], 'ArtifactsProduced', {'task_id': task['id'], 'run_id': run_id, 'outputs': outputs})
        except Exception as error:
            directory.mkdir(parents=True, exist_ok=True)
            # Adapters deliberately provide sanitized errors; do not save provider response bodies.
            message = str(error) if isinstance(error, (RuntimeError, ValueError)) else type(error).__name__
            (directory / 'failure.json').write_text(encode({'run_id': run_id, 'error': message}))
            with self.store.transaction() as db:
                db.execute("UPDATE runs SET status='failed',result=?,ended=? WHERE id=?",
                           (encode({'error': message}), time.time(), run_id))
                db.execute("UPDATE tasks SET status='failed_waiting_user',error=? WHERE id=? AND active_run=?",
                           (message, task['id'], run_id))
                db.execute('DELETE FROM resource_locks WHERE run_id=?', (run_id,))
                Store.event(db, project['id'], 'FailurePending', {'task_id': task['id'], 'run_id': run_id,
                             'error': message, 'mobile_delivery': 'not_connected'})

    def review(self, task_id, report):
        dimension = report.get('dimension')
        reviewer = report.get('reviewer')
        verdict = report.get('verdict')
        findings = report.get('findings', [])
        if dimension not in self.dimensions or verdict not in ('passed', 'failed', 'blocked') or not reviewer:
            raise Conflict('审查必须明确身份、维度和结论。')
        if not isinstance(findings, list):
            raise Conflict('缺陷列表格式错误。')
        normalized = []
        for item in findings:
            if not isinstance(item, dict) or item.get('severity') not in ('P0', 'P1', 'P2') or not item.get('locator') or not item.get('message'):
                raise Conflict('每项缺陷须有P0/P1/P2、精确位置和描述。')
            item = dict(item)
            if item.get('mandatory_requirement'):
                item['severity'] = 'P0'  # Hard delivery requirements cannot be downgraded.
            normalized.append(item)
        blocking = any(x['severity'] == 'P0' for x in normalized)
        if verdict == 'failed' and not blocking:
            raise Conflict('阻断失败须明确P0；普通建议用通过并附P1/P2清单。')
        if verdict == 'passed' and blocking:
            raise Conflict('P0尚未解决，不能登记通过。')
        with self.store.transaction() as db:
            task = self.require(db, 'tasks', task_id)
            project = self.require(db, 'projects', task['project_id'])
            run = self.require(db, 'runs', task['active_run'])
            if (report.get('generation') != task['generation'] or report.get('run_id') != run['id'] or
                report.get('plan_version') != project['version'] or run['project_version'] != project['approved_version']):
                raise Conflict('旧方案/旧generation/旧run报告被拒收。')
            output_hash = digest(encode(json.loads(run['result'])['outputs']).encode())
            if report.get('input_hash') != run['input_hash'] or report.get('output_hash') != output_hash:
                raise Conflict('审查输入输出哈希不匹配。')
            if reviewer == run['author']:
                raise Conflict('作者不能审查自己的产物。')
            existing = db.execute('SELECT * FROM reviews WHERE run_id=?', (run['id'],)).fetchall()
            if any(r['reviewer'] == reviewer and r['dimension'] != dimension for r in existing):
                raise Conflict('两种审查需要独立成员。')
            same = next((r for r in existing if r['dimension'] == dimension), None)
            if same:
                if same['reviewer'] == reviewer and same['verdict'] == verdict and same['findings'] == encode(normalized):
                    return
                raise Conflict('同一轮同一维度已有报告，不能覆盖。')
            if task['status'] != 'checking':
                raise Conflict('任务当前不接受新审查。')
            db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?)',
                       (new_id('review'), run['id'], dimension, reviewer, verdict, encode(normalized), time.time()))
            for finding in normalized:
                fingerprint = digest(encode([task_id, finding['locator'], finding['message']]).encode())
                db.execute('''INSERT OR IGNORE INTO issues VALUES(?,?,?,?,?,?,?,?)''',
                           (new_id('issue'), task['project_id'], task_id, fingerprint, finding['severity'],
                            encode(finding), 'open', 'local_outbox_not_synced'))
            Store.event(db, task['project_id'], 'ReviewRecorded', {'task_id': task_id, 'dimension': dimension,
                        'reviewer': reviewer, 'verdict': verdict, 'generation': task['generation']})
            reports = db.execute('SELECT * FROM reviews WHERE run_id=?', (run['id'],)).fetchall()
            if len(reports) == 2:
                next_round = task['review_round'] + 1
                passed = all(r['verdict'] == 'passed' for r in reports)
                if passed:
                    status = 'checked'
                    db.execute("UPDATE issues SET status='verified_closed' WHERE task_id=? AND severity='P0'", (task_id,))
                elif any(r['verdict'] == 'blocked' for r in reports) or next_round >= 2:
                    status = 'failed_waiting_user'
                else:
                    status = 'needs_patch'
                db.execute('UPDATE tasks SET status=?,review_round=? WHERE id=?', (status, next_round, task_id))
                Store.event(db, task['project_id'], 'ReviewGateResolved', {'task_id': task_id,
                            'status': status, 'review_round': next_round, 'automatic_third_round': False})

    def review_scope(self, task_id):
        with self.store.transaction() as db:
            task = self.require(db, 'tasks', task_id)
            run = self.require(db, 'runs', task['active_run'])
            project = self.require(db, 'projects', task['project_id'])
            if not run['result'] or run['status'] != 'produced':
                raise Conflict('尚未产出可审查结果。')
            return {'run_id': run['id'], 'generation': task['generation'], 'plan_version': project['version'],
                    'author': run['author'], 'input_hash': run['input_hash'],
                    'output_hash': digest(encode(json.loads(run['result'])['outputs']).encode())}

    def resume(self, task_id, reason, patch=False, old_process_checked=False):
        if not isinstance(reason, str) or len(reason.strip()) < 3:
            raise Conflict('需要记录已经完成的处理或补丁说明。')
        with self.store.transaction() as db:
            task = self.require(db, 'tasks', task_id)
            expected = 'needs_patch' if patch else 'failed_waiting_user'
            if task['status'] != expected:
                raise Conflict('当前状态不能进行该恢复操作。')
            if task['review_round'] >= 2:
                raise Conflict('已达两审上限；需人工仲裁并建立新方案，不能自动第三轮。')
            future = self.futures.get(task['active_run'])
            if future and not future.done():
                raise Conflict('原工具仍在执行，不能重放。')
            run = self.require(db, 'runs', task['active_run'])
            if run['status'] == 'interrupted':
                if not old_process_checked:
                    raise Conflict('需人工核对原进程/软件会话已停止，才可释放资源锁。')
                db.execute('DELETE FROM resource_locks WHERE run_id=?', (run['id'],))
            db.execute("UPDATE tasks SET status='queued',generation=generation+1,error=NULL WHERE id=?", (task_id,))
            db.execute('UPDATE artifacts SET stale=1 WHERE task_id=?', (task_id,))
            Store.event(db, task['project_id'], 'PatchRequested' if patch else 'HumanResume',
                        {'task_id': task_id, 'reason': reason, 'generation': task['generation'] + 1})

    def invalidate(self, task_id, reason):
        if not reason.strip():
            raise Conflict('需记录变更来源。')
        with self.store.transaction() as db:
            source = self.require(db, 'tasks', task_id)
            rows = [dict(r) for r in db.execute('SELECT * FROM tasks WHERE project_id=?', (source['project_id'],))]
            affected = {task_id}
            changed = True
            while changed:
                changed = False
                for row in rows:
                    if row['id'] not in affected and affected.intersection(json.loads(row['dependencies'])):
                        affected.add(row['id']); changed = True
            if any(r['status'] == 'running' and r['id'] in affected for r in rows):
                raise Conflict('受影响任务仍在运行，先等待其结束。')
            for identifier in affected:
                db.execute("UPDATE tasks SET status='pending',generation=generation+1,review_round=0 WHERE id=?", (identifier,))
                db.execute('UPDATE artifacts SET stale=1 WHERE task_id=?', (identifier,))
            Store.event(db, source['project_id'], 'EvidenceInvalidated', {'affected_tasks': sorted(affected),
                        'reason': reason, 'granularity': 'task_dependency_graph'})
        return sorted(affected)

    def decision(self, project_id, card):
        required = ('background', 'alternatives', 'selected', 'constraints', 'rejected_reasons')
        if not isinstance(card, dict) or any(key not in card for key in required):
            raise Conflict('决定需记录背景、备选、选用、约束与否决理由。')
        with self.store.transaction() as db:
            self.require(db, 'projects', project_id)
            identity = new_id('decision')
            db.execute('INSERT INTO decisions VALUES(?,?,?,?)', (identity, project_id, encode(card), time.time()))
            Store.event(db, project_id, 'DecisionRecorded', {'decision_id': identity})
        return identity

    def accept(self, project_id):
        with self.store.transaction() as db:
            project = self.require(db, 'projects', project_id)
            tasks = db.execute('SELECT * FROM tasks WHERE project_id=?', (project_id,)).fetchall()
            if project['version'] != project['approved_version'] or not tasks or any(t['status'] not in ('checked', 'accepted') for t in tasks):
                raise Conflict('方案未确认、任务未检查通过或存在阻断，不能验收。')
            files = [dict(a) for a in db.execute('SELECT * FROM artifacts WHERE project_id=? AND stale=0', (project_id,))]
            if not files:
                raise Conflict('没有真实有效文件。')
            for artifact in files:
                path = self.store.root / artifact['path']
                if not path.is_file() or digest(path.read_bytes()) != artifact['sha256']:
                    raise Conflict('产物实际文件已改变或丢失，须重新检查。')
            manifest = {'project_id': project_id, 'plan_version': project['version'], 'files': files,
                        'manifest_hash': digest(encode(files).encode()), 'accepted_at': time.time()}
            path = self.store.root / 'projects' / project_id / ('acceptance-' + new_id('version') + '.json')
            path.write_text(encode(manifest))
            db.execute("UPDATE tasks SET status='accepted' WHERE project_id=?", (project_id,))
            Store.event(db, project_id, 'UserAccepted', {'manifest_hash': manifest['manifest_hash'], 'file_count': len(files)})
        return manifest

    def issue_export(self, project_id):
        snapshot = self.store.snapshot(project_id)
        if not snapshot:
            raise Conflict('项目不存在。')
        return {'project_id': project_id, 'delivery': 'local_export_only', 'github_written': False,
                'issues': [{'local_id': item['id'], 'fingerprint': item['fingerprint'],
                            'title': '[' + item['severity'] + '] ' + item['body']['message'],
                            'labels': [{'P0': 'p0-blocker', 'P1': 'p1-review', 'P2': 'p2-suggestion'}[item['severity']]],
                            'body': item['body'], 'local_status': item['status'], 'mirror_status': item['mirror_status']}
                           for item in snapshot['issues']]}
