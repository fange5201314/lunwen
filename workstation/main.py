from contextlib import asynccontextmanager
from pathlib import Path
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from .core import Core, Conflict
from .adapters import capabilities, REPO_ROOT


def create_app(data_root=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.core = Core(data_root or os.environ.get('THESIS_DATA_DIR', REPO_ROOT / '.local/workstation'))
        yield
        app.state.core.close()

    app = FastAPI(title='论文工作站 · 开发验证核心', version='0.1.0', lifespan=lifespan)

    @app.exception_handler(Conflict)
    async def conflict_handler(request, error):
        return JSONResponse(status_code=409, content={'detail': str(error)})

    @app.get('/')
    def index():
        return FileResponse(Path(__file__).parent / 'web/index.html')

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'edition': 'development_poc', 'worker_id': app.state.core.worker_id,
                'state_owner': 'workstation-core', 'capabilities': capabilities()}

    @app.get('/api/resources')
    def resources():
        import json
        path = REPO_ROOT / 'deliverables/v2.0/config/fusion-blueprints.json'
        return json.loads(path.read_text(encoding='utf-8'))

    @app.get('/api/model-bindings')
    def bindings():
        import json
        return json.loads((REPO_ROOT / 'config/model-bindings.example.json').read_text(encoding='utf-8'))

    @app.get('/api/projects')
    def projects():
        with app.state.core.store.transaction() as db:
            return [dict(r) for r in db.execute('SELECT id,title,worker_id,version,approved_version FROM projects ORDER BY created DESC')]

    @app.post('/api/projects', status_code=201)
    def create_project(body: dict):
        identifier = app.state.core.create_project(body.get('title'), body.get('requirements'), body.get('worker_id'))
        return app.state.core.store.snapshot(identifier)

    @app.get('/api/projects/{project_id}')
    def project(project_id: str):
        result = app.state.core.store.snapshot(project_id)
        if not result:
            raise HTTPException(404, '项目不存在')
        return result

    @app.post('/api/projects/{project_id}/approve')
    def approve(project_id: str, body: dict):
        app.state.core.approve(project_id, body.get('version'), body.get('plan_hash'))
        return {'status': 'approved'}

    @app.post('/api/projects/{project_id}/revise')
    def revise(project_id: str, body: dict):
        app.state.core.revise(project_id, body.get('requirements'), body.get('reason', ''))
        return {'status': 'awaiting_plan_approval'}

    @app.post('/api/projects/{project_id}/inputs')
    def input_text(project_id: str, body: dict):
        app.state.core.add_input(project_id, body.get('name'), body.get('content'))
        return {'status': 'stored'}

    @app.post('/api/projects/{project_id}/tasks', status_code=201)
    def add_task(project_id: str, body: dict):
        identifier = app.state.core.add_task(project_id, body.get('node'), body.get('kind'),
                    body.get('role', 'R009'), body.get('dependencies'), body.get('config'), body.get('lock_key'))
        return {'task_id': identifier}

    @app.post('/api/tasks/{task_id}/dispatch')
    def dispatch(task_id: str):
        return {'run_id': app.state.core.dispatch(task_id), 'completion': 'asynchronous; poll project state'}

    @app.get('/api/tasks/{task_id}/review-scope')
    def review_scope(task_id: str):
        return app.state.core.review_scope(task_id)

    @app.post('/api/tasks/{task_id}/reviews')
    def review(task_id: str, body: dict):
        app.state.core.review(task_id, body)
        return {'status': 'registered', 'note': 'Report supplied by caller; this does not claim a model was invoked.'}

    @app.post('/api/tasks/{task_id}/resume')
    def resume(task_id: str, body: dict):
        app.state.core.resume(task_id, body.get('reason', ''), body.get('patch', False), body.get('old_process_checked', False))
        return {'status': 'queued'}

    @app.post('/api/tasks/{task_id}/invalidate')
    def invalidate(task_id: str, body: dict):
        return {'affected_tasks': app.state.core.invalidate(task_id, body.get('reason', ''))}

    @app.post('/api/projects/{project_id}/decisions', status_code=201)
    def decision(project_id: str, body: dict):
        return {'decision_id': app.state.core.decision(project_id, body)}

    @app.post('/api/projects/{project_id}/accept')
    def accept(project_id: str):
        return app.state.core.accept(project_id)

    @app.get('/api/projects/{project_id}/issue-outbox')
    def issue_outbox(project_id: str):
        return app.state.core.issue_export(project_id)

    @app.get('/api/artifacts/{artifact_id}/download')
    def artifact(artifact_id: str):
        with app.state.core.store.transaction() as db:
            item = app.state.core.require(db, 'artifacts', artifact_id)
        path = (app.state.core.store.root / item['path']).resolve()
        if not path.is_relative_to(app.state.core.store.root) or not path.is_file():
            raise HTTPException(404, '产物已丢失')
        return FileResponse(path, filename=item['name'])

    return app


app = create_app()
