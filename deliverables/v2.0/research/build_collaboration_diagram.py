from pathlib import Path
import html,json
root=Path(__file__).parent.parent
scenes=[{'title':'多 Agent 的组队、讨论与成果交接','height':1420,'nodes':[
('control','R001 项目总控','任务图 / 项目作用域 / 关卡',345,40,270,70,'调度只依据持久状态；模型可提议任务图，确定性服务校验依赖、能力和关卡。','Project + Requirement → TaskDAG + TeamManifest','Paperclip角色、派发与适配器；工作站领域状态'),
('input','R002 / R003 输入与学校','任务书理解 / 模板 / 真实缺项',20,190,220,80,'区分硬性要求、设计建议和真实事实缺项；模板冲突进入待处理。','任务书与模板 → 来源位置与验收映射','上传v1.0 §2、§8'),
('repo','R011 开源搜索','主动检索 / 接口 / 许可证',255,190,220,80,'以明确问题、来源优先级和停止条件搜索；收藏介绍不代表本机能力已验证。','能力缺口 → RepoCandidate / 适配与自测计划','GitHub台账252条；固定提交README'),
('paper','R015 / R017 文献','真全文 / 近五年 / 选择理由',490,190,220,80,'元数据和真全文分开；只有摘要不能进入全文翻译。','任务主题 → LiteratureRecord + SourceArtifact','Paper Search CLI / getbib'),
('architect','R021 / R023 架构与骨架','备选路线 / 章节证据需求',725,190,220,80,'给技术路线、备选与取舍；每章列需要的工程证据与真实来源。','需求与证据 → PlanProposal + ChapterContract','Codeg分叉参考 / Research Units方法'),
('meeting','R006 证据会议 · R008 招募','独立提案 → 两轮收敛 → 决策',320,340,320,80,'先匹配已验证岗位；新增能力先面试；默认最多两轮会议，关键决定仍交用户。','成员提案 → DecisionProposal + 未决项','Rovai长期角色与协作方法'),
('plan','四区方案包 + 工程决策板','理解 / 路线 / 提纲引用 / 外文',320,480,320,80,'保留候选、否决理由与当前决定。本文信息仅为设计定义，不是真实执行记录。','方案建议 + 证据 → PlanVersion','DeepSeek Agent Notes / write-notes方法'),
('approve','G10 用户确认具体版本','重大变化必须重新确认',320,620,320,70,'没有真实全文、模板或关键事实时不开始对应生产任务；确认绑定plan_hash。','可验收方案 → PlanApproved','上传对话中用户确认要求'),
('translate','R016 / R018 / R019 / R020','解析 → 全文翻译 → 术语核验',190,760,270,80,'先原文对象清单再译文；保留段落、图表、公式、附录的映射与疑义。','SourceArtifact → TranslationSegments + ObjectLedger','Docling / 可选PDFMathTranslate / 模型API'),
('opening','R024 开题写作 / R021复核','学校栏目 / 真实引用 / 拟开展计划',500,760,270,80,'首版写研究计划；未进行的工程和实验不能用完成时包装。','确认方案 + 来源 → 开题结构稿','Research Harness任务方法 / 学校配置'),
('doc','R031 文档制作 + 确定性程序','原文 / 译文 / 开题 DOCX与PDF',320,910,320,80,'同一文件一个写入者；临时文件通过结构检查后登记不可变正式对象。','结构稿 + 学校模板 → ArtifactManifest','OfficeCLI / 可配置Word或LibreOffice'),
('check','R082 / R085 独立核验','来源 / 全文 / 术语 / 格式 / 逐页',320,1050,320,80,'作者与检查者分离；系统失败保存现场、暂停依赖和通知，不循环自修。','冻结文件 → CheckReport / 阻断项','thesis-docx + 确定性检查 + 专业复核'),
('accept','G16 待用户验收','检查通过不自动完成',320,1190,320,70,'验收绑定文件清单、哈希和方案版本；修改是明确新任务，不覆盖旧验收。','必交清单与检查 → Acceptance','用户明确的完成判定'),
('done','已完成 · 证据护照进入后续工程与论文','后续按计算机 → CAD → CAE → PLC扩展',250,1320,460,70,'本图是设计方案。实际能力、模板、全文、通知与专业软件需实机验证。','已验收前期材料 → 归档与后续任务','全部96岗位与215节点保留配置')], 'edges': [('control','input'),('control','repo'),('control','paper'),('control','architect'),('input','meeting'),('repo','meeting'),('paper','meeting'),('architect','meeting'),('meeting','plan'),('plan','approve'),('approve','translate'),('approve','opening'),('translate','doc'),('opening','doc'),('doc','check'),('check','accept'),('accept','done')]},
{'title':'两类失败：API有限切换，业务人工恢复','height':1140,'nodes':[
('run','运行中的 TaskRun','项目 / 输入 / 已确认方案 / 检查点',335,30,290,70,'任务执行保存日志、输入与checkpoint。其他独立项目拥有自己的状态。','TaskContract → RunEvent','唯一业务状态源'),
('api','API请求级故障','429 / 可重试5xx / 连接或断流',60,170,300,80,'只有没有已提交副作用、且同能力备用有效时可有限重试；流式片段隔离。','request_id → attempt_id','Octopus；当前README需实机故障注入'),
('business','业务 / 工具 / 质量失败','缺文件 / 漏译 / 编译或求解错误',600,170,300,80,'业务不自动纠错或换方案；系统检查失败和用户标失败触发相同暂停。','Error + outputs → FailureEvent','上传用户约定'),
('budget','一个重试预算拥有者','示例：总3次 / 90秒 / 同能力渠道',60,340,300,80,'SDK、网关、业务层不叠加重试；尊重Retry-After；工具副作用不自动重放。','剩余预算 → 可切换请求或失败','单一Octopus，AxonHub/GPT-Load作替代'),
('success','完整响应 + 去重核验','校验后提交一次，原任务继续',40,510,330,80,'不能把网关的HTTP200、空内容或部分Token当成功；核对tool_call_id和operation ledger。','完整响应 → 有效模型输出','响应暂存 / 结构Schema / 工具去重'),
('failure','失败现场 + 依赖隔离','业务立即 / API预算耗尽后',575,340,350,80,'停失败节点和下游；共享能力故障只影响其使用者；其他独立项目继续。','checkpoint + logs + files → 工单','TaskDAG / CapabilityCircuit'),
('notify','本机待处理 + 手机通知','提交 / 服务接受 / 投递失败 / 已查看',575,510,350,80,'手机未配置要显示未就绪；投递失败单独记录；不能拿200响应代替用户收到。','FailureEvent → NotificationOutbox','指定渠道适配器；当前未连接'),
('human','用户处理、记录原因与决定','修复渠道 / 补资料 / 调整工具或方案',575,680,350,80,'主要路线或文献更换产生新方案和新确认；普通修复记录可追溯恢复事件。','HumanAction → Decision / ResumeRequest','工程决策板与恢复控制台'),
('verify','检查点、版本、依赖与锁复核','重启先查外部进程；能力需已验证',335,850,360,80,'外部副作用状态不明转人工；锁过期先核对进程和fencing token；不把running直接当成功。','ResumeRequest → 新attempt或阻塞','数据库事务 + lease + operation ledger'),
('resume','最小有效节点恢复','旧失败、旧成果、旧验收永久保留',335,1020,360,80,'能真正resume才从检查点继续；否则从最小节点重跑；有效已验收成果不盲目重做。','有效checkpoint → 新Run / 继续观察','外部执行器声明resume_supported')], 'edges':[('run','api'),('run','business'),('api','budget'),('budget','success'),('budget','failure'),('business','failure'),('failure','notify'),('notify','human'),('human','verify'),('verify','resume')]}]
colors=['#ebe7fa','#e8f4ee','#e9f1fb','#fff1e5']
def svg(scene):
 nodes={n[0]:n for n in scene['nodes']};parts=[f'<svg viewBox="0 0 960 {scene["height"]}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(scene["title"])}"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6" fill="#9d91b7"/></marker></defs><g fill="none" stroke="#b5a9ca" stroke-width="1.4" marker-end="url(#arrow)">']
 for a,b in scene['edges']:
  x,y,w,h=nodes[a][3:7];xx,yy,ww,hh=nodes[b][3:7]
  if abs(y-yy)<30:
   sx=x+w;sy=y+h/2;tx=xx;ty=yy+hh/2;path=f'M{sx},{sy} H{tx}'
  else:
   sx=x+w/2;sy=y+h;tx=xx+ww/2;ty=yy;mid=(sy+ty)/2
   path=f'M{sx},{sy} V{mid} H{tx} V{ty}'
  parts.append(f'<path d="{path}"/>')
 parts.append('</g>')
 for i,n in enumerate(scene['nodes']):
  id,label,sub,x,y,w,h,desc,contract,source=n;fill=colors[i%4];parts.append(f'<g class="node" tabindex="0" role="button" data-node="{id}" onclick="inspect(\'{id}\')" onkeydown="if(event.key===\'Enter\')inspect(\'{id}\')"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" fill="{fill}" stroke="#d6cfea"/><text x="{x+w/2}" y="{y+29}" font-size="13" font-weight="600" text-anchor="middle" fill="#39344e">{html.escape(label)}</text><text x="{x+w/2}" y="{y+52}" font-size="10" text-anchor="middle" fill="#7a738a">{html.escape(sub)}</text></g>')
 parts.append('</svg>');return ''.join(parts)
for i,s in enumerate(scenes): (root/('多Agent协作.svg' if i==0 else '失败与恢复.svg')).write_text(svg(s))
(root/'config/collaboration-diagram.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2))
body='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>多Agent协作与故障恢复 · 设计图</title><style>body{margin:0;background:#f5f4f9;color:#29273b;font:14px/1.65 "Noto Sans CJK SC","Microsoft YaHei",sans-serif}header{max-width:1330px;margin:30px auto;padding:0 24px}h1{font-size:24px;margin:4px 0}p{font-size:12px;color:#898396}button{padding:9px 15px;border:1px solid #ded9eb;border-radius:9px;background:white;color:#7561a5;cursor:pointer;margin:0 7px 7px 0}button.active{background:#7561d9;color:white}.layout{max-width:1330px;margin:auto;padding:0 24px;display:grid;grid-template-columns:1fr 300px;gap:20px}.canvas{background:white;border:1px solid #e6e1ef;border-radius:15px;padding:20px}.canvas svg{width:100%;height:auto}.node{cursor:pointer}.node:hover rect,.node:focus rect{stroke:#7561d9;stroke-width:2.5}.panel{background:white;border:1px solid #e6e1ef;border-radius:15px;padding:24px;position:sticky;top:20px;height:max-content}.panel h2{font-size:17px}.panel label{font-size:10px;letter-spacing:2px;color:#8d7baa}.panel p{font-size:12px;color:#6d667e}a{color:#7561d9;text-decoration:none}@media(max-width:850px){.layout{grid-template-columns:1fr}.panel{position:static}}@media print{header button,.panel{display:none}.layout{display:block}.canvas{border:0}} </style><header><label style="font-size:11px;color:#8d7baa">THESIS ATELIER / ORCHESTRATION DESIGN</label><h1 id="title"></h1><p>点击岗位或状态，查看职责、输入输出与复用资源。全部为设计定义；没有真实Agent执行。</p><button id="b0" onclick="switchScene(0)">多Agent协作</button><button id="b1" onclick="switchScene(1)">失败与人工恢复</button><a href="可点击原型.html">返回原型 ↗</a></header><div class="layout"><div class="canvas" id="canvas"></div><aside class="panel" id="panel"></aside></div><script>const DATA=__DATA__;const SVG=__SVG__;let current=0;function esc(s){return String(s).replace(/[&<>]/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[x]))}function switchScene(i){current=i;document.getElementById('title').textContent=DATA[i].title;document.getElementById('canvas').innerHTML=SVG[i];document.getElementById('b0').className=i===0?'active':'';document.getElementById('b1').className=i===1?'active':'';inspect(DATA[i].nodes[0][0])}function inspect(id){let n=DATA[current].nodes.find(x=>x[0]===id);document.getElementById('panel').innerHTML='<label>ROLE / STATE CONTRACT</label><h2>'+esc(n[1])+'</h2><p>'+esc(n[2])+'</p><hr style="border:0;border-top:1px solid #eee;margin:20px 0"><label>职责与边界</label><p>'+esc(n[7])+'</p><label>输入 → 输出</label><p>'+esc(n[8])+'</p><label>复用来源</label><p>'+esc(n[9])+'</p>'}window.addEventListener('hashchange',()=>switchScene(location.hash==='#recovery'?1:0));switchScene(location.hash==='#recovery'?1:0);</script></html>'''
body=body.replace('__DATA__',json.dumps(scenes,ensure_ascii=False)).replace('__SVG__',json.dumps([svg(s) for s in scenes],ensure_ascii=False))
(root/'多Agent协作与恢复图.html').write_text(body)
print('Agent collaboration and recovery diagrams generated')
