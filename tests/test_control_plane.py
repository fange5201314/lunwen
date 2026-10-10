import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from workstation.core import Core, Conflict
from workstation.adapters import ask_gateway, capabilities, digest, run_adapter
from workstation.main import create_app


class ControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.core = Core(self.temp.name)
        self.project = self.core.create_project('真实控制面验证样例', {'goal': '保留真实来源哈希', 'source_status': 'test_fixture'})

    def tearDown(self):
        self.core.close()
        self.temp.cleanup()

    def approve(self, identifier=None):
        identifier = identifier or self.project
        p = self.core.store.snapshot(identifier)['project']
        self.core.approve(identifier, p['version'], p['plan_hash'])

    def run(self, result=None):
        # Keep unittest.TestCase.run intact: task execution helper is execute().
        return super().run(result)

    def execute(self, task):
        run = self.core.dispatch(task)
        self.core.futures[run].result(timeout=30)
        return run

    def report(self, task, dimension, verdict='passed', findings=None, **overrides):
        scope = self.core.review_scope(task)
        return {**scope, 'reviewer': dimension + '-independent', 'dimension': dimension,
                'verdict': verdict, 'findings': findings or [], **overrides}

    def pass_reviews(self, task):
        for dimension in sorted(self.core.dimensions):
            self.core.review(task, self.report(task, dimension))

    def status(self, task):
        return next(t['status'] for t in self.core.store.snapshot(self.project)['tasks'] if t['id'] == task)

    def test_approval_and_dependency_are_enforced(self):
        first = self.core.add_task(self.project, '来源', 'source_manifest')
        second = self.core.add_task(self.project, '检查', 'integrity_check', dependencies=[first])
        with self.assertRaises(Conflict): self.core.dispatch(first)
        with self.assertRaises(Conflict): self.core.approve(self.project, 99, 'old')
        self.approve()
        self.execute(first)
        with self.assertRaises(Conflict): self.core.dispatch(second)
        self.pass_reviews(first)
        self.execute(second)
        self.assertEqual(self.status(second), 'checking')

    def test_real_file_hash_acceptance_and_tamper_detection(self):
        task = self.core.add_task(self.project, '清单', 'source_manifest')
        self.approve(); self.execute(task)
        with self.assertRaises(Conflict): self.core.accept(self.project)
        self.pass_reviews(task)
        manifest = self.core.accept(self.project)
        for item in manifest['files']:
            path = Path(self.temp.name) / item['path']
            self.assertEqual(digest(path.read_bytes()), item['sha256'])
        path.write_text('modified outside controlled submission')
        with self.assertRaises(Conflict): self.core.accept(self.project)

    def test_two_distinct_reviews_scope_hash_and_idempotence(self):
        task = self.core.add_task(self.project, '清单', 'source_manifest')
        self.approve(); self.execute(task)
        scope = self.core.review_scope(task)
        for bad in ({'reviewer': scope['author']}, {'generation': 999}, {'output_hash': 'old'}, {'plan_version': 999}):
            with self.assertRaises(Conflict):
                self.core.review(task, self.report(task, 'engineering_quality', **bad))
        first = self.report(task, 'engineering_quality')
        self.core.review(task, first)
        self.assertEqual(self.status(task), 'checking')
        with self.assertRaises(Conflict):
            self.core.review(task, self.report(task, 'original_goal_alignment', reviewer=first['reviewer']))
        second = self.report(task, 'original_goal_alignment')
        self.core.review(task, second)
        self.core.review(task, second)
        self.assertEqual(len(self.core.store.snapshot(self.project)['reviews']), 2)
        self.assertEqual(self.status(task), 'checked')

    def test_p1_is_advisory_but_mandatory_requirement_cannot_be_downgraded(self):
        task = self.core.add_task(self.project, '清单', 'source_manifest')
        self.approve(); self.execute(task)
        finding = {'severity': 'P1', 'locator': 'requirements.md', 'message': '文字风格可改善'}
        self.core.review(task, self.report(task, 'engineering_quality', findings=[finding]))
        self.core.review(task, self.report(task, 'original_goal_alignment'))
        self.assertEqual(self.status(task), 'checked')
        self.assertEqual(self.core.issue_export(self.project)['issues'][0]['labels'], ['p1-review'])
        self.core.invalidate(task, '新增硬性交付验证')
        self.execute(task)
        with self.assertRaises(Conflict):
            self.core.review(task, self.report(task, 'engineering_quality', findings=[{**finding, 'mandatory_requirement': True}]))

    def test_two_review_rounds_have_no_automatic_third_round_and_issue_deduplicates(self):
        task = self.core.add_task(self.project, '清单', 'source_manifest')
        self.approve(); self.execute(task)
        defect = {'severity': 'P0', 'locator': 'source-manifest.json:1', 'message': '缺少合同必交项'}
        for cycle in range(2):
            self.core.review(task, self.report(task, 'engineering_quality', 'failed', [defect]))
            self.core.review(task, self.report(task, 'original_goal_alignment'))
            if cycle == 0:
                self.assertEqual(self.status(task), 'needs_patch')
                self.core.resume(task, '作者提交局部修复后重新验证', patch=True)
                self.execute(task)
        self.assertEqual(self.status(task), 'failed_waiting_user')
        with self.assertRaises(Conflict): self.core.resume(task, '不要开启第三轮')
        outbox = self.core.issue_export(self.project)
        self.assertEqual(len(outbox['issues']), 1)
        self.assertFalse(outbox['github_written'])

    def test_actual_missing_input_isolated_and_manual_recovery(self):
        failed = self.core.add_task(self.project, '缺失文件', 'integrity_check', config={'required_input': 'extra.txt'})
        other = self.core.create_project('其他项目', {'goal': '独立运行'})
        task_b = self.core.add_task(other, '清单', 'source_manifest')
        self.approve(); self.approve(other)
        self.execute(failed); self.execute(task_b)
        self.assertEqual(self.status(failed), 'failed_waiting_user')
        self.assertEqual(self.core.store.snapshot(other)['tasks'][0]['status'], 'checking')
        self.core.add_input(self.project, 'extra.txt', '真实补充文件')
        self.core.resume(failed, '补充extra.txt并确认原任务停止')
        self.execute(failed)
        self.assertEqual(self.status(failed), 'checking')

    def test_duplicate_dispatch_and_exclusive_resource_lock(self):
        started, release = threading.Event(), threading.Event()
        def blocking(kind, project, config, directory):
            started.set(); release.wait(5)
            return run_adapter(kind, project, config, directory)
        a = self.core.add_task(self.project, '独占A', 'source_manifest', lock_key='local:shared-tool')
        b = self.core.add_task(self.project, '独占B', 'source_manifest', lock_key='local:shared-tool')
        self.approve()
        with patch('workstation.core.run_adapter', blocking):
            try:
                run = self.core.dispatch(a); self.assertTrue(started.wait(3))
                self.assertEqual(self.core.dispatch(a), run)
                with self.assertRaises(Conflict): self.core.dispatch(b)
            finally: release.set()
            self.core.futures[run].result(10)
        self.execute(b)

    def test_dependency_invalidation_preserves_unrelated_branch(self):
        source = self.core.add_task(self.project, '来源A', 'source_manifest')
        dependent = self.core.add_task(self.project, '使用A', 'integrity_check', dependencies=[source])
        unrelated = self.core.add_task(self.project, '独立B', 'integrity_check')
        self.approve()
        for task in [source, dependent, unrelated]:
            self.execute(task); self.pass_reviews(task)
        affected = self.core.invalidate(source, '来源A版本变化')
        self.assertEqual(set(affected), {source, dependent})
        self.assertEqual(self.status(unrelated), 'checked')
        with self.assertRaises(Conflict): self.core.accept(self.project)

    def test_restart_keeps_checkpoint_and_lock_until_process_verification(self):
        task = self.core.add_task(self.project, '中断任务', 'source_manifest')
        self.approve(); self.core.close()
        with self.core.store.transaction() as db:
            db.execute("UPDATE tasks SET status='running',active_run='interrupted-run',checkpoint=? WHERE id=?",
                       (json.dumps({'input_hash': 'frozen'}), task))
            db.execute("INSERT INTO runs VALUES('interrupted-run',?,1,1,'author','running','frozen',NULL,?,NULL)", (task, time.time()))
            db.execute("INSERT INTO resource_locks VALUES('shared-session','interrupted-run')")
        self.core = Core(self.temp.name)
        self.assertEqual(self.status(task), 'failed_waiting_user')
        with self.assertRaises(Conflict): self.core.resume(task, '只记录说明不释放原进程')
        self.core.resume(task, '人工确认旧进程已经停止', old_process_checked=True)
        self.execute(task)
        self.assertEqual(self.status(task), 'checking')

    def test_worker_binding_and_plan_revision_block_old_approval(self):
        other = self.core.create_project('另一笔记本', {'goal': '专机执行'}, worker_id='laptop-B')
        task = self.core.add_task(other, '清单', 'source_manifest')
        self.approve(other)
        with self.assertRaises(Conflict): self.core.dispatch(task)
        local = self.core.add_task(self.project, '清单', 'source_manifest')
        self.approve()
        self.core.revise(self.project, {'goal': '新的正式要求'}, '用户调整目标')
        with self.assertRaises(Conflict): self.core.dispatch(local)

    def test_pinned_archify_really_produces_html_svg(self):
        self.assertTrue(capabilities()['architecture_render']['ready'], 'Required: pinned Archify capability configured')
        task = self.core.add_task(self.project, '真实架构图', 'architecture_render', role='R028')
        self.approve(); self.execute(task)
        self.assertEqual(self.status(task), 'checking')
        html = next(a for a in self.core.store.snapshot(self.project)['artifacts'] if a['name'] == 'architecture.html')
        self.assertIn('<svg', (Path(self.temp.name) / html['path']).read_text())


class GatewayTests(unittest.TestCase):
    def test_direct_mode_total_retry_budget_and_success(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(429) if len(calls) < 3 else httpx.Response(200, json={'choices': [{'message': {'content': '{"goals":["核对真实来源"]}'}}]})
        result = ask_gateway([], 'planning', base_url='https://fixture.invalid/v1', api_key='fixture', retry_owner='client', transport=httpx.MockTransport(handler))
        self.assertEqual(len(calls), 3); self.assertEqual(result['client_attempts'], 3)

    def test_gateway_owned_budget_never_stacks_and_401_never_retries(self):
        for code, owner in [(429, 'gateway'), (401, 'client'), (200, 'client')]:
            calls = []
            def handler(request):
                calls.append(request); return httpx.Response(code, json={'bad': 'not a valid goal draft'})
            with self.assertRaises(RuntimeError):
                ask_gateway([], 'planning', base_url='https://fixture.invalid/v1', api_key='fixture', retry_owner=owner, transport=httpx.MockTransport(handler))
            self.assertEqual(len(calls), 1)


class ApiTests(unittest.TestCase):
    def test_real_api_lifespan_create_dispatch_download_and_restart_persistence(self):
        with tempfile.TemporaryDirectory() as root:
            with TestClient(create_app(root)) as client:
                self.assertEqual(client.get('/').status_code, 200)
                body = client.post('/api/projects', json={'title': 'API真实文件验证', 'requirements': {'goal': '留存来源'}}).json()
                project = body['project']; identity = project['id']
                task = client.post('/api/projects/' + identity + '/tasks', json={'node': '输入清单', 'kind': 'source_manifest'}).json()['task_id']
                self.assertEqual(client.post('/api/tasks/' + task + '/dispatch', json={}).status_code, 409)
                self.assertEqual(client.post('/api/projects/' + identity + '/approve', json={'version': 1, 'plan_hash': project['plan_hash']}).status_code, 200)
                run = client.post('/api/tasks/' + task + '/dispatch', json={}).json()['run_id']
                client.app.state.core.futures[run].result(10)
                snapshot = client.get('/api/projects/' + identity).json()
                artifact = snapshot['artifacts'][0]
                data = client.get('/api/artifacts/' + artifact['id'] + '/download')
                self.assertEqual(digest(data.content), artifact['sha256'])
                self.assertEqual(client.get('/api/resources').json()['source_count'], 23)
            with TestClient(create_app(root)) as restarted:
                saved = restarted.get('/api/projects/' + identity).json()
                self.assertEqual(saved['tasks'][0]['status'], 'checking')
                self.assertEqual(saved['artifacts'][0]['sha256'], artifact['sha256'])


if __name__ == '__main__':
    unittest.main()
