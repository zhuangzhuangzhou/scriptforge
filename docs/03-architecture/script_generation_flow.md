 ★ Insight ─────────────────────────────────────
  剧本生成的核心架构：
  1. 三层架构：API 层（scripts.py）→ Celery 任务层（script_tasks.py）→ AI 执行层（simple_executor.py）
  2. Skill 执行模式：使用 Prompt 模板填充 + LLM 流式生成 + 结构化解析
  3. 流式输出优化：支持实时 JSON 解析和格式化，通过 Redis 推送到前端 Console
  ─────────────────────────────────────────────

  完整调用链路

  1. API 层入口（backend/app/api/v1/scripts.py:111-186）

  @router.post("/episode/start")
  async def start_episode_script(request: EpisodeScriptStartRequest, ...):
      """
      前端调用：POST /api/v1/scripts/episode/start
      参数：
      - breakdown_id: 剧情拆解 ID
      - episode_number: 集数
      - model_config_id: 模型配置 ID（可选）
      - novel_type: 小说类型（可选）
      """

      # 1. 验证拆解结果存在
      breakdown = await db.execute(
          select(PlotBreakdown).join(Batch).join(Project)
          .where(PlotBreakdown.id == request.breakdown_id, ...)
      )

      # 2. 检查并预扣积分
      quota_service = QuotaService(db)
      credits_check = await quota_service.check_credits(current_user, "script")
      consume_result = await quota_service.consume_credits(current_user, "script", "剧本生成")

      # 3. 创建任务记录
      task_config = {
          "model_config_id": request.model_config_id or project.script_model_id,
          "breakdown_id": str(breakdown.id),
          "episode_number": request.episode_number,
          "novel_type": request.novel_type or project.novel_type
      }

      task = AITask(
          project_id=breakdown.project_id,
          batch_id=breakdown.batch_id,
          task_type="episode_script",
          status=TaskStatus.QUEUED,
          config=task_config
      )

      # 4. 启动 Celery 异步任务
      from app.tasks.script_tasks import run_episode_script_task
      celery_task = run_episode_script_task.delay(
          str(task.id),
          str(breakdown.id),
          request.episode_number,
          str(breakdown.project_id),
          str(current_user.id)
      )

      return {"task_id": str(task.id), "status": TaskStatus.QUEUED}

  2. Celery 任务层（backend/app/tasks/script_tasks.py:35-128）

  @celery_app.task(**CELERY_TASK_CONFIG)
  def run_episode_script_task(self, task_id, breakdown_id, episode_number, project_id, user_id):
      """
      Celery 异步任务，负责：
      1. 初始化日志发布器（Redis）
      2. 加载模型适配器
      3. 调用核心执行函数
      4. 处理失败时的积分退款
      """

      db = SyncSessionLocal()
      log_publisher = RedisLogPublisher()  # 用于推送日志到前端

      try:
          # 1. 获取模型配置
          task_record = db.query(AITask).filter(AITask.id == task_id).first()
          model_id = task_record.config.get("model_config_id")

          # 2. 初始化模型适配器
          from app.ai.adapters import get_adapter_sync
          model_adapter = get_adapter_sync(db=db, model_id=model_id, user_id=user_id)

          # 3. 执行剧本生成
          result = _execute_episode_script_sync(
              db=db, task_id=task_id, breakdown_id=breakdown_id,
              episode_number=episode_number, project_id=project_id,
              model_adapter=model_adapter, task_config=task_config,
              log_publisher=log_publisher
          )

          # 4. 更新任务状态为完成
          update_task_progress_sync(db, task_id, status=TaskStatus.COMPLETED, progress=100)

          # 注意：积分已在 API 层预扣，成功时不退款

          return {"status": TaskStatus.COMPLETED, "task_id": task_id, **result}

      except Exception as e:
          # 失败时退还预扣的积分
          from app.core.quota import refund_episode_quota_sync
          refund_episode_quota_sync(db, user_id, 1, auto_commit=False)
          db.commit()
          raise

  3. 核心执行函数（backend/app/tasks/script_tasks.py:131-315）

  def _execute_episode_script_sync(db, task_id, breakdown_id, episode_number, ...):
      """
      核心执行逻辑：
      1. 加载剧情拆解结果
      2. 筛选本集剧情点
      3. 加载章节原文
      4. 加载 AI 资源（Prompt 模板）
      5. 调用 Skill 执行器生成剧本
      6. 保存结果到数据库
      7. 更新剧情点状态为 used
      """

      # 1. 加载剧情拆解
      breakdown = db.query(PlotBreakdown).filter(PlotBreakdown.id == breakdown_id).first()

      # 2. 筛选本集剧情点
      episode_plot_points = [
          pp for pp in breakdown.plot_points
          if pp.get("episode") == episode_number
      ]

      # 3. 加载章节原文（最多 10 章）
      source_chapters = {pp.get("source_chapter") for pp in episode_plot_points}
      chapters = db.query(Chapter).filter(
          Chapter.batch_id == breakdown.batch_id,
          Chapter.chapter_number.in_(source_chapters)
      ).order_by(Chapter.chapter_number).limit(10).all()

      chapters_text = "\n\n".join([
          f"## 第 {ch.chapter_number} 章\n{ch.content or ''}"
          for ch in chapters
      ])

      # 4. 加载 AI 资源（分层 Prompt）
      from app.core.init_ai_resources import load_layered_resources_sync
      novel_type = task_config.get("novel_type")
      resources = load_layered_resources_sync(db, stage="script", novel_type=novel_type)
      adapt_method = "\n\n---\n\n".join([
          resources.get("core"),      # 核心方法论
          resources.get("script"),    # 剧本创作方法
          resources.get("type")       # 类型特定方法
      ])

      # 5. 调用 Skill 执行器生成剧本 ⭐ 关键步骤
      from app.ai.simple_executor import SimpleSkillExecutor
      skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)

      script_result = skill_executor.execute_skill(
          skill_name="webtoon_script",  # Skill 名称
          inputs={
              "plot_points": json.dumps(episode_plot_points, ensure_ascii=False),
              "chapters_text": chapters_text[:5000],  # 限制长度
              "adapt_method": adapt_method,
              "episode_number": str(episode_number)
          },
          task_id=task_id
      )

      # 6. 保存剧本到数据库
      new_script = Script(
          batch_id=breakdown.batch_id,
          project_id=project_id,
          plot_breakdown_id=breakdown_id,
          episode_number=episode_number,
          title=script_result.get("title", f"第 {episode_number} 集"),
          content={
              "structure": script_result.get("structure", {}),
              "full_script": script_result.get("full_script", ""),
              "scenes": script_result.get("scenes", []),
              "characters": script_result.get("characters", []),
              "hook_type": script_result.get("hook_type", "")
          },
          word_count=len(script_result.get("full_script", "")),
          scene_count=len(script_result.get("scenes", [])),
          status="draft"
      )
      db.add(new_script)
      db.commit()

      # 7. 更新剧情点状态为 used
      _update_plot_points_status_sync(db, breakdown_id, episode_number)

      return {"episode_number": episode_number, "script_id": str(new_script.id), ...}

  4. Skill 执行器（backend/app/ai/simple_executor.py:667-983）

  这是 LLM 调用的核心逻辑：

  class SimpleSkillExecutor:
      def execute_skill(self, skill_name: str, inputs: Dict[str, Any], task_id: str):
          """
          执行单个 Skill 的完整流程：
          1. 从数据库加载 Skill 配置
          2. 预处理输入参数
          3. 填充 Prompt 模板
          4. 调用 LLM（流式生成）
          5. 解析响应
          6. 发布日志
          """

          # 1. 加载 Skill 配置
          skill = self.db.query(Skill).filter(
              Skill.name == skill_name,
              Skill.is_active == True
          ).first()

          # Skill 包含：
          # - prompt_template: Prompt 模板（带占位符）
          # - system_prompt: 系统提示词
          # - model_config: 模型参数（temperature, max_tokens）
          # - input_schema: 输入参数定义
          # - output_schema: 输出格式定义

          # 2. 预处理输入参数
          processed_inputs = {}
          for key, value in inputs.items():
              if value is None:
                  processed_inputs[key] = ""
              elif isinstance(value, str):
                  processed_inputs[key] = value
              elif isinstance(value, list):
                  # 剧情点参数转换为结构化文本格式
                  if key in {"plot_points", "previous_plot_points"}:
                      processed_inputs[key] = format_plot_points_to_text(value)
                  else:
                      processed_inputs[key] = json.dumps(value, ensure_ascii=False)
              elif isinstance(value, dict):
                  processed_inputs[key] = json.dumps(value, ensure_ascii=False)
              else:
                  processed_inputs[key] = str(value)

          # 2.5 为缺失的可选参数填充空值
          if skill.input_schema:
              for param_name in skill.input_schema.keys():
                  if param_name not in processed_inputs:
                      processed_inputs[param_name] = ""

          # 3. 填充 Prompt 模板
          prompt = skill.prompt_template.format(**processed_inputs)

          # 示例 Prompt 模板（webtoon_script）：
          """
          你是一位专业的网文改编编剧。请根据以下剧情点创作第 {episode_number} 集的完整剧本。

          ### 剧情点
          {plot_points}

          ### 章节原文
          {chapters_text}

          ### 改编方法
          {adapt_method}

          ### 输出格式
          请以 JSON 格式输出：
          {{
            "title": "第X集标题",
            "structure": {{"开场": "...", "发展": "...", "高潮": "...", "结尾": "..."}},
            "scenes": [
              {{"scene_number": 1, "location": "...", "characters": [...], "dialogue": "...", "action": "..."}}
            ],
            "full_script": "完整剧本文本",
            "characters": ["角色1", "角色2"],
            "hook_type": "钩子类型"
          }}
          """

          system_prompt = skill.system_prompt or ""

          # 4. 配置模型参数
          skill_config = skill.model_config or {}
          temperature = skill_config.get("temperature") or 0.7
          max_tokens = skill_config.get("max_tokens") or 1000

          # 5. 调用 LLM（流式生成）⭐ 核心调用
          full_response = ""

          # 初始化流式 JSON 解析器
          from app.utils.stream_json_parser import StreamJsonParser
          json_parser = StreamJsonParser()
          formatted_index = 0

          try:
              # 流式生成
              for chunk in self.model_adapter.stream_generate(
                  prompt,
                  system_prompt=system_prompt,
                  temperature=temperature,
                  max_tokens=max_tokens
              ):
                  if chunk:
                      # 发送原始 JSON 片段到前端
                      if self.log_publisher and task_id:
                          self.log_publisher.publish_stream_chunk(
                              task_id,
                              "剧本生成",
                              chunk
                          )

                          # 解析并发送格式化内容
                          parsed_objects = json_parser.feed(chunk)
                          for obj in parsed_objects:
                              formatted_text = format_json_object(obj, "script", formatted_index)
                              self.log_publisher.publish_formatted_chunk(
                                  task_id,
                                  "剧本生成",
                                  formatted_text + "\n"
                              )
                              formatted_index += 1

                      full_response += chunk

          except Exception as stream_error:
              # 流式失败，回退到非流式
              full_response = self.model_adapter.generate(
                  prompt,
                  system_prompt=system_prompt,
                  temperature=temperature,
                  max_tokens=max_tokens
              )

          # 6. 解析 JSON 响应
          result = self._parse_json(full_response)

          # 7. 发布步骤结束日志
          if self.log_publisher and task_id:
              self.log_publisher.publish_step_end(
                  task_id,
                  "剧本生成",
                  {"status": "success"}
              )

          return result

  LLM 调用参数详解

  输入参数（inputs）

  {
      "plot_points": """
      1|酒店大堂|林浩/陈总|林浩揭穿欺诈|打脸爽点|第1集
      2|公司会议室|林浩/秘书小王|林浩展示隐藏实力|碾压爽点|第1集
      3|地下停车场|林浩/神秘女子|神秘女子暗示身份|悬念开场|第1集
      """,

      "chapters_text": """
      ## 第 1 章
      林浩站在酒店大堂，看着眼前的陈总...

      ## 第 2 章
      会议室里，所有人都在等待林浩的发言...
      """,

      "adapt_method": """
      【核心方法论】
      1. 保留原著核心冲突
      2. 强化视觉表现
      3. 优化节奏控制

      【剧本创作方法】
      1. 场景设计：每个剧情点对应一个场景
      2. 对话设计：简洁有力，符合角色性格
      3. 动作描述：具体可视化

      【类型特定方法】（都市爽文）
      1. 强化打脸爽点
      2. 快节奏推进
      3. 突出主角光环
      """,

      "episode_number": "1"
  }

  模型参数

  {
      "temperature": 0.7,        # 控制输出随机性（0-1，越高越随机）
      "max_tokens": 1000000,     # 最大输出长度
      "system_prompt": "你是一位专业的网文改编编剧...",
      "prompt": "请根据以下剧情点创作第 1 集的完整剧本..."
  }

  LLM 返回格式

  {
    "title": "第1集：真相揭露",
    "structure": {
      "开场": "林浩在酒店大堂遇到陈总",
      "发展": "林浩揭穿陈总的欺诈行为",
      "高潮": "陈总当众认错",
      "结尾": "神秘女子出现，暗示更大阴谋"
    },
    "scenes": [
      {
        "scene_number": 1,
        "location": "酒店大堂",
        "characters": ["林浩", "陈总"],
        "dialogue": "林浩：陈总，您的账目有问题...",
        "action": "林浩拿出一份文件，递给陈总"
      }
    ],
    "full_script": "【第1场 酒店大堂 日】\n林浩站在大堂中央...",
    "characters": ["林浩", "陈总", "秘书小王", "神秘女子"],
    "hook_type": "打脸爽点"
  }

  关键技术点

  1. 流式输出：使用 model_adapter.stream_generate() 实现实时输出，通过 Redis 推送到前端
  2. 结构化解析：使用 StreamJsonParser 实时解析 JSON 片段，格式化后显示
  3. 错误处理：流式失败自动回退到非流式调用
  4. 积分管理：API 层预扣，任务成功不退款，失败自动退款
  5. 状态同步：通过 update_task_progress_sync 更新任务进度，前端轮询获取

  这就是剧本生成的完整调用链路和 LLM 调用逻辑！