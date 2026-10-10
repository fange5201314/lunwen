"""Build the offline, resource-derived fusion architecture and validate its interactions."""
from pathlib import Path
import argparse, functools, html, http.server, json, threading
ROOT=Path(__file__).resolve().parent.parent
E=html.escape

def node(id,title,sub,x,y,w=318,h=104,*,kind='control',inputs='',outputs='',sources=None,status='设计契约；运行时接入未验证',detail='',guard=''):
 return dict(id=id,title=title,sub=sub,x=x,y=y,w=w,h=h,kind=kind,inputs=inputs,outputs=outputs,sources=sources or [],status=status,detail=detail,guard=guard)

COMMON_STATUS='固定提交 README 已核对；尚未运行接入'
system=[
 node('resources','111 重点资源 · 可组合能力卡','23 条台账 → 去重成 22 组来源',35,75,420,kind='source',inputs='资源台账 CL 条目、GH 链接、来源摘要和证据等级',outputs='ResourceCapabilityCard：能力、接口、许可、适用任务、缺口、来源与验证等级',sources=['CL-0004…CL-0026：全部 23 条 111 前缀资料','GH 252 项索引 + 已固定提交的 34 个重点项目'],detail='原始台账的 111 是优先阅读标记，并非软件名称；CL-0021/0022 是同源 UI 条目。保留两条来源，合并一组设计能力。介绍文章、README 与真正可派发能力分开登记。',guard='没有定位的 repo/接口或缺失原文正文时，保存候选卡与补证据任务，不声称已接通。'),
 node('goal','Goalcraft · 可验证目标契约','目标 / 边界 / 检查 / 回滚',515,75,410,kind='source',inputs='任务书、学校模板、已有成果、用户优先级',outputs='RequirementContract vN：project_id、plan_version、范围、成功条件、EvidenceNeeds、允许动作、回滚点',sources=['CL-0020','GH-034 xiaoyangtx996/goalcraft-skill'],status=COMMON_STATUS,detail='把“做一个毕设”拆成可验收的契约；每条约束有来源位置、确认状态、检查方式和目标成果。Goalcraft SKILL 验收门中的前四门：G1无占位、G2命令真实、G3结果可核对、G4权限诚实；其余门与时限等上下游约束也保留。编译器将四门映射为契约检查，不让提示词直接承担业务派发。',guard='真实缺项、可设计项与已确认项分列；没有学校模板和全文不假造。'),
 node('compiler','组合蓝图编译器 · 工作站新增','能力卡 → 配方 → DAG + 证据需求',985,75,420,inputs='RequirementContract + 能力卡 + 资源融合配方 + 环境能力注册表',outputs='BlueprintProposal：TaskDAG、TeamManifest、ArtifactSchemas、EvidenceEdges、接入缺口',sources=['CL-0020 目标契约 + CL-0023 开源研究','CL-0011 规格流水线 + CL-0015 协作分工','原创整合服务；设计契约，尚无真实实现'],detail='将资源组合为目标契约、共享驾驶舱、研究证据活页、规格开发、数字样机、证据答辩和授权软件研究七类蓝图。可生成多候选，编译时做 Schema/环检测、许可证、输入、能力、资源锁和预算检查。',guard='Goalcraft四门必须由确定性检查和真实证据回答：不接受TODO占位、编造验证命令或隐瞒权限缺口。未经用户确认的蓝图仅为草案；只执行已确认 PlanVersion。'),
 node('cockpit','共享驾驶舱 · Co-Space / PI','同项目空间 · 人与 Agent 同步观察',35,265,420,kind='source',inputs='项目成员、授权会话、只读事件流、文件预览',outputs='会议请求、用户确认、暂停/恢复命令、项目空间视图',sources=['CL-0016 → JingxuanKang/cospace（新固定提交核对）','CL-0010 → vastsa/PI-Desktop','CL-0017 UI Guide（待定位）、CL-0021/0022 → gamecrafters-io/base-ui'],status='PI/Co-Space/base-ui README 已核对；运行接入与UI Guide来源待验证',detail='复用项目即空间、共同上下文、流式输出和子 Agent 观察。网页与桌面只持读模型；命令经 API 进入领域服务。共享上下文按项目/版本冻结，不能混用不同项目秘密。',guard='PI 是可选宿主，Co-Space 是空间方法；均无独立业务派发权。'),
 node('meeting','Rovai 证据会议 + 用户确认','独立提案 → 两轮收敛 → 决定',515,265,410,kind='source',inputs='候选蓝图、独立成员提案、支持/反对证据',outputs='DecisionProposal + 用户确认事件 + PlanApproved(plan_hash)',sources=['CL-0015 → murray17/rovai-ai','CL-0012 项目维护方法；GH-003 Notes 主题相关候选'],status=COMMON_STATUS,detail='会议由领域服务登记触发理由、参与岗位、两轮上限与终止条件。Rovai 的使命板和群聊用于协作参考，结论绑定 Notes；分歧不消失，明确交用户。',guard='会议讨论不绕过用户的路线/范围/外文更换确认，结束讨论不等于完成任务。'),
 node('domain','唯一业务状态源 · 领域服务','计划 / DAG / 决定 / 证据 / 验收',985,265,420,inputs='API 命令、PlanApproved、执行回调、检查报告、ResumeRequest',outputs='事务状态变更 + OutboxEvent + 可派发任务 + 前端读模型',sources=['原上传全流程 v1.0 的关卡与岗位契约','v3 Core：Python / FastAPI / SQLite 单机PoC'],detail='唯一持有 Project、Requirement、PlanVersion、TaskDAG、Decision、Evidence、Artifact、CheckRun、Acceptance。确定性关卡要求：确认版本有效、输入齐备、依赖有效、能力就绪、资源可用。',guard='Paperclip 的 issue 完成只能投影为运行结束；领域状态及用户验收由此服务决定。回调幂等、状态转换与 outbox 同事务。'),
 node('notes','决策记忆 · 双向版本关联','为什么选 / 为什么拒绝 / 何时重议',35,455,420,kind='source',inputs='目标契约、会议提案、设计取舍、实施与验证',outputs='DecisionRecord：候选、取舍、证据、影响、确认者、supersedes',sources=['CL-0012 项目维护原帖（不认定与Notes为同项目）','GH-003 czm15053/write-notes-like-deepseek'],status=COMMON_STATUS,detail='记录决定到工作站结构化数据库，再投影成可版本控制的 Notes。Notes 一头关联需求和蓝图，另一头关联成果/检查，以便半年后知道工程为何这样实现。',guard='Notes 文本是可读投影，数据库决定对象是主记录；笔记编辑不会直接改变已确认计划。'),
 node('paperclip','宿主适配器 · Paperclip / Rovai','Core-local 已运行；外部宿主待验证',515,455,410,kind='source',inputs='领域 outbox 中可领取 TaskContract、岗位、run_id、幂等键',outputs='绑定执行器的 Run、日志、结束/失败/取消回调',sources=['paperclipai/paperclip 固定提交 5badea4','CL-0015 群聊/使命协作方式'],status=COMMON_STATUS,detail='复用长期岗位、所有者、唤醒与适配器；岗位目录不是 96 个常驻推理进程。建议初始 4–8 推理槽，按项目公平轮转与渠道限速。',guard='领域服务唯一批准/冻结业务任务。接入先验证自主恢复钩子；不能拦截时替换派发适配器，不叠第二主流程。'),
 node('db','状态与事件 · SQLite / 后续中心数据库','领域 schema / outbox / 去重 / lease',985,455,420,kind='storage',inputs='命令事务、输入/方案哈希、事件序号、operation_id',outputs='版本化对象、只读快照、待派发 outbox、持久恢复记录',sources=['PostgreSQL / 工作站领域 schema','原上传要求：多项目隔离、暂停与恢复'],detail='任务状态、事件与 outbox 原子提交；Paperclip 表通过公开插件/API 关联，工作站不直接修改第三方内部表。SQLite 可用于单机小 PoC，正式方案以 PostgreSQL 并发与锁语义为准。',guard='业务状态与文件内容分离；事件流断连后按序号重放；执行器 lease 过期先核对外部进程和 fencing token。'),
 node('development','Anneal / Trellis · 规格开发单元','spec → 实施 → 测试 → 审核',35,645,420,kind='source',inputs='工作站开发需求/适配器缺口、明确 spec、Notes',outputs='代码 diff、测试证据、版本化适配器包、待独立审查 PR',sources=['CL-0011 / CL-0277 → mosonlab/anneal','GH-150 mindfold-ai/Trellis','CL-0004 / GH-013 → liu-zhengdong/pi-shadow-mind'],status=COMMON_STATUS,detail='在独立开发工作区建设工作站和新适配器；Anneal 流水线与 Trellis 规格作为可选单元，单个开发任务选一个主阶段流程。交付代码与测试后再做 capability 面试。',guard='不把 PR 合并或开发任务结束当毕业项目验收；双审计分别看结构坏味道与原目标达成。'),
 node('workers','按需 Agent + MCP / CLI 适配器','角色 × 宿主 × 能力 × 独立上下文',515,645,410,inputs='TaskContract：project、plan、inputs、capability、run、budget、checkpoint',outputs='RunEvent、原生文件、结构化日志、实际 tool/version、checkpoint',sources=['CL-0010 PI / Codex / Claude CLI 可选宿主','CL-0025 → yyjeqhc/webcodex；CL-0026 / GH-043 → uvwt/agentdock','GH FastMCP、既有适配器契约'],status='契约已设计；各真实宿主/工具需逐个自测',detail='研究员、工程员、文档员仅在任务运行时实例化。工具适配器不自主规划全项目；所有写入有 project_scope、资源锁、operation ledger，输出先暂存再提交。专业桌面执行使用 Windows Worker。',guard='能力必须有版本与小任务自测；不支持真正 resume 的执行器从最小有效节点重跑，状态未知的副作用待人工。'),
 node('storage','内容寻址文件库 · 原生工程','SHA-256 / 临时区 / 正式不可变对象',985,645,420,kind='storage',inputs='真实来源 PDF、代码/工程、数据、图像、DOCX/PDF/PPTX、日志',outputs='ArtifactManifest：content_hash、input_hash、run_id、tool_version、location',sources=['本地 FS 先行；可选 S3 兼容对象存储','原上传要求：原件/译文/工程与验收版本保留'],detail='哈希对象是正式内容；SQL 持有位置与护照。先写隔离临时目录，完整性/格式检查后提交。对象包含原生 CAD/PLC/PCB 工程，而不仅导出截图。',guard='同一目标文件一名写入者；验收绑定不可变文件清单，不覆盖原件和旧失败现场。'),
 node('engineering','数字样机 · 跨专业适配包','Blender + PCB + CAD + PLC',35,835,420,kind='source',inputs='控制参数、跨专业 InterfaceContract、机械/电子/PLC 限制',outputs='原生工程、接口校验、仿真/编译/测试日志、真实渲染',sources=['CL-0005 Blender CLI 创意示例','CL-0008 PCB Skill（正文/仓库待核对）','GH-006 CAD-Agent-Hub；TIA/CODESYS 专业桥'],status='Blender/PCB/CAD/PLC 实机接入与许可待自测',detail='把一个控制系统作为多视角数字样机：Blender 解释结构与动作，CAD 保存机械设计，PCB 校核采样/供电接口，PLC 验证控制逻辑。每个视角通过同一 InterfaceContract 引用时间/空间/电气参数。',guard='Blender 视觉模型不替代工程 CAD 精度和 CAE 求解；PCB 未找到原文与接口先设计占位契约，不能派发制作。'),
 node('gateway','Octopus · 唯一 API 重试预算','总 3 次 / 90 秒 · 同能力渠道',515,835,410,kind='api',inputs='request_id、模型能力、服务端凭据引用、总预算、已提交副作用状态',outputs='完整响应或明确 ApiExhausted；attempt 日志与计费',sources=['bestruirui/octopus 固定提交 d1a26bd','已有 CC-Switch / API 渠道配置'],status=COMMON_STATUS,detail='总次数包括初次请求；可恢复 429/连接/5xx 按 Retry-After 与剩余预算切换。业务 SDK 禁用额外自动重试；流式片段暂存隔离，完整 Schema 验证后只提交一次。',guard='请求级恢复不能自动更换工程方案。已提交副作用或未知工具结果不自动重放；全渠道失败保存 checkpoint 并暂停依赖。'),
 node('apis','模型 API · 按能力分工','研究 / 编码 / 审计 / 图像',985,835,420,kind='api',inputs='冻结任务上下文、prompt/version、model capability、预算',outputs='结构化提案/翻译/代码/图像 + token/耗时记录',sources=['用户已有 API；模型能力矩阵','CL-0006 image2 学术演示方法'],status='渠道已有线索；模型协议/图像接口需实际验证',detail='选择模型以能力自测为准；规划、生成、审查可用不同模型，但换模型保留任务身份与证据约束。图像只承担说明/版面插画；数值与引文仍来自可核证据。',guard='凭据只在服务端/系统钥匙串；前端、日志和正式产物不包含 API key。'),
 node('outcomes','一份证据 · 三类成果投影','论文 / 工程 / 答辩与 HTML',35,1025,420,kind='output',inputs='通过检查的 EvidenceGraph、学校模板、图像/原生工程',outputs='OfficeCLI DOCX/PDF/PPTX + 原生工程包 + 交互 HTML + 成果护照',sources=['CL-0009 → QingYunA/answer-me-with-html（SKILL已核对，未运行）','CL-0006 image2 演示视觉方法','GH-125 OfficeCLI；GH thesis-docx 独立检查'],status='本交互架构 HTML 已实现；外部成果工具运行接入未验证',detail='论文章节、答辩页和交互演示引用同一 evidence_id / revision。image2 为视觉叙事候选，OfficeCLI 保留可编辑文字和图表，HTML 展示可点的证据路径。',guard='不让图像生成代造实验数值、引文或原生工程。最终每个具体文件版本需独立检查与用户验收。'),
 node('evidence','版本化证据图谱 · 成果护照','Requirement → Task → Artifact → Claim',515,1025,410,kind='evidence',inputs='真实来源、工程/实验数据、文件护照、独立 CheckRun',outputs='EvidenceRevision：project_id、plan_version、generation、input_hash、output_hash；supports/derived_from/uses_parameter、章节/页引用',sources=['CL-0019 / CL-0358 科研方法合集','GH-094 Docling + Paper Search/getbib + Zotero 方法','工作站原创 evidence/claim 版本图'],detail='证据图是 PostgreSQL 中的有向版本关系；每条论断只引用真实证据，保存内容哈希、输入参数与检查。向量检索是辅助索引，不当作事实主库。',guard='论文、工程、答辩的每次投影冻结图谱版本。来源不足时登记待证实，不能用模型自评补足。'),
 node('audits','双 shadow + 独立来源/专业核验','结构与质量 × 成功目标一致性',985,1025,420,kind='audit',inputs='冻结成果、RequirementContract、真实日志、源文件',outputs='StructureAudit + GoalAudit + Source/ProfessionalCheckReport',sources=['CL-0004 / GH-013 → liu-zhengdong/pi-shadow-mind','CL-0019 来源/引用核验；thesis-docx 文档检查'],status='方法已落实为契约；审查工具与岗位尚未运行',detail='按 pi-shadow 实际 DESIGN 将独立审计设为 read-only，按 generation 聚合 final_response，并限制 max_parallel。shadow A 检查结构/接口，shadow B 检查原始目标。报告显式 pass/fail/unknown 与检查证据；旧代报告拒收，沉默不代表通过。原项目不提供统一文件锁，领域服务需补锁。',guard='审者不审自己的产物；每份报告核对project_id/plan_version/generation/input_hash/output_hash，旧版本与缺报告阻断。checks passed 不自动 acceptance；失败暂停人工处理。'),
 node('change','需求变化雷达 · 精确失效传播','参数 diff → 证据引用 → 最小重验范围',515,1200,410,100,kind='evidence',inputs='新的 RequirementContract、参数/输入哈希变化、当前证据边',outputs='ImpactReport：确定过期、待核对、保持有效 + 新计划/重验提案',sources=['CL-0020 可回滚契约 + CL-0012 决策版本','原创：跨成果失效传播服务'],detail='示例：响应时限 200 ms→100 ms。沿实际 uses_parameter 边标记控制算法/PLC/实验/图表/论文/答辩待重验；PCB采样和CAD安装接口先做影响核对，文献库保持有效。',guard='传播标记不等于自动重跑。重大范围变动须用户确认，已验收历史永久保留。')
,
 node('authorized','授权软件研究 · 专业可选单元','结构还原 / 合法测试 / 兼容性证据',35,1200,420,100,kind='source',inputs='自有或有授权的软件/网页、明确研究范围、可访问来源',outputs='模块树、src/lines出处、接口笔记、合法测试与兼容性报告',sources=['CL-0013 → boyang-hu/website-rebuild-skill；CL-0014 → newliver666/apk-reverse','CL-0018/GH-004 Chromix 兼容性候选','CL-0024 过盾、CL-0007 Keysmith：登记来源，不纳入默认执行'],status='网站/apk/Chromix README已核对；运行能力与授权范围待验证',detail='面向计算机专业的有授权软件架构研究：把来源定位、结构分析和本地验证作为证据单元。浏览器兼容性工具按合法可访问站点使用，遇访问限制转官方API、人工导入或待处理。',guard='CL-0024和CL-0007的绕过性宣传不自动转为生产能力；保留资源记录与取舍理由，不把全部资源强行安装。'),
 node('repo_research','PavedPath · 开源方案证据链','本地问题 → repo/issue/PR → 最小验证',985,1200,420,100,kind='source',inputs='明确本地问题、当前代码/环境、缺口与停止条件',outputs='RepoCandidate、rejected_options、最小适配diff、真实验证命令/日志',sources=['CL-0023 → Jia-Ethan/pavedpath-code / SKILL协议','GH台账与固定commit、issue、merged PR、源代码证据'],status='SKILL协议本次已核对；Agent运行接入未验证',detail='先理解本地问题，按issue/merged PR/源码定位候选，保留为何拒绝其他方案；最小适配后必须本地验证。将可靠新方案交 capability 面试，成为下一代蓝图能力卡。',guard='controller复核来源与验证命令；链接数量、star和README宣传不能替代真实验证证据。')
]
# Control edges are intentionally one-way; storage and audit feedback are events, never a second scheduler.
system_edges=[('resources','goal','资料→约束'),('goal','compiler','契约'),('compiler','domain','蓝图候选'),('cockpit','meeting','人机协作'),('meeting','domain','确认 plan_hash'),('notes','meeting','决定上下文','secondary'),('domain','paperclip','仅可派发任务'),('domain','db','事务 / outbox','secondary'),('paperclip','workers','TaskContract'),('development','workers','已验证适配包','secondary'),('engineering','workers','能力绑定','secondary'),('workers','storage','暂存→正式对象','secondary'),('workers','gateway','request_id'),('gateway','apis','总预算共享'),('workers','evidence','成果 / 实际日志','secondary'),('storage','evidence','Manifest','secondary'),('evidence','outcomes','同源多投影'),('evidence','audits','冻结证据'),('audits','domain','检查事件 / 关卡','secondary'),('evidence','change','参数引用'),('change','domain','影响 / 重确认','secondary'),('repo_research','workers','研究任务/能力面试','secondary'),('authorized','outcomes','授权研究成果','secondary')]

ev_nodes=[
 node('requirement_contract','目标契约 v2 → v3','响应时限：200 ms → 100 ms',545,65,380,100,kind='source',inputs='用户明确的新约束与变更原因',outputs='RequirementRevision + 参数 diff + 影响报告',sources=['CL-0020 / GH-034 Goalcraft','CL-0012 / GH-003 Notes'],detail='变更引用同一 parameter_id=response_deadline_ms。只在明确登记 uses_parameter 的节点传播。这里是架构示例，不是真实验结论。',guard='先影响分析与必要的计划重确认，再创建重验任务。'),
 node('library','文献库 / 学校模板','未引用时限参数 → 保持有效',35,65,390,100,kind='storage',inputs='已有真实全文与模板版本',outputs='冻结来源对象仍可引用',sources=['CL-0019 科研合集','Docling / Paper Search / getbib'],detail='新控制性能约束不自动让所有文献、译文和学校模板过期。若变更使某论点依据不足，才创建有停止条件的新研究任务。',guard='独立项目和未受影响资料继续可用。'),
 node('control_algo','控制算法 / 任务调度','直接使用响应时限 → 确定过期',35,270,318,104,kind='evidence',inputs='response_deadline_ms、输入数据、代码版本',outputs='新算法候选与实际性能测试证据',sources=['CL-0011 规格开发','CL-0004 双审计'],detail='旧实现的性能检查证书使用200ms成功条件；100ms目标需重验实际端到端日志。',guard='过期标记不直接生成成功结果，也不自动重跑失败测试。'),
 node('cad_interface','CAD 安装/机械接口','安装位置、惯量关联 → 待核对',395,270,318,104,kind='source',inputs='传感器位置、安装刚度、活动范围 InterfaceContract',outputs='影响审计；有实证关联才更新模型/重验',sources=['GH-006 CAD-Agent-Hub','CL-0005 Blender 解释性视图'],detail='机械接口可能影响控制动态，但响应时限变更并不必然改变几何。先核对有向参数关联和实际专业说明。',guard='没有真实影响证据时保持既有CAD有效。'),
 node('pcb_interface','PCB 采样/通信接口','采样周期、延迟预算 → 待核对',755,270,318,104,kind='source',inputs='采样率、ADC/通信时延、供电约束',outputs='延迟预算核对；必要时原生PCB修改提案',sources=['CL-0008 PCB Skill（正文待补）'],status='来源为文章摘要；repo/接口与工具未验证',detail='新的总时限可能要求重新分配电子采样和通信预算；只有具体参数值/限制受影响才标过期。',guard='缺少PCB工具接入时只产影响报告和待接入工单。'),
 node('plc_project','PLC 原生工程 / 扫描周期','程序时序证书 → 确定过期',1115,270,318,104,kind='evidence',inputs='PLC扫描周期、总响应预算、冻结程序',outputs='真实编译/时序验证日志 + 新工程版本',sources=['TIA Openness / CODESYS 专业桥','上传全流程专业节点'],detail='原生工程与扫描周期/通信链路共同验证100ms条件，截图和模型自评不能替代真实检查。',guard='PLC能力与许可未验证时等待，不虚构硬件数据。'),
 node('experiment','端到端实验 / 仿真证据','冻结输入、环境、程序、参数',545,460,380,104,kind='evidence',inputs='工程版本 + ParameterSet v3 + CheckContract',outputs='原始日志、测量数据、独立检查报告',sources=['数字样机组合配方','CL-0004 目标一致性审计'],detail='保存每次采样原始数据、程序/硬件版本与工具。失败进入恢复控制台，不能自动调参直到过关。',guard='任务输入改变后旧证据保留历史，但不再支持新100ms论断。'),
 node('charts','性能图表 / 结果论断','derived_from 实验版本',245,650,360,104,kind='evidence',inputs='真实100ms条件的实验数据与脚本',outputs='数据图表与 ClaimRevision + 脚本 hash',sources=['版本化证据图谱','OfficeCLI 可编辑图表'],detail='图表引用数据源和处理脚本；新结果未通过时不能沿用200ms条件下的达标结论。',guard='模型可以解释图表，不能凭空填充测量数值。'),
 node('passport','成果护照 / 原生工程包','Manifest + 输入哈希 + CheckRun',850,650,360,104,kind='storage',inputs='原生工程、实验、日志与独立检查',outputs='可验收的冻结文件版本清单',sources=['领域 ArtifactManifest','FS 内容寻址库'],detail='工程包与文字成果共享证据revision；旧验收绑定旧清单，新版本需要新确认。',guard='对原生CAD/PCB/PLC文件逐类检查，不只检查文件存在。'),
 node('chapter','论文章节与开题修订','论断引用 evidence_revision',35,840,390,104,kind='output',inputs='目标/方法/结果、证据与真实引用',outputs='按学校模板的结构稿 / DOCX / PDF',sources=['CL-0019 科研资料','GH-125 OfficeCLI / thesis-docx'],detail='更新受影响的性能指标、结果图和相关讨论；没有引用该变更的研究背景、全文译文可以保持有效。',guard='明确拟开展与已完成；独立来源/格式审查后待用户验收。'),
 node('slides','答辩 PPT / 视觉故事','同源图表 + 可编辑说明',540,840,390,104,kind='output',inputs='已核验图表、论断、讲述提纲',outputs='PPTX/PDF + 图片来源标记',sources=['CL-0006 image2 演示视觉方法','GH-125 OfficeCLI'],status='方法候选；API与工具接入未验证',detail='使用image2设计视觉草稿，正式数值图表来自证据，文字保留可编辑。幻灯片上的“100ms达标”必须引用新的检查结果。',guard='图像不是测量证据，不能自动渲染虚假结果。'),
 node('html_story','交互 HTML / 数字样机演示','点论断 → 数据 → 工程 → 决定',1045,840,390,104,kind='output',inputs='冻结证据图谱与成果护照',outputs='离线可点击演示 + evidence_id 跳转',sources=['CL-0009 → QingYunA/answer-me-with-html SKILL（本次核对）','CL-0005 Blender 解说型模型'],status='本架构交互 HTML 已实现；Skill源码已核对，运行接入待验证',detail='依据 answer-me-with-html SKILL 使用 #am-source 作为真实来源块、按 panel patch 更新局部区域，并用 +/-/~ 对照变更。代码草图 sketch 的 src/lines 只引用真实本地路径与行号。正式 HTML 引用同一 evidence_revision；视觉模型与原生工程分开标识。',guard='未得到有效新证据时展示待重验标签。'),
 node('acceptance','新版本检查 + 用户验收','历史有效；新版本单独确认',545,1040,380,104,kind='audit',inputs='新ArtifactManifest + 独立CheckReport',outputs='Acceptance：user、plan_hash、文件hash、证据revision',sources=['原用户要求：文件具体版本人工验收','CL-0004 双shadow检查方法'],detail='用户确认具体文件版本后才算完成。不同投影中的参数、图表和论断自动一致性检查；用户验收不覆盖历史。',guard='新需求影响分析、重验方案和重大路线改变等待明确确认。')]
ev_edges=[('requirement_contract','control_algo','uses_parameter'),('requirement_contract','cad_interface','影响核对','review'),('requirement_contract','pcb_interface','影响核对','review'),('requirement_contract','plc_project','uses_parameter'),('control_algo','experiment','程序版本'),('cad_interface','experiment','接口证据','review'),('pcb_interface','experiment','接口证据','review'),('plc_project','experiment','时序日志'),('experiment','charts','derived_from'),('experiment','passport','Manifest'),('charts','chapter','supports'),('charts','slides','supports'),('charts','html_story','supports'),('passport','acceptance','文件版本'),('chapter','acceptance','文件hash'),('slides','acceptance','文件hash'),('html_story','acceptance','图谱版本')]

recovery=[
 node('run','当前 TaskRun / Operation Ledger','冻结输入与 PlanVersion',535,65,390,104,inputs='TaskContract + checkpoint + operation_id',outputs='正在运行的 task / 外部进程与副作用记录',sources=['领域 TaskRun 状态机','Paperclip Run 适配器'],detail='进程心跳、租约与副作用状态属于持久任务记录。客户端断开不会将running直接改为成功。',guard='共享能力故障只暂停该能力依赖者；独立项目继续。'),
 node('api_error','API 请求故障','429 / 可恢复5xx / 连接断流',100,255,400,104,kind='api',inputs='request_id + 错误分类 + 流式暂存',outputs='同一个总预算中的下一 attempt 或 ApiExhausted',sources=['Octopus / 一个预算拥有者'],detail='请求级错误才可进入有限恢复；工具调用已发生的副作用先核查状态。',guard='HTTP200空内容或截断响应不算成功。'),
 node('business_error','业务 / 工具 / 审查失败','漏译 / 缺文件 / 编译 / 检查未通过',970,255,400,104,kind='audit',inputs='RunError 或独立 CheckReport fail',outputs='FailureEvent + 暂停失败节点及依赖',sources=['原用户确认的失败即停约定','CL-0004 双shadow审计'],detail='工具与质量错误不自动修改方案并循环重试。用户主动标失败也使用同一失败协议。',guard='其他独立项目与不使用故障能力的任务继续。'),
 node('api_budget','统一预算 · 总3次 / 90秒','初次请求计入总次数',100,445,400,104,kind='api',inputs='剩余次数/期限 + Retry-After + 同能力备用',outputs='完整可验证响应或预算耗尽',sources=['Octopus网关候选；SDK重试关闭'],status='设计值；故障注入与真实接口待验证',detail='网关、SDK与业务层共享同一个预算；全渠道失败明确返回，不能重复包裹重试器。',guard='无可用同能力备用时直接失败，不降低任务质量约束。'),
 node('committed','完整响应 · 去重后提交一次','部分流与重复tool_call_id隔离',100,635,400,104,kind='evidence',inputs='完整 Schema 响应 + operation ledger',outputs='当前 TaskRun继续；一次性工具提交',sources=['AdapterContract + response staging'],detail='既有成功提交不会因为重发请求再执行一遍。可读请求与有副作用操作使用不同重放规则。',guard='副作用状态未知进入人工核对，不默默重放。'),
 node('paused','保存现场 · PAUSED_FAILED','checkpoint / 日志 / 已有文件 / 依赖',970,445,400,104,kind='storage',inputs='业务失败或ApiExhausted',outputs='冻结失败现场 + 下游BLOCKED + 待处理工单',sources=['PostgreSQL事务事件与outbox','内容寻址文件库'],detail='记录输入版本、错误原文、最后有效checkpoint、临时与正式文件、依赖影响和能力状态；失败历史不可抹除。',guard='只有当前项目依赖和共享故障能力被隔离。'),
 node('notify','本机工单 + 可选手机通知','投递/失败/已查看分别记录',970,635,400,104,inputs='FailureEvent + 通知配置引用',outputs='NotificationOutbox + RecoveryTicket',sources=['原用户需求：可见失败与人工处理','通知适配器：尚未连接'],status='通知渠道未接通；原型仅模拟',detail='手机未配置标未就绪。投递失败单独存事件，恢复控制台始终能看见工单。',guard='服务接受或HTTP200不能代表用户已读。'),
 node('human','人工处理 + 决策留痕','修API / 补资料 / 修环境 / 改计划',535,825,390,104,kind='source',inputs='失败工单、处理原因与恢复请求',outputs='DecisionRecord + ResumeRequest；必要时新PlanApproved',sources=['CL-0012 / GH-003 Notes','CL-0020 可回滚目标契约'],detail='普通渠道修复保存恢复说明；更换路线、外文或范围产生新的计划与确认，旧决定通过supersedes关联保留。',guard='保持问题未解决时继续等待，不把无限“继续”当恢复。'),
 node('resume_gate','恢复关卡 · 版本与外部状态核对','Plan / 输入 / 依赖 / 能力 / 锁',535,1010,390,104,kind='audit',inputs='ResumeRequest + checkpoint + 现有外部进程',outputs='真resume / 最小节点新Run / 人工阻断原因',sources=['领域确定性关卡','能力注册表 resume_supported'],detail='核对方案版本、输入哈希、有效上游、真实能力、外部进程、lease/fencing token与operation ledger。启动时扫描遗留运行并接管或转待处理。',guard='无resume能力明确从最小有效节点重跑；不盲目重做已验收资料。')
]
recovery_edges=[('run','api_error','请求异常'),('run','business_error','业务失败'),('api_error','api_budget','唯一预算'),('api_budget','committed','完整通过'),('api_budget','paused','耗尽 / 未知','secondary'),('business_error','paused','立即暂停'),('paused','notify','outbox'),('notify','human','明确处理'),('human','resume_gate','ResumeRequest'),('resume_gate','run','新attempt / 真resume','secondary')]

SCENES=[dict(id='system',title='资源融合的单一编排架构',subtitle='资料不只进收藏夹：编译为目标、任务、角色、接口与证据契约。',width=1440,height=1340,nodes=system,edges=system_edges),dict(id='evidence',title='需求变化如何影响工程、论文与答辩',subtitle='响应时限 200 ms → 100 ms：沿实际引用传播；确定过期、待核对、保持有效分别显示。',width=1470,height=1180,nodes=ev_nodes,edges=ev_edges),dict(id='recovery',title='请求有限重试 · 业务暂停与人工恢复',subtitle='恢复机制不改任务目标；业务失败保存现场，人工处理后从最小有效节点恢复。',width=1470,height=1160,nodes=recovery,edges=recovery_edges)]
COLORS={'source':('#e8ecfd','#6053bc'),'control':('#e9f2fa','#3167a4'),'storage':('#e8f4ee','#367658'),'api':('#fff2dd','#aa7520'),'evidence':('#e9f5f2','#287c75'),'audit':('#fbece6','#b96a47'),'output':('#f0eafb','#8061bd')}

def edge_route(a,b):
 # Nearby rows route through their empty horizontal gap; skipped rows route through a side gutter.
 ax,ay,aw,ah=a['x'],a['y'],a['w'],a['h']; bx,by,bw,bh=b['x'],b['y'],b['w'],b['h']
 if abs(ay-by)<40:
  if bx>ax: sx,sy,tx,ty=ax+aw,ay+ah/2,bx,by+bh/2
  else: sx,sy,tx,ty=ax,ay+ah/2,bx+bw,by+bh/2
  return f'M{sx},{sy} H{tx}',(sx+tx)/2,sy-8
 if abs(by-ay)<=225:
  sx,tx=ax+aw/2,bx+bw/2
  sy,ty=(ay+ah,by) if by>ay else (ay,by+bh)
  mid=(sy+ty)/2
  return f'M{sx},{sy} V{mid} H{tx} V{ty}',(sx+tx)/2,mid-7
 if abs(ax-bx)<30:
  lane=ax-24; sx,sy,tx,ty=ax,ay+ah/2,bx,by+bh/2
 else:
  # Use a gutter between columns, never run an edge through an intermediate node.
  left,right=(a,b) if ax<bx else (b,a)
  lane=(left['x']+left['w']+right['x'])/2
  sx,sy=(ax+aw,ay+ah/2) if ax<bx else (ax,ay+ah/2)
  tx,ty=(bx,by+bh/2) if bx>ax else (bx+bw,by+bh/2)
 return f'M{sx},{sy} H{lane} V{ty} H{tx}',lane+6,(sy+ty)/2

def svg(scene):
 ids={n['id']:n for n in scene['nodes']};p=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {scene["width"]} {scene["height"]}" role="img" aria-label="{E(scene["title"])}"><defs><marker id="arr-{scene["id"]}" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto-start-reverse"><path d="M0,0 L7,3 L0,6" fill="context-stroke"/></marker></defs><style>text{{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif}}.node{{cursor:pointer}}.node:focus rect,.node:hover rect{{stroke-width:3}}.node.selected rect{{stroke:#6053bc;stroke-width:3}}.muted{{opacity:.21}}.impact rect{{fill:#fff0e9;stroke:#d66d47;stroke-width:3}}.review rect{{fill:#fff8df;stroke:#c5932f;stroke-width:3}}.safe rect{{fill:#e6f6ee;stroke:#3f9971;stroke-width:3}}.edge.impact path{{stroke:#d66d47;stroke-width:3}}.edge.review path{{stroke:#c5932f;stroke-width:2.5}}</style><rect width="100%" height="100%" fill="#fff"/><text x="35" y="31" font-size="15" font-weight="700" fill="#474360">{E(scene["title"])}</text><text x="35" y="52" font-size="11" fill="#868294">{E(scene["subtitle"])}</text>']
 for e in scene['edges']:
  aid,bid,label=e[:3];style=e[3] if len(e)>3 else '';route,x,y=edge_route(ids[aid],ids[bid]);color='#c89f48' if style=='review' else '#9aa4b8';dash='stroke-dasharray="5 4"' if style in ('secondary','review') else ''
  p.append(f'<g class="edge" data-edge="{aid}|{bid}"><path d="{route}" fill="none" stroke="{color}" stroke-width="1.6" {dash} marker-end="url(#arr-{scene["id"]})"/><text x="{x}" y="{y}" text-anchor="middle" font-size="9" fill="#777589" paint-order="stroke" stroke="#fff" stroke-width="4">{E(label)}</text></g>')
 for n in scene['nodes']:
  bg,stroke=COLORS[n['kind']];x,y,w,h=[n[k] for k in ('x','y','w','h')]
  title_size=13 if len(n['title'])>27 else 14
  source=' · '.join(s.split(' ')[0] for s in n['sources'][:2])
  if len(source)>50:source=source[:47]+'…'
  p.append(f'<g class="node" data-node="{n["id"]}" role="button" tabindex="0" aria-label="{E(n["title"])}" onclick="window.inspectNode&amp;&amp;inspectNode(\'{n["id"]}\')" onkeydown="if(event.key===\'Enter\'&amp;&amp;window.inspectNode)inspectNode(\'{n["id"]}\')"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="15" fill="{bg}" stroke="{stroke}" stroke-width="1.2"/><text x="{x+18}" y="{y+28}" font-size="{title_size}" font-weight="700" fill="#302d45">{E(n["title"])}</text><text x="{x+18}" y="{y+53}" font-size="11.5" fill="#59556c">{E(n["sub"])}</text><text x="{x+18}" y="{y+79}" font-size="9" fill="{stroke}">{E(source)}</text></g>')
 p.append(f'<text x="35" y="{scene["height"]-18}" font-size="10" fill="#8d889b">v2.1 / 2026-10-09 · 设计定义与离线交互已实现；Agent、模型与专业工具运行接入需自测。实线：主路径；虚线：引用、回调或待核对。</text></svg>')
 return ''.join(p)

HTML='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>111 资源融合编排架构 · THESIS ATELIER</title><style>
:root{--ink:#27253c;--muted:#77748b;--accent:#6353b8}*{box-sizing:border-box}body{margin:0;background:#f5f5fa;color:var(--ink);font:14px/1.65 "Noto Sans CJK SC","Microsoft YaHei",system-ui,sans-serif}header{max-width:1820px;margin:auto;padding:24px 30px 17px}.eyebrow{font-size:11px;color:var(--accent);letter-spacing:2px}h1{margin:7px 0 5px;font-size:25px;font-weight:700}header p{max-width:1040px;color:var(--muted);margin:6px 0 14px;font-size:13px}.toolbar{display:flex;gap:9px;flex-wrap:wrap;align-items:center}button{font:inherit;cursor:pointer;background:white;border:1px solid #dbd9e8;color:#5a5273;border-radius:10px;padding:9px 16px}button.active{background:var(--accent);color:white;border-color:var(--accent)}a{color:var(--accent);text-decoration:none;font-size:12px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 335px;gap:18px;max-width:1820px;margin:0 auto 24px;padding:0 30px}.canvas{background:white;border:1px solid #e0ddeb;border-radius:18px;overflow:auto;padding:9px}.canvas svg{width:100%;height:auto;min-width:850px;display:block}.panel{background:white;border:1px solid #e0ddeb;border-radius:18px;padding:22px;height:max-content;position:sticky;top:16px}.panel h2{font-size:18px;line-height:1.55;margin:7px 0 11px}.panel h3{font-size:11px;letter-spacing:1px;color:var(--accent);margin:20px 0 6px}.panel p,.panel li{font-size:12px;color:#68647c;line-height:1.85}.panel ul{padding-left:17px;margin:6px 0}.badge{font-size:11px;padding:5px 9px;border-radius:7px;display:inline-block;background:#f5f0df;color:#8f7038}.scenario{max-width:1820px;margin:0 auto 13px;padding:0 30px;display:none}.scenario-inner{border:1px solid #e4d6ba;background:#fffaf0;border-radius:12px;padding:12px 18px;display:flex;gap:14px;flex-wrap:wrap;align-items:center;font-size:12px;color:#826944}.scenario button{padding:6px 10px;font-size:12px}.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:11px;color:#77738a}.legend b{font-weight:600}.print-only{display:none}@media(max-width:1100px){.layout{grid-template-columns:1fr}.panel{position:static}.canvas svg{min-width:760px}header,.layout,.scenario{padding-left:16px;padding-right:16px}h1{font-size:22px}}@media print{@page{size:A3 landscape;margin:8mm}body{background:white}header,.panel,.scenario{display:none!important}.layout{display:block;margin:0;padding:0}.canvas{border:0;padding:0;overflow:visible}.canvas svg{min-width:0;width:100%;max-height:265mm}.print-only{display:block;font-size:10px;color:#777;margin-top:6px}}
</style><header><div class="eyebrow">THESIS ATELIER / RESOURCE FUSION / v3.0 DESIGN</div><h1>让收藏的创意进入同一套工作流</h1><p>以 23 条「111」重点资料为能力来源，用统一的目标、接口、任务与证据契约，把共享空间、团队讨论、软件开发、跨专业数字样机和答辩叙事组合起来。点击节点查看输入输出、来源和接入状态。</p><div class="toolbar"><button data-view="system" onclick="switchView('system')">系统与资源融合</button><button data-view="evidence" onclick="switchView('evidence')">证据与需求变化</button><button data-view="recovery" onclick="switchView('recovery')">失败与人工恢复</button><a href="可点击原型.html">返回原型 ↗</a><a href="资源融合编排架构.svg" download>下载 SVG</a><a href="资源融合编排架构.mmd" download>Mermaid 图源</a></div></header><div class="scenario" id="scenario"><div class="scenario-inner"><b>示例：响应时限 200 ms → 100 ms</b><button id="impact-button" onclick="toggleImpact()">高亮变更影响路径</button><span class="legend"><b style="color:#c96543">橙：确定过期，待重验</b><b style="color:#b28b2c">黄：待影响核对</b><b style="color:#378b63">绿：保持有效</b></span><span>传播只标记影响；重验按新计划与能力关卡执行。</span></div></div><main class="layout"><section class="canvas" id="canvas" aria-label="架构图"></section><aside class="panel" id="panel" aria-live="polite"></aside></main><div class="print-only">离线资源融合编排架构 / 设计方案 v2.1 / Agent与专业工具未实际运行；唯一领域状态源、单一派发路径、单一API重试预算。</div><script>
const SCENES=__DATA__;const SVGS=__SVGS__;let current='system',impact=false;const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));function scene(){return SCENES.find(s=>s.id===current)}function inspectNode(id){let n=scene().nodes.find(n=>n.id===id);if(!n)return;document.querySelectorAll('.node').forEach(e=>e.classList.toggle('selected',e.dataset.node===id));document.getElementById('panel').innerHTML='<div class="eyebrow">NODE CONTRACT / '+esc(n.id)+'</div><h2>'+esc(n.title)+'</h2><span class="badge">'+esc(n.status)+'</span><h3>这项创意怎样融入</h3><p>'+esc(n.detail)+'</p><h3>输入</h3><p>'+esc(n.inputs)+'</p><h3>输出与可追踪对象</h3><p>'+esc(n.outputs)+'</p><h3>资源出处</h3><ul>'+n.sources.map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul>'+((n.upstream_refs||[]).length?'<h3>固定提交中的实际协议</h3><ul>'+(n.upstream_refs||[]).map(r=>'<li><a href="'+esc(r.url)+'" target="_blank" rel="noopener noreferrer">'+esc(r.label)+'</a><br><small>'+esc(r.commit)+'</small><br>'+esc(r.mapping)+'</li>').join('')+'</ul>':'')+'<h3>业务关卡与边界</h3><p>'+esc(n.guard)+'</p>';}function switchView(id,updateHash=true){if(!SCENES.some(s=>s.id===id))id='system';current=id;impact=false;document.getElementById('canvas').innerHTML=SVGS[SCENES.findIndex(s=>s.id===id)];document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===id));document.getElementById('scenario').style.display=id==='evidence'?'block':'none';document.getElementById('impact-button').textContent='高亮变更影响路径';inspectNode(scene().nodes[0].id);if(updateHash&&location.hash!=='#'+id)history.replaceState(null,'','#'+id)}function toggleImpact(){impact=!impact;const affected=new Set(['requirement_contract','control_algo','plc_project','experiment','charts','passport','chapter','slides','html_story','acceptance']);const review=new Set(['cad_interface','pcb_interface']);document.querySelectorAll('.node').forEach(n=>{const id=n.dataset.node;n.classList.toggle('impact',impact&&affected.has(id));n.classList.toggle('review',impact&&review.has(id));n.classList.toggle('safe',impact&&id==='library')});document.querySelectorAll('.edge').forEach(e=>{const[a,b]=e.dataset.edge.split('|');e.classList.toggle('impact',impact&&affected.has(a)&&affected.has(b));e.classList.toggle('review',impact&&(review.has(a)||review.has(b)))});document.getElementById('impact-button').textContent=impact?'取消路径高亮':'高亮变更影响路径';inspectNode('requirement_contract');}window.addEventListener('hashchange',()=>switchView(location.hash.slice(1),false));switchView(location.hash.slice(1)||'system',false);
</script></html>'''

def mermaid():
 parts=['%% 资源融合编排架构 v2.1；一个可编辑 Mermaid flowchart，含系统/证据/恢复三个子图。','%% 未运行组件为候选；仅离线交互已实现。','flowchart TB']
 for s in SCENES:
  parts.append(f'  subgraph {s["id"]}_view["{s["title"]}"]\n    direction TB')
  prefix=s['id']+'_'
  for n in s['nodes']:
   title=n['title'].replace('"',"'");sub=n['sub'].replace('"',"'")
   parts.append(f'    {prefix}{n["id"]}["{title}<br/>{sub}"]')
  for e in s['edges']:
   a,b,label=e[:3];dotted=len(e)>3
   parts.append(f'    {prefix}{a} {"-." if dotted else "--"} "{label}" {".->" if dotted else "-->"} {prefix}{b}')
  parts.append('  end')
 parts.append('  classDef state fill:#e9f2fa,stroke:#3167a4,color:#302d45;\n  classDef source fill:#e8ecfd,stroke:#6053bc,color:#302d45;\n  classDef evidence fill:#e9f5f2,stroke:#287c75,color:#302d45;')
 for kind in ['control','source','evidence']:
  ids=','.join(s['id']+'_'+n['id'] for s in SCENES for n in s['nodes'] if n['kind']==kind)
  if ids:parts.append(f'  class {ids} {"state" if kind=="control" else kind};')
 return '\n'.join(parts)+'\n'

def build():
 # Embed fixed upstream evidence into the offline inspector, without runtime network calls.
 evidence_file=ROOT/'research/111-repo-evidence.json'
 refs=json.loads(evidence_file.read_text()) if evidence_file.exists() else {}
 contracts=refs.get('reusable_contracts',[])
 mapping={'goal':['goalcraft-skill'],'compiler':['goalcraft-skill'],'audits':['pi-shadow-mind'],'development':['pi-shadow-mind'],'outcomes':['answer-me-with-html'],'html_story':['answer-me-with-html'],'repo_research':['pavedpath-code'],'control_algo':['pi-shadow-mind'],'acceptance':['pi-shadow-mind']}
 for scene in SCENES:
  for n in scene['nodes']:
   selected=[r for r in contracts if any(k in r.get('repo','') for k in mapping.get(n['id'],[]))]
   n['upstream_refs']=[{'label':r.get('repo','')+' / '+r.get('path','')+':'+str(r.get('line_start',''))+'–'+str(r.get('line_end',''))+' · '+r.get('section',''),'url':r.get('file_url',''),'commit':r.get('commit','')[:12],'mapping':r.get('local_mapping','')} for r in selected]
 svgs=[svg(s) for s in SCENES]
 (ROOT/'资源融合编排架构.html').write_text(HTML.replace('__DATA__',json.dumps(SCENES,ensure_ascii=False)).replace('__SVGS__',json.dumps(svgs,ensure_ascii=False)))
 # The portable SVG includes all three readable scenes, translated below one another.
 height=sum(s['height'] for s in SCENES)+100
 combined=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1470 {height}" role="img" aria-label="资源融合编排：系统、证据与恢复三视图"><rect width="100%" height="100%" fill="#fff"/>'
 offset=0
 for s,raw in zip(SCENES,svgs):
  inner=raw[raw.index('>')+1:raw.rindex('</svg>')]
  # Standalone SVG is static; remove click event handlers to preserve clean XML/export.
  import re
  inner=re.sub(r'\s(?:onclick|onkeydown)="[^"]*"','',inner)
  combined+=f'<g transform="translate(0,{offset})">{inner}</g>';offset+=s['height']+35
 (ROOT/'资源融合编排架构.svg').write_text(combined+'</svg>')
 (ROOT/'资源融合编排架构.mmd').write_text(mermaid())
 print('Generated offline fusion HTML, 3-view SVG, and editable Mermaid source')


def validate_and_export():
 from playwright.sync_api import sync_playwright
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start();url='http://127.0.0.1:'+str(server.server_address[1])+'/资源融合编排架构.html'
 errors=[];checks=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'],env={'XDG_CONFIG_HOME':'/tmp/fusion-pw-config','XDG_CACHE_HOME':'/tmp/fusion-pw-cache'})
  page=browser.new_page(viewport={'width':1720,'height':1120});page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(url);page.wait_for_load_state('networkidle');page.evaluate('document.fonts.ready')
  assert page.locator('script[src]').count()==0;checks.append('No external JS/CDN dependency')
  for scene in SCENES:
   page.locator(f'[data-view="{scene["id"]}"]').click();assert page.locator('svg').count()==1
   for n in scene['nodes']:
    page.locator(f'[data-node="{n["id"]}"]').click();panel=page.locator('#panel').inner_text()
    assert n['title'] in panel and n['inputs'] in panel and n['outputs'] in panel and n['status'] in panel
   checks.append(f'{scene["id"]}: {len(scene["nodes"])} node input/output/source/status contracts inspectable')
  page.locator('[data-view="evidence"]').click();page.locator('#impact-button').click()
  assert page.locator('.node.impact').count()==10;assert page.locator('.node.review').count()==2;assert page.locator('.node.safe').count()==1
  checks.append('200→100ms: 10 affected objects, 2 pending impact reviews, 1 unchanged source library; highlighting works')
  page.screenshot(path=str(ROOT/'资源融合证据变化预览.png'),full_page=True)
  page.locator('#impact-button').click();assert page.locator('.node.impact').count()==0;checks.append('Impact highlighting resets')
  page.goto(url+'#recovery');assert page.locator('[data-node="resume_gate"]').count()==1;checks.append('Direct hash navigation selects recovery view')
  page.evaluate("location.hash='system'");assert page.locator('[data-node="domain"]').count()==1;checks.append('Hashchange switches existing page view')
  page.locator('[data-node="domain"]').click();assert '唯一持有' in page.locator('#panel').inner_text();page.screenshot(path=str(ROOT/'资源融合架构预览.png'),full_page=True)
  # Three explicit A3 pages, one scene per page, with real Chinese browser fonts.
  printable='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>@page{size:A3 landscape;margin:8mm}body{margin:0}section{break-after:page}section:last-child{break-after:auto}svg{width:100%;max-height:273mm;display:block}</style>'+''.join('<section>'+svg(s)+'</section>' for s in SCENES)+'</html>'
  page.set_content(printable);page.evaluate('document.fonts.ready');page.pdf(path=str(ROOT/'资源融合编排架构.pdf'),prefer_css_page_size=True,print_background=True)
  checks.append('Three-scene A3 PDF exported with browser fonts')
  page.set_viewport_size({'width':390,'height':844});page.goto(url);assert page.locator('#panel').is_visible();page.locator('[data-view="recovery"]').click();assert page.locator('[data-node="resume_gate"]').count()==1;checks.append('390px mobile view retains scrollable SVG and node panel')
  assert not errors,errors;browser.close()
 server.shutdown()
 import xml.etree.ElementTree as ET
 ET.parse(ROOT/'资源融合编排架构.svg');checks.append('Standalone three-view SVG is valid XML')
 report={'status':'passed','version':'2.1','checks':checks,'javascript_errors':errors,'browser':'System Chromium / localhost HTTP','scope':'Offline architecture interaction and actual generated artifacts; external Agent/tools/API not runtime-tested'}
 (ROOT/'research/fusion-architecture-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--no-export',action='store_true');args=parser.parse_args();build()
 if not args.no_export:validate_and_export()
