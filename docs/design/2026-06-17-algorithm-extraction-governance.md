# Algorithm Extraction Governance

## 目标

把参考项目中的主材类型算法、牛腿算法、零件特征提取算法迁入 `I:\zijinhuatekla` 时，保持算法可解释、可验证、可持续进化，避免随着案例增多维护成规则堆砌。

## 核心原则

算法允许随着案例反馈持续修正，但修正必须进入正确层级：

- Data Quality Gate：处理模型、Excel、编号、制造口径与建模口径不一致。
- Feature Snapshot：补充稳定、可复用的几何/孔/切割/焊接/关系特征。
- Scoring / Strategy：调整证据权重、阈值、优先级和置信度。
- Case Bank：沉淀人工确认样例、失败原因、期望标签和回归测试。

禁止把单个构件号、零件号、项目名写成业务规则。

## 反馈归因流程

每个失败案例先归因，再决定改哪里。

| 失败类型 | 判断方式 | 应该改哪里 | 禁止做法 |
| --- | --- | --- | --- |
| 数据问题 | 模型缺件、Excel 错号、同名不同物、整板/分段口径冲突 | Data Quality Gate | 强行分类成 MATCH |
| 特征缺失 | 人能判断，但当前导出字段不足 | Feature Snapshot / 导出器 | 用编号或名称猜测 |
| 评分问题 | 特征足够，但权重或阈值不稳 | Scoring / Strategy | 加单样本阈值 |
| 新类型 | 现有类别表达不了真实角色/工艺 | 类别定义 + 验收样例 | 塞进相近旧类别 |

## 算法抽取边界

### 零件特征提取

来源：`I:\autoweb\teklatest`

抽取目标不是直接复制 Tekla API 代码，而是定义统一的 `PartFeatureSnapshot`：

- 基本信息：零件号、构件号、名称、profile、材质、尺寸、重量。
- 几何信息：OBB、轮廓点、轮廓边、厚度、名义加工长宽。
- 加工特征：孔、螺栓孔、内部孔、倒角、切口、剖口、折弯。
- 关系特征：焊缝、接触、螺栓连接。
- 形状特征：矩形、带倒角矩形、异形板、型材、复杂件。

Tekla 插件、MCP、离线 JSON 都应该适配到这个契约。

### 构件主材类型

来源：`I:\autoteklasuanfa`

抽取目标是 `MemberBodyClassifier`：

- 输入：构件级 PartFeatureSnapshot 集合、关系图、截面采样/拓扑特征。
- 输出：`BOX`、`H`、`PRIMARY_PLATE_BODY`、`UNKNOWN` 等主材类型。
- 必须输出 evidence、confidence、reason code。

主体候选、截面 trace、闭环证据、H 的 web/flange 拓扑应作为可解释证据，不得退化成名称规则。

### 牛腿与零件角色

来源：`I:\lingjianjuesemimo`

抽取目标是 `PartRoleClassifier / BracketClassifier`：

- 输入：主体 body、附属件 cluster、root zone、overhang features、焊接/接触/螺栓关系。
- 输出：`Bracket`、`Stiffener`、`Diaphragm`、`ConnectionPlate`、`WeldPad`、`Unknown`。
- 牛腿不应只按单零件名称判断，应基于附属件簇、根部连接、悬挑比例和支承面。

## 变更准入

任何算法变更必须满足至少一条：

- 新增或修正了 Feature Snapshot 字段。
- 修正了可解释评分/策略。
- 新增了 Case Bank 样例和期望标签。
- 修正了 Data Quality Gate 对数据问题的分类。

任何算法变更必须留下：

- 失败样例来源。
- 人工确认口径。
- 变更归因。
- 回归测试或验证命令。

## 第一阶段落地顺序

1. 建立 `PartFeatureSnapshot` 契约和 adapter。
2. 接入 `teklatest` 中稳定的孔、倒角、切口、形状、焊接特征。
3. 建立 `MemberBodyClassifier` 接口，迁入 `autoteklasuanfa` 的主材拓扑证据。
4. 建立 `PartRoleClassifier` 接口，迁入 `lingjianjuesemimo` 的牛腿/附属件簇算法。
5. 建立 Case Bank，用 T3-5GKZ-10 和后续人工确认案例做回归。

## 验收标准

- 新增规则不能只引用单个构件号或零件号。
- 每个失败案例都有归因标签。
- 每次人工确认都能沉淀为 case，而不是只停留在聊天。
- 分类结果必须带 evidence 和 confidence。
- Data Quality Gate 能阻止错误数据污染后续分类器。
