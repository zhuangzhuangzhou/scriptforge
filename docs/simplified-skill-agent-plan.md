# Skill & Agent 管理系统 - 简化方案

## 核心理念

**去掉复杂的类继承和抽象，一切都是配置化的 Prompt 模板**

- ✅ Skill = Prompt 模板 + 输入/输出定义
- ✅ Agent = Skill 的执行序列（工作流）
- ✅ 执行引擎 = 模板填充 + 模型调用 + JSON 解析
- ✅ 用户可通过 UI 编辑和测试

---

## 架构对比

### ❌ 旧方案（过度工程化）

```python
# 每个 Skill 都是一个类
class ConflictExtractionSkill(BaseSkill):
    async def execute(self, context):
        prompt = self._build_prompt(context)
        response = await model.generate(prompt)
        return self._parse_response(response)

# 需要注册、加载、实例化
skill_loader.load_skill("conflict_extraction")
```

**问题**：
- 修改逻辑需要改代码
- 同步/异步混乱
- 维护成本高

### ✅ 新方案（配置化）

```python
# Skill 就是数据库中的一条记录
skill = {
    "name": "conflict_extraction",
    "prompt_template": """分析以下章节，提取冲突：
{chapters_text}

返回 JSON 格式：
[{{"type": "...", "description": "...", "intensity": 1-10}}]
""",
    "input_schema": {"chapters_text": "string"},
    "output_schema": {"type": "array"}
}

# 执行就是简单的模板填充
def execute_skill(skill, inputs, model):
    prompt = skill.prompt_template.format(**inputs)
    response = model.generate(prompt)
    return parse_json(response)
```

**优势**：
- ✅ 用户可通过 UI 修改 Prompt
- ✅ 代码简单，无需类继承
- ✅ 易于测试和调试

---

## 数据模型设计

### 1. Skill 模型（扩展现有）

```python
class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID, primary_key=True)
    name = Column(String, unique=True)  # 唯一标识
    display_name = Column(String)       # 显示名称
    description = Column(Text)          # 描述
    category = Column(String)           # 分类：breakdown/qa/script

    # 核心字段
    prompt_template = Column(Text)      # Prompt 模板
    input_schema = Column(JSONB)        # 输入定义
    output_schema = Column(JSONB)       # 输出定义

    # 配置
    model_config = Column(JSONB)        # 模型参数（temperature, max_tokens）

    # 示例数据（用于测试）
    example_input = Column(JSONB)
    example_output = Column(JSONB)

    # 元数据
    owner_id = Column(UUID)
    is_builtin = Column(Boolean)        # 是否内置
    is_active = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**示例数据**：

```json
{
  "name": "conflict_extraction",
  "display_name": "冲突提取",
  "description": "从章节内容中提取主要冲突",
  "category": "breakdown",
  "prompt_template": "你是专业的剧情分析师。分析以下章节，提取冲突：\n\n{chapters_text}\n\n返回 JSON 数组：\n[{{\"type\": \"冲突类型\", \"description\": \"描述\", \"intensity\": 1-10}}]",
  "input_schema": {
    "chapters_text": {
      "type": "string",
      "description": "章节文本内容"
    }
  },
  "output_schema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "type": {"type": "string"},
        "description": {"type": "string"},
        "intensity": {"type": "number"}
      }
    }
  },
  "model_config": {
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "example_input": {
    "chapters_text": "第1章：重生\n主角张三重生到十年前..."
  },
  "example_output": [
    {
      "type": "内心冲突",
      "description": "重生后的迷茫与决心",
      "intensity": 7
    }
  ]
}
```

### 2. Agent 模型（新增）

```python
class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID, primary_key=True)
    name = Column(String, unique=True)
    display_name = Column(String)
    description = Column(Text)

    # 工作流定义
    workflow = Column(JSONB)  # Skill 执行序列

    # 元数据
    owner_id = Column(UUID)
    is_builtin = Column(Boolean)
    is_active = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**Workflow 示例**：

```json
{
  "name": "breakdown_agent",
  "display_name": "剧情拆解 Agent",
  "description": "执行完整的剧情拆解流程",
  "workflow": {
    "steps": [
      {
        "id": "step1",
        "skill": "conflict_extraction",
        "inputs": {
          "chapters_text": "${context.chapters_text}"
        },
        "output_key": "conflicts"
      },
      {
        "id": "step2",
        "skill": "plot_hook_identification",
        "inputs": {
          "chapters_text": "${context.chapters_text}"
        },
        "output_key": "plot_hooks"
      },
      {
        "id": "step3",
        "skill": "episode_planning",
        "inputs": {
          "conflicts": "${step1.conflicts}",
          "plot_hooks": "${step2.plot_hooks}"
        },
        "output_key": "episodes"
      },
      {
        "id": "step4",
        "skill": "breakdown_aligner",
        "inputs": {
          "breakdown_data": {
            "conflicts": "${step1.conflicts}",
            "plot_hooks": "${step2.plot_hooks}",
            "episodes": "${step3.episodes}"
          },
          "chapters_text": "${context.chapters_text}"
        },
        "output_key": "qa_result",
        "on_fail": "retry",
        "max_retries": 3
      }
    ]
  }
}
```

---

## 执行引擎设计

### 简化的执行器

```python
# backend/app/ai/simple_executor.py

class SimpleSkillExecutor:
    """简化的 Skill 执行器"""

    def __init__(self, db: Session, model_adapter):
        self.db = db
        self.model_adapter = model_adapter

    def execute_skill(
        self,
        skill_name: str,
        inputs: Dict[str, Any],
        log_publisher=None,
        task_id: str = None
    ) -> Dict[str, Any]:
        """执行单个 Skill

        Args:
            skill_name: Skill 名称
            inputs: 输入数据
            log_publisher: 日志发布器
            task_id: 任务 ID

        Returns:
            执行结果
        """
        # 1. 从数据库加载 Skill 配置
        skill = self.db.query(Skill).filter(
            Skill.name == skill_name,
            Skill.is_active == True
        ).first()

        if not skill:
            raise ValueError(f"Skill '{skill_name}' 不存在或未激活")

        # 2. 填充 Prompt 模板
        try:
            prompt = skill.prompt_template.format(**inputs)
        except KeyError as e:
            raise ValueError(f"缺少必需的输入参数: {e}")

        # 3. 发布步骤开始
        if log_publisher and task_id:
            log_publisher.publish_step_start(
                task_id,
                skill.display_name
            )

        # 4. 调用模型
        model_config = skill.model_config or {}
        temperature = model_config.get("temperature", 0.7)
        max_tokens = model_config.get("max_tokens", 2000)

        full_response = ""
        for chunk in self.model_adapter.stream_generate(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            if log_publisher and task_id:
                log_publisher.publish_stream_chunk(
                    task_id,
                    skill.display_name,
                    chunk
                )
            full_response += chunk

        # 5. 解析 JSON 响应
        result = self._parse_json(full_response)

        # 6. 发布步骤结束
        if log_publisher and task_id:
            log_publisher.publish_step_end(
                task_id,
                skill.display_name,
                {"status": "success"}
            )

        return result

    def _parse_json(self, response: str) -> Any:
        """解析 JSON 响应"""
        import re

        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 提取 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 提取任何 JSON
        json_match = re.search(r'(\[.*\]|\{.*\})', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法解析 JSON 响应: {response[:200]}")


class SimpleAgentExecutor:
    """简化的 Agent 执行器"""

    def __init__(self, db: Session, model_adapter):
        self.db = db
        self.skill_executor = SimpleSkillExecutor(db, model_adapter)

    def execute_agent(
        self,
        agent_name: str,
        context: Dict[str, Any],
        log_publisher=None,
        task_id: str = None
    ) -> Dict[str, Any]:
        """执行 Agent 工作流

        Args:
            agent_name: Agent 名称
            context: 初始上下文数据
            log_publisher: 日志发布器
            task_id: 任务 ID

        Returns:
            执行结果
        """
        # 1. 加载 Agent 配置
        agent = self.db.query(Agent).filter(
            Agent.name == agent_name,
            Agent.is_active == True
        ).first()

        if not agent:
            raise ValueError(f"Agent '{agent_name}' 不存在或未激活")

        # 2. 执行工作流
        workflow = agent.workflow
        steps = workflow.get("steps", [])

        results = {"context": context}

        for step in steps:
            step_id = step["id"]
            skill_name = step["skill"]
            input_template = step["inputs"]
            output_key = step.get("output_key", step_id)

            # 解析输入（支持变量引用）
            inputs = self._resolve_inputs(input_template, results)

            # 执行 Skill
            try:
                result = self.skill_executor.execute_skill(
                    skill_name=skill_name,
                    inputs=inputs,
                    log_publisher=log_publisher,
                    task_id=task_id
                )

                # 保存结果
                results[output_key] = result
                results[step_id] = result

            except Exception as e:
                # 处理失败
                on_fail = step.get("on_fail", "stop")
                max_retries = step.get("max_retries", 0)

                if on_fail == "retry" and max_retries > 0:
                    # TODO: 实现重试逻辑
                    pass
                else:
                    raise

        return results

    def _resolve_inputs(
        self,
        input_template: Dict[str, Any],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析输入模板中的变量引用

        支持：
        - ${context.chapters_text}
        - ${step1.conflicts}
        """
        import re

        def resolve_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # 变量引用
                path = value[2:-1]  # 去掉 ${ 和 }
                parts = path.split(".")

                current = results
                for part in parts:
                    current = current.get(part)
                    if current is None:
                        raise ValueError(f"变量 '{path}' 不存在")

                return current
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(v) for v in value]
            else:
                return value

        return {k: resolve_value(v) for k, v in input_template.items()}
```

---

## 实施步骤

### Phase 1: 数据模型和 API（后端）

**目标**：扩展 Skill 模型，新增 Agent 模型，提供管理 API

#### 1.1 扩展 Skill 模型

- [ ] 修改 `backend/app/models/skill.py`
  - 添加 `prompt_template` 字段
  - 添加 `input_schema` 字段
  - 添加 `output_schema` 字段
  - 添加 `model_config` 字段
  - 添加 `example_input` 和 `example_output` 字段

- [ ] 创建数据库迁移脚本
  ```bash
  cd backend
  alembic revision --autogenerate -m "扩展 Skill 模型"
  alembic upgrade head
  ```

#### 1.2 创建 Agent 模型

- [ ] 新增 `backend/app/models/agent.py`
- [ ] 创建数据库迁移脚本

#### 1.3 Skill 管理 API

- [ ] 新增 `backend/app/api/v1/skills.py`
  - `GET /api/v1/skills` - 列表
  - `GET /api/v1/skills/{id}` - 详情
  - `POST /api/v1/skills` - 创建
  - `PUT /api/v1/skills/{id}` - 更新
  - `DELETE /api/v1/skills/{id}` - 删除
  - `POST /api/v1/skills/{id}/test` - 测试执行

#### 1.4 Agent 管理 API

- [ ] 新增 `backend/app/api/v1/agents.py`
  - `GET /api/v1/agents` - 列表
  - `GET /api/v1/agents/{id}` - 详情
  - `POST /api/v1/agents` - 创建
  - `PUT /api/v1/agents/{id}` - 更新
  - `DELETE /api/v1/agents/{id}` - 删除
  - `POST /api/v1/agents/{id}/execute` - 执行

#### 1.5 简化的执行引擎

- [ ] 新增 `backend/app/ai/simple_executor.py`
  - `SimpleSkillExecutor` 类
  - `SimpleAgentExecutor` 类

---

### Phase 2: Skill 管理 UI（前端）

**目标**：提供可视化的 Skill 编辑和测试界面

#### 2.1 Skill 列表页面

- [ ] 新增 `frontend/src/pages/admin/Skills/index.tsx`
  - 显示所有 Skills（表格或卡片）
  - 分类筛选（breakdown/qa/script）
  - 搜索功能
  - 新建按钮

#### 2.2 Skill 编辑器

- [ ] 新增 `frontend/src/pages/admin/Skills/SkillEditor.tsx`
  - 基本信息编辑（名称、描述、分类）
  - Prompt 模板编辑器（代码编辑器，支持语法高亮）
  - 输入/输出 Schema 编辑（JSON 编辑器）
  - 模型配置（temperature, max_tokens）
  - 示例数据编辑

#### 2.3 Skill 测试器

- [ ] 新增 `frontend/src/pages/admin/Skills/SkillTester.tsx`
  - 输入示例数据
  - 点击"测试"按钮
  - 实时显示执行过程（流式输出）
  - 显示执行结果
  - 显示执行时间和 Token 消耗

#### 2.4 UI 组件

- [ ] JSON Schema 编辑器组件
- [ ] Prompt 模板编辑器组件（Monaco Editor）
- [ ] 执行日志查看器组件

---

### Phase 3: Agent 管理 UI（前端）

**目标**：提供可视化的 Agent 工作流编辑界面

#### 3.1 Agent 列表页面

- [ ] 新增 `frontend/src/pages/admin/Agents/index.tsx`

#### 3.2 Agent 工作流编辑器

- [ ] 新增 `frontend/src/pages/admin/Agents/AgentEditor.tsx`
  - 可视化工作流编辑器（拖拽式）
  - 或者 JSON 编辑器（简单版本）
  - 步骤配置（选择 Skill、配置输入映射）
  - 错误处理配置（重试、跳过）

#### 3.3 Agent 测试器

- [ ] 新增 `frontend/src/pages/admin/Agents/AgentTester.tsx`
  - 输入初始上下文
  - 执行 Agent
  - 显示每个步骤的执行结果

---

### Phase 4: 集成到现有流程

**目标**：用新的执行引擎替换旧的实现

#### 4.1 修改拆解任务

- [ ] 修改 `backend/app/tasks/breakdown_tasks.py`
  - 使用 `SimpleAgentExecutor` 执行 `breakdown_agent`
  - 移除旧的 Skill 加载逻辑

#### 4.2 迁移现有 Skills

- [ ] 将现有的 Skill 类转换为配置数据
  - 提取 Prompt 模板
  - 定义输入/输出 Schema
  - 插入到数据库

---

## 优先级排序

### 🔴 P0（核心功能，先做）

1. **扩展 Skill 模型** - 数据基础
2. **Skill 管理 API** - 后端接口
3. **简化的执行引擎** - 核心逻辑
4. **Skill 列表和编辑器** - 前端 UI
5. **Skill 测试器** - 验证功能

### 🟡 P1（重要功能，后做）

6. **Agent 模型和 API** - 工作流支持
7. **Agent 编辑器** - 可视化编排
8. **集成到拆解流程** - 替换旧实现

### 🟢 P2（增强功能，可选）

9. **版本管理** - Skill 版本历史
10. **权限控制** - 谁可以编辑哪些 Skills
11. **市场/分享** - 分享 Skills 给其他用户

---

## 预期效果

### 开发者视角

- ✅ 代码量减少 70%
- ✅ 不再需要写 Skill 类
- ✅ 修改逻辑只需编辑配置
- ✅ 易于测试和调试

### 用户视角

- ✅ 可以通过 UI 自定义 Prompt
- ✅ 可以测试 Skill 效果
- ✅ 可以创建自己的 Agent 工作流
- ✅ 不需要懂代码

---

## 下一步

1. **确认方案** - 您是否同意这个简化方案？
2. **开始实施** - 从 Phase 1 开始，先做数据模型和 API
3. **迭代优化** - 根据实际使用情况调整

请告诉我您的想法！
