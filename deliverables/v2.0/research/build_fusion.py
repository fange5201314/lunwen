"""Build a self-contained, simulated fusion laboratory from the user resource ledger."""
from pathlib import Path
import json,urllib.parse,re
ROOT=Path(__file__).resolve().parents[1]
priority_path=Path('/workspace/111-priority-resources.json')
if priority_path.exists():
 priority=json.load(open(priority_path))
else:
 audit_resources=json.load(open(ROOT/'research/111-resource-audit.json'))['resources']
 priority=[{'id':r['id'],'url':'Clippings/'+urllib.parse.quote(r['decoded_filename'])} for r in audit_resources]
curated=json.load(open(ROOT/'config/curated-resources.json'))
catalog=json.load(open(ROOT/'config/resource-catalog.json'))
repos={r['repo']:r for r in curated}
audit=json.load(open(ROOT/'research/111-resource-audit.json'))
audited={r['id']:r for r in audit['resources']}
for r in json.load(open(ROOT/'research/111-repo-evidence.json'))['repositories']:
 repos[r['repo']]={**repos.get(r['repo'],{}),**r,'url':'https://github.com/'+r['repo'],'evidence_level':'E2 · 固定提交README/核心协议核对；未运行接入'}
byid={r['id']:r for r in catalog}
for sid in ['GH-013','GH-034','GH-043','GH-004','GH-005']:
 r=byid[sid]
 if r['name'] not in repos:
  repos[r['name']]={'repo':r['name'],'url':r['url'],'source_ids':[sid],'commit':None,'license':'待核对','runtime_verified':False,'evidence_level':'上传台账摘要；仓库固定版本待复核'}
source_titles={'CL-0005':'Blender CLI 建模与动画','CL-0008':'PCB Skill / 电路板设计','CL-0004':'双 Shadow Mind 审计','CL-0009':'answer-me-with-html 可视化交付','CL-0010':'PI-Desktop 多模型与子 Agent 可视化','CL-0011':'Anneal 规格开发流水线','CL-0012':'DeepSeek 式项目维护与决策沉淀','CL-0014':'apk-reverse 软件研究技能','CL-0015':'Rovai 群聊式多 Agent 工作台','CL-0017':'UI Design Guide 界面设计','CL-0020':'Goalcraft 目标契约','CL-0021':'Base UI React 组件库','CL-0022':'Base UI React 组件库（同主题副本）','CL-0023':'PavedPath / GitHub Solution Research','CL-0024':'CF / Turnstile 自动化资料','CL-0025':'WebCodex MCP 本机协作','CL-0019':'Zotero 科研笔记与引用校验','CL-0006':'image2 学术答辩视觉策略','CL-0018':'Chromix 浏览器自动化资料','CL-0026':'AgentDock 远程工具运行时','CL-0007':'Keysmith 模型行为研究','CL-0013':'网站模块与证据溯源研究','CL-0016':'Co-Space 共享项目空间'}
roles=[{'id':'author','name':'主创 Agent','authority':'提出方案 / 制作成果，不可审计自己的成果'}, {'id':'researcher','name':'资料与事实 Agent','authority':'提供来源锚点，不直接批准最终成果'}, {'id':'engineer','name':'专业工程 Agent','authority':'原生工程与实验，受会话锁与工具权限约束'}, {'id':'evidence','name':'证据整理 Agent','authority':'产物封装、版本与引用关系'}, {'id':'structure-auditor','name':'结构质量审计者','authority':'独立会话，只读产物，检查结构/可复现/格式'}, {'id':'goal-auditor','name':'目标一致性审计者','authority':'独立会话，只读已批准目标，检查需求覆盖与边界'}, {'id':'human','name':'学生 / 导师','authority':'需求冻结、变更路线、恢复与最终交付批准'}]

def bp(key,title,tag,question,innovation,sids,repo_names,parallel,artifact,major,parameter,unit,baseline):
 steps=[{'id':key+'-contract','name':'目标与边界冻结','agents':['author','researcher'],'source_ids':['CL-0020','CL-0012'],'depends_on':[],'output_type':'GoalContract','mode':'human_gate'}, {'id':key+'-parallel','name':'并行研究与制作','agents':['researcher','engineer','author'],'source_ids':sids,'depends_on':[key+'-contract'],'output_type':artifact,'mode':'parallel','branches':parallel}, {'id':key+'-join','name':'类型化证据汇合','agents':['evidence'],'source_ids':['CL-0012'],'depends_on':[key+'-parallel'],'output_type':'EvidenceBundle','mode':'join'}, {'id':key+'-audit','name':'两名独立审计者','agents':['structure-auditor','goal-auditor'],'source_ids':['CL-0004'],'depends_on':[key+'-join'],'output_type':'AuditPair','mode':'parallel'}, {'id':key+'-human','name':'人工接受与发布','agents':['human'],'source_ids':[],'depends_on':[key+'-audit'],'output_type':'ReleaseDecision','mode':'human_gate'}]
 return {'id':key,'title':title,'tag':tag,'question':question,'innovation':innovation,'source_ids':sids,'repos':repo_names,'agents':roles,'steps':steps,'handoffs':[{'from':'author','to':'researcher','type':'GoalContract','required':['goal_id','acceptance_criteria','constraints','version','human_approval']},{'from':'researcher / engineer','to':'evidence','type':artifact,'required':['artifact_uri','sha256','native_format','source_anchor','tool_version','goal_version','test_result']},{'from':'evidence','to':'structure-auditor / goal-auditor','type':'EvidenceBundle','required':['claims','source_pages','parameters','depends_on','revision','author_id']},{'from':'structure-auditor / goal-auditor','to':'human','type':'AuditPair','required':['reviewer_id','review_session_id','independent_of_author','findings','decision']}], 'gates':[{'id':'G0','name':'冻结目标契约','owner':'human','rule':'目标、可检验条件、学校要求与数据范围已确认'}, {'id':'G1','name':'双审计收敛','owner':'human','rule':'两审计会话独立于作者；缺证据或任一拒绝则停止依赖'}, {'id':'G2','name':'批准变更与成果','owner':'human','rule':'受影响证据重新核对后批准新版本，发布前保留可编辑源文件'}], 'change_impact':{'parameter':parameter,'unit':unit,'baseline':baseline,'goal':['requirement_contract'],'edges':[['requirement_contract','control_algo'],['requirement_contract','cad_interface'],['requirement_contract','pcb_interface'],['requirement_contract','plc_project'],['control_algo','experiment'],['cad_interface','experiment'],['pcb_interface','experiment'],['plc_project','experiment'],['experiment','chapter'],['chapter','slides']], 'nodes':[{'id':'requirement_contract','name':'目标契约','type':'GoalContract'},{'id':'control_algo','name':'控制算法 / 计算规则','type':'AlgorithmSpec'},{'id':'cad_interface','name':'CAD 接口尺寸','type':'NativeCAD'},{'id':'pcb_interface','name':'PCB 接口与时序','type':'NetlistContract'},{'id':'plc_project','name':'PLC / 程序原生工程','type':'NativeProject'},{'id':'experiment','name':'实验日志与曲线','type':'TestEvidence'},{'id':'chapter','name':'论文章节与图表','type':'ChapterBinding'},{'id':'slides','name':'答辩页与问答','type':'PresentationBinding'},{'id':'literature','name':'原始文献库','type':'CitationRecord'},{'id':'decision_notes','name':'未被取代的决策笔记','type':'DecisionRecord'}]},'readiness':{'design':'资源机制已映射为设计契约','prototype':'离线示例可点击，状态在此浏览器保存','runtime':'全部执行示例模拟；未真实接入 Agent / API / 工程工具','blockers':['Clippings 正文与准确仓库身份补齐','适配器安装与合约自测','学校模板 / 专业工具版本 / 可用模型确认']},'major':major}
blueprints=[
 bp('goal','目标契约工厂','01 · 需求不漂移','怎样让“帮我做毕设”变成 Agent 能交接的可检验目标？','Goalcraft 拆目标，双 Shadow 审计分别对结构和目标发问，Notes 记录被否决理由。下一位 Agent 接到的是有效决定与证据包。',['CL-0020','CL-0004','CL-0012'],['xiaoyangtx996/goalcraft-skill','liu-zhengdong/pi-shadow-mind','czm15053/write-notes-like-deepseek','paperclipai/paperclip'],['任务书约束提取','验收指标编制','技术方案对照'],'GoalContractDraft','general','响应时限','ms',200),
 bp('cockpit','共享驾驶舱','02 · 讨论落到任务','多位学生与多模型怎样看见同一个项目、保留每个决定？','Co-Space 的共享空间 + PI 子 Agent 可视化 + Rovai 两轮会议，工作站保存唯一任务状态；Core 是唯一委派入口，Paperclip 是可选适配器。桌面端只提供执行与观察。',['CL-0016','CL-0010','CL-0015','CL-0025','CL-0026'],['paperclipai/paperclip','vastsa/PI-Desktop','murray17/rovai-ai','uvwt/agentdock'],['共享上下文制作','本机执行能力自测','方案异议收敛'],'SessionHandoff','general','响应时限','ms',200),
 bp('research','研究证据活页','03 · 引文能回到原页','论文一段结论能否回溯文献原页、翻译与使用版本？','Zotero/RSS 线索驱动 Paper Search 检索，Docling 切成可定位的证据单元，OfficeCLI 与 HTML 共享同一段落绑定。改一个结论即可找到使用它的章节。',['CL-0019','CL-0009','CL-0012'],['dr-dumpling/paper-search-cli','docling-project/docling','shilong20/getbib','iOfficeAI/OfficeCLI','the-shy123456/thesis-docx'],['文献去重与 DOI 核对','原文段落 / 表格解析','术语与翻译对照'],'CitationEvidence','general','响应时限','ms',200),
 bp('twin','跨专业数字样机','04 · 工程与论文同源','机械、PCB 与 PLC 各自做完，能否证明它们真正对得上？','把 Blender 场景作为可视化外壳，CAD 尺寸、PCB 引脚、PLC I/O 共享 InterfaceContract。并行产物先汇合做接口检查，再给章节与答辩同一份实验证据。',['CL-0005','CL-0008','CL-0006','CL-0009'],['Cai-aa/CAD-Agent-Hub','bulaofen0036-coder/TIA_Portal_Openness_MCP','johannesPettersson80/codesys-mcp-toolkit','jgraph/drawio-mcp','iOfficeAI/OfficeCLI'],['机械建模 / 渲染','PCB 网络表 / 引脚定义','PLC I/O 与互锁测试'],'InterfaceContract','mechatronics','响应时限','ms',200),
 bp('spec','规格开发流水线','05 · 开发不黑箱','编码 Agent 怎样复用 GitHub 解法，同时可解释取舍和验收？','GitHub Solution Research 先交 repo/issue/PR/代码证据，Anneal 作为唯一开发流水线，Trellis 只提供规格和上下文格式；双 Shadow 独立审计后写 Notes。',['CL-0011','CL-0023','CL-0004','CL-0012'],['mosonlab/anneal','mindfold-ai/Trellis','liu-zhengdong/pi-shadow-mind','czm15053/write-notes-like-deepseek'],['解决方案证据搜索','规格与模块契约编写','隔离工作区实现 / 测试'],'PatchEvidence','software','响应时限','ms',200),
 bp('defense','证据答辩剧场','06 · 讲故事不造事实','一套证据怎样产生可编辑 PPT、交互演示和反方问答？','image2 只设计视觉草稿，OfficeCLI 生成可编辑文字与数据图；HTML 做结论→原始证据的点击跳转，UI Guide 与 React 统一阅读层。答辩对手 Agent 只能引用证据提出质疑。',['CL-0006','CL-0009','CL-0017','CL-0021','CL-0022'],['iOfficeAI/OfficeCLI','the-shy123456/thesis-docx','tt-a1i/archify','jgraph/drawio-mcp'],['论证主线与讲稿','可编辑幻灯片制作','反方提问与来源核对'],'PresentationBinding','general','响应时限','ms',200),
 bp('software-lab','授权软件显微镜','07 · 还原机制与证据','如何研究自己的 APK / 网站，并形成可复现实验而非截图拼贴？','把 apk-reverse 与网站模块研究作为选装方法，模块树每个推断绑定可见源位置。UI 复现后用事实与目标双审计，输出机制报告与原创实现。',['CL-0014','CL-0013','CL-0023','CL-0017'],['uvwt/agentdock','mindfold-ai/Trellis','liu-zhengdong/pi-shadow-mind'],['自有 APK / 站点模块定位','机制笔记与行为对照','原创原型与可复现测试'],'SoftwareObservation','software','响应时限','ms',200)
]
# Resource usage is explicit even when a lead is not enabled in a runnable chain.
for b in blueprints:
 direct=[m['repo'] for sid in b['source_ids'] for m in audited[sid]['github_matches'] if m.get('commit') and m['repo'] in repos]
 b['repos']=list(dict.fromkeys(b['repos']+direct))
 b['protocol_contracts']=[c for c in audit['reusable_contracts'] if c['repo'] in b['repos']]
 b['readiness']['blockers']=['未提供的 Clippings 原始正文 / 媒体补齐','适配器安装与合约自测','学校模板 / 专业工具版本 / 可用模型确认']
 b['repo_relations']=[{'repo':n,'relation':'配套候选；不是 CL-0012 同源项目' if n=='czm15053/write-notes-like-deepseek' else ('直接来源仓库' if any(m['repo']==n for sid in b['source_ids'] for m in audited[sid]['github_matches']) else '已有精选配套能力')} for n in b['repos']]
 b['change_impact']['impact_classification']={'confirmed_stale':['requirement_contract','control_algo','plc_project','experiment','chapter','slides'],'needs_impact_review':['cad_interface','pcb_interface'],'unaffected':['literature','decision_notes']}
sources=[]
for r in priority:
 sid=r['id']; matches=[b['id'] for b in blueprints if sid in b['source_ids']]
 decoded=urllib.parse.unquote(r['url']).split('/')[-1].removesuffix('.md')
 decoded=re.sub(r'^111','',decoded)
 status='机制参考 · 待正文核验'
 note='以上传台账摘要为设计依据；未取得该 Clippings 正文，不能把文章描述当已验证能力。'
 if sid in ['CL-0018','CL-0024']: status='隔离评估 · 不进入主链';note='保留浏览器兼容性/访问边界研究线索；采集使用官方 API、用户授权会话与合法全文渠道。主链不依赖反拦截能力。'
 if sid=='CL-0007': status='暂缓生产接入';note='保留模型行为研究索引。生产链沿用已配置模型和有限同能力渠道重试，拒绝或能力不足交人工处理。'
 if sid=='CL-0008': status='专业选装 · 身份待核';note='台账仅有 PCB Skill 开源线索，尚无准确仓库身份；先定义 NetlistContract 与 DRC 证据，不宣称已接入。'
 if sid in ['CL-0017','CL-0005','CL-0006']: status='方法选装 · 正文 / 工具待补证'
 if sid=='CL-0012':note+=' 原帖未提供 GitHub 同源身份；write-notes-like-deepseek 是主题相近的配套候选，不能当作该文章对应项目。'
 verified=[m for m in audited[sid]['github_matches'] if m.get('commit')]
 if verified:status='设计采用 · 固定仓库核对 / 适配待自测'
 sources.append({'id':sid,'title':source_titles[sid],'original_title':decoded,'original_path':r['url'],'level':'E1 台账摘要'+(' / E2 对应仓库固定版本核对' if verified else ''),'status':status,'used_in':matches,'usage_note':note,'duplicate_of':'CL-0021' if sid=='CL-0022' else None,'source_index_ids':audited[sid]['clippings_index_ids'],'public_source_urls':audited[sid]['public_source_urls'],'github_matches':audited[sid]['github_matches'],'protocol_contracts':[c for c in audit['reusable_contracts'] if c['repo'] in [m['repo'] for m in verified]]})
data={'schema_version':'fusion-blueprints/1.0','edition':'111-priority-resource-fusion','simulation':True,'principles':['Workstation Core 保存唯一业务状态并派发；Paperclip / Rovai 作为待验证宿主适配器','一次开发选择一个主工作流；参考机制不另启调度器','作者与结构 / 目标审计者分离，审计会话独立，关卡由人类批准','API 最多 3 次共用请求预算；业务检查失败保存检查点并暂停依赖','111 标记是用户优先级，不是运行验证等级'],'source_count':23,'unique_source_topics':22,'sources':sources,'repos':[repos[k] for k in sorted({n for b in blueprints for n in b['repos']})],'blueprints':blueprints,'typed_evidence_schema':{'required':['artifact_uri','sha256','source_anchor','goal_version','parameter_version','tool_version','author_id','revision','depends_on','validation_status'],'artifact_uri':'由后端文件存储生成，本原型不写入真实工程','validation_status':['draft','stale','checks_passed','human_accepted','rejected']},'addons':[{'id':'pcb','name':'PCB 接口选装','source_ids':['CL-0008'],'requires':'准确 Skill 仓库 / 工具许可证 / 目标器件','artifact_type':'NetlistContract'},{'id':'desktop','name':'本机执行端选装','source_ids':['CL-0010','CL-0025','CL-0026'],'requires':'执行端二选一、权限自测与会话锁','artifact_type':'WorkerCapabilityReport'},{'id':'software','name':'自有软件研究选装','source_ids':['CL-0014','CL-0013'],'requires':'自有或已获授权的 APK / 网站样本与范围确认','artifact_type':'SoftwareObservation'}],'retry_policy':{'max_attempts_total':3,'retryable':['429','5xx','timeout'],'same_capability_only':True,'shared_gateway_budget':True,'business_failure_action':'save_checkpoint_pause_dependents_wait_human','tool_effect_commit':'at_most_once_by_idempotency_key'}}
data['shared_core']={'source_ids':['CL-0020','CL-0004','CL-0012'],'repos':['xiaoyangtx996/goalcraft-skill','liu-zhengdong/pi-shadow-mind','czm15053/write-notes-like-deepseek','paperclipai/paperclip','bestruirui/octopus'],'scope':'各配方共享的目标、审计、决策与请求预算机制；不另起调度器'}
all_repo_names=set(r['repo'] for r in data['repos'])
data['repos'] += [repos[n] for n in data['shared_core']['repos'] if n not in all_repo_names]
(ROOT/'config/fusion-blueprints.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
TEMPLATE=Path(__file__).with_name('fusion_template.html').read_text()
(ROOT/'资源融合实验室.html').write_text(TEMPLATE.replace('__FUSION_DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')))
print('Built',len(blueprints),'blueprints,',len(sources),'priority entries,',len(data['repos']),'repository mappings')
