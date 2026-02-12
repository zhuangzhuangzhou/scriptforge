import re
import json
import inspect
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.skills.skill_loader import SkillLoader
from app.ai.skills.template_skill_executor import TemplateSkillExecutor
from app.ai.consistency_checker import ConsistencyChecker
from app.core.pipeline_defaults import DEFAULT_BREAKDOWN_SKILLS, DEFAULT_SCRIPT_SKILLS
from app.models.pipeline import Pipeline, PipelineStage
from app.models.skill import Skill
from app.models.agent import AgentDefinition
from app.models.chapter import Chapter
from app.models.plot_breakdown import PlotBreakdown
from app.models.script import Script


class PipelineExecutor:
    """基于数据库 Pipeline 配置的执行器"""

    def __init__(self, db: AsyncSession, model_adapter, user_id: Optional[str] = None, task_config: Optional[Dict[str, Any]] = None):
        self.db = db
        self.model_adapter = model_adapter
        self.user_id = user_id
        self.task_config = task_config or {}
        self.skill_loader = SkillLoader()
        self.template_executor = TemplateSkillExecutor(db, model_adapter=model_adapter)
        # 配置缓存
        self._adapt_method = None
        self._quality_rule = None
        self._output_style = None

    async def run_breakdown(
        self,
        project_id: str,
        batch_id: str,
        pipeline_id: Optional[str] = None,
        selected_skills: Optional[List[str]] = None,
        progress_callback: Optional[Any] = None,
        log_callback: Optional[Any] = None
    ) -> PlotBreakdown:
        stage = await self._get_stage(pipeline_id, "breakdown")
        skills = self._get_stage_skills(stage, selected_skills, DEFAULT_BREAKDOWN_SKILLS)

        # 加载配置
        adapt_method = await self.get_adapt_method()
        quality_rule = await self.get_quality_rule()
        output_style = await self.get_output_style()

        chapters = await self._load_chapters(batch_id)
        context: Dict[str, Any] = {
            "chapters": chapters,
            "model_adapter": self.model_adapter,
            # 注入配置到上下文
            "adapt_method": adapt_method,
            "quality_rule": quality_rule,
            "output_style": output_style
        }

        context = await self._execute_skills(skills, context, progress_callback)

        # 质检（可选）
        validation = await self._run_validators(
            stage=stage,
            context=context,
            project_id=project_id,
            batch_id=batch_id,
            log_callback=log_callback
        )

        breakdown = PlotBreakdown(
            batch_id=batch_id,
            project_id=project_id,
            conflicts=context.get("conflicts", []),
            plot_hooks=context.get("plot_hooks", []),
            characters=context.get("characters", []),
            scenes=context.get("scenes", []),
            emotions=context.get("emotions", []),
            consistency_status=validation.get("status", "pending"),
            consistency_score=validation.get("score"),
            consistency_results=validation.get("results"),
            used_adapt_method_id=self.task_config.get("adapt_method_key")
        )

        self.db.add(breakdown)
        await self.db.commit()
        await self.db.refresh(breakdown)

        return breakdown

    async def run_script(
        self,
        project_id: str,
        batch_id: str,
        breakdown_id: str,
        pipeline_id: Optional[str] = None,
        selected_skills: Optional[List[str]] = None,
        progress_callback: Optional[Any] = None,
        log_callback: Optional[Any] = None
    ) -> Script:
        stage = await self._get_stage(pipeline_id, "script")
        skills = self._get_stage_skills(stage, selected_skills, DEFAULT_SCRIPT_SKILLS)

        breakdown_data = await self._load_breakdown_data(breakdown_id)
        context: Dict[str, Any] = {
            "breakdown_data": breakdown_data,
            "model_adapter": self.model_adapter
        }

        context = await self._execute_skills(skills, context, progress_callback)

        script_content = {
            "version": "1.0",
            "episodes": context.get("episodes", []),
            "scenes": context.get("scenes", []),
            "dialogues": context.get("dialogues", [])
        }

        # 质检（可选）
        context["script"] = script_content
        validation = await self._run_validators(
            stage=stage,
            context=context,
            project_id=project_id,
            batch_id=batch_id,
            log_callback=log_callback
        )
        if validation.get("status") and validation.get("results") is not None:
            script_content["validation"] = validation

        episodes = context.get("episodes", [])
        title = "第一集"
        if episodes and isinstance(episodes[0], dict):
            title = episodes[0].get("title") or title

        script = Script(
            batch_id=batch_id,
            project_id=project_id,
            plot_breakdown_id=breakdown_id,
            episode_number=1,
            title=title,
            content=script_content,
            word_count=0,
            scene_count=len(context.get("scenes", []))
        )

        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)

        return script

    async def run_pipeline(
        self,
        pipeline_id: str,
        project_id: str,
        batch_id: Optional[str],
        breakdown_id: Optional[str] = None,
        progress_callback: Optional[Any] = None,
        stage_completed_callback: Optional[Any] = None,
        log_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        pipeline = await self._get_pipeline(pipeline_id)
        if not pipeline:
            raise ValueError("Pipeline不存在")

        stages = await self._load_pipeline_stages(pipeline)
        if not stages:
            raise ValueError("Pipeline未配置任何阶段")

        total_stages = len(stages)
        results: Dict[str, Any] = {"completed_stages": []}
        current_breakdown_id = breakdown_id

        for index, stage in enumerate(stages):
            stage_start = int((index / total_stages) * 100)
            stage_end = int(((index + 1) / total_stages) * 100)

            async def stage_progress(step: str, progress: int, start=stage_start, end=stage_end, stage_name=stage.display_name or stage.name):
                if not progress_callback:
                    return
                scaled = start + int((progress / 100) * (end - start))
                scaled = max(start, min(end, scaled))
                await progress_callback(f"{stage_name}: {step}", scaled)

            if log_callback:
                cb = log_callback(stage.name, "stage_start", f"阶段开始: {stage.display_name or stage.name}", None)
                if inspect.isawaitable(cb):
                    await cb

            if stage.name == "breakdown":
                if not batch_id:
                    raise ValueError("执行 breakdown 阶段需要 batch_id")
                breakdown = await self.run_breakdown(
                    project_id=project_id,
                    batch_id=batch_id,
                    pipeline_id=pipeline_id,
                    progress_callback=stage_progress,
                    log_callback=log_callback
                )
                current_breakdown_id = str(breakdown.id)
                results["breakdown_id"] = current_breakdown_id
                results["completed_stages"].append(stage.name)
                if stage_completed_callback:
                    cb_result = stage_completed_callback(stage.name)
                    if inspect.isawaitable(cb_result):
                        await cb_result
            elif stage.name == "script":
                if not batch_id:
                    raise ValueError("执行 script 阶段需要 batch_id")
                if not current_breakdown_id:
                    raise ValueError("执行 script 阶段需要 breakdown_id")
                script = await self.run_script(
                    project_id=project_id,
                    batch_id=batch_id,
                    breakdown_id=current_breakdown_id,
                    pipeline_id=pipeline_id,
                    progress_callback=stage_progress,
                    log_callback=log_callback
                )
                results["script_id"] = str(script.id)
                results["completed_stages"].append(stage.name)
                if stage_completed_callback:
                    cb_result = stage_completed_callback(stage.name)
                    if inspect.isawaitable(cb_result):
                        await cb_result
            else:
                # 未知阶段先跳过，保留配置扩展空间
                if progress_callback:
                    await progress_callback(f"{stage.display_name or stage.name}: 跳过", stage_end)
                results.setdefault("skipped_stages", []).append(stage.name)
                if log_callback:
                    cb = log_callback(stage.name, "stage_skipped", f"阶段跳过: {stage.display_name or stage.name}", None)
                    if inspect.isawaitable(cb):
                        await cb

        return results

    async def _get_stage(self, pipeline_id: Optional[str], stage_name: str) -> PipelineStage:
        pipeline = await self._get_pipeline(pipeline_id)
        if not pipeline:
            # 兜底：构造临时阶段
            return PipelineStage(
                pipeline_id=None,
                name=stage_name,
                display_name=stage_name,
                skills=[],
                order=0,
                config={}
            )

        stages = await self._load_pipeline_stages(pipeline)
        for stage in stages:
            if stage.name == stage_name:
                return stage

        # 找不到则回退空阶段
        return PipelineStage(
            pipeline_id=pipeline.id,
            name=stage_name,
            display_name=stage_name,
            skills=[],
            order=0,
            config={}
        )

    async def _get_pipeline(self, pipeline_id: Optional[str]) -> Optional[Pipeline]:
        if pipeline_id:
            result = await self.db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
            return result.scalar_one_or_none()

        # 优先用户默认 Pipeline
        if self.user_id:
            result = await self.db.execute(
                select(Pipeline).where(
                    Pipeline.user_id == self.user_id,
                    Pipeline.is_default == True,
                    Pipeline.is_active == True
                )
            )
            pipeline = result.scalar_one_or_none()
            if pipeline:
                return pipeline

        # 回退系统默认 Pipeline
        result = await self.db.execute(
            select(Pipeline).where(
                Pipeline.is_default == True,
                Pipeline.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def _load_pipeline_stages(self, pipeline: Pipeline) -> List[PipelineStage]:
        # 优先使用 Pipeline.stages_config 作为运行时配置源
        stages_config = pipeline.stages_config or []
        if stages_config:
            temp_stages = []
            for i, stage_data in enumerate(stages_config):
                temp_stages.append(PipelineStage(
                    pipeline_id=pipeline.id,
                    name=stage_data.get("name", f"stage_{i}"),
                    display_name=stage_data.get("display_name", f"Stage {i+1}"),
                    description=stage_data.get("description"),
                    skills=stage_data.get("skills", []),
                    skills_order=stage_data.get("skills_order"),
                    config=stage_data.get("config", {}),
                    input_mapping=stage_data.get("input_mapping"),
                    output_mapping=stage_data.get("output_mapping"),
                    order=stage_data.get("order", i)
                ))
            return temp_stages

        # 回退：读取 PipelineStage 表
        result = await self.db.execute(
            select(PipelineStage)
            .where(PipelineStage.pipeline_id == pipeline.id)
            .order_by(PipelineStage.order)
        )
        stages = result.scalars().all()

        return list(stages)

    def _get_stage_skills(
        self,
        stage: PipelineStage,
        selected_skills: Optional[List[str]],
        default_skills: List[str]
    ) -> List[Union[str, dict]]:
        if selected_skills:
            return selected_skills

        if stage.skills_order:
            return stage.skills_order

        if stage.skills:
            return stage.skills

        return default_skills

    async def _execute_skills(
        self,
        skills: List[Union[str, dict]],
        context: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        total = max(len(skills), 1)
        for idx, skill_ref in enumerate(skills, start=1):
            if progress_callback:
                await progress_callback(f"执行Skill: {skill_ref}", int(10 + (idx / total) * 80))

            skill = await self._resolve_skill(skill_ref)
            result = await self._execute_skill(skill, context)

            if isinstance(result, dict):
                context.update(result)

        return context

    async def _resolve_skill(self, skill_ref: Union[str, dict]) -> Skill:
        skill_id = None
        skill_name = None

        if isinstance(skill_ref, dict):
            skill_id = skill_ref.get("id") or skill_ref.get("skill_id")
            skill_name = skill_ref.get("name")
        elif isinstance(skill_ref, str):
            if self._looks_like_uuid(skill_ref):
                skill_id = skill_ref
            else:
                skill_name = skill_ref

        if skill_id:
            result = await self.db.execute(select(Skill).where(Skill.id == skill_id))
            skill = result.scalar_one_or_none()
            if not skill:
                raise ValueError(f"Skill不存在: {skill_id}")
            return skill

        if skill_name:
            result = await self.db.execute(select(Skill).where(Skill.name == skill_name))
            skill = result.scalar_one_or_none()
            if not skill:
                raise ValueError(f"Skill不存在: {skill_name}")
            return skill

        raise ValueError("无效的Skill引用")

    async def _execute_skill(self, skill: Skill, context: Dict[str, Any]) -> Dict[str, Any]:
        if skill.is_template_based:
            result = await self.template_executor.execute(
                skill_id=str(skill.id),
                variables=context,
                user_id=str(self.user_id) if self.user_id else None
            )
            output = result.get("result")
            if isinstance(output, dict):
                return output
            return {"output": output}

        # 非模板 Skill：尝试从本地代码加载
        skill_instance = self.skill_loader.get_skill(skill.name)
        if not skill_instance:
            raise ValueError(f"Skill代码未找到: {skill.name}")
        return await skill_instance.execute(context)

    async def _run_validators(
        self,
        stage: PipelineStage,
        context: Dict[str, Any],
        project_id: str,
        batch_id: str,
        log_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        config = stage.config or {}
        validators = config.get("validators", [])

        if not validators:
            return {"status": "pending", "score": None, "results": None}

        results = []
        final_status = "passed"
        final_score = None

        for validator in validators:
            # 支持 {"type": "consistency_checker"} 或字符串
            if validator == "consistency_checker" or (
                isinstance(validator, dict) and validator.get("type") == "consistency_checker"
            ):
                checker = ConsistencyChecker(self.model_adapter)
                breakdown_data = {
                    "conflicts": context.get("conflicts", []),
                    "plot_hooks": context.get("plot_hooks", []),
                    "characters": context.get("characters", []),
                    "scenes": context.get("scenes", []),
                    "emotions": context.get("emotions", [])
                }
                audit = await checker.run_full_audit(project_id, batch_id, breakdown_data, self.db)
                results.append({"type": "consistency_checker", "result": audit})
                if log_callback:
                    cb = log_callback(stage.name, "validator_result", "consistency_checker", audit)
                    if inspect.isawaitable(cb):
                        await cb
                final_status = audit.get("status", final_status)
                final_score = audit.get("overall_score", final_score)
                if final_status != "passed":
                    break
                continue

            # 绑定 Agent 作为 Validator
            if isinstance(validator, dict) and validator.get("type") == "agent":
                agent_name = validator.get("name") or validator.get("agent_name")
                agent_id = validator.get("id") or validator.get("agent_id")
                agent_result = await self._run_agent_validator(agent_name, agent_id, context)
                results.append({"type": "agent", "agent": agent_name or agent_id, "result": agent_result})
                if log_callback:
                    cb = log_callback(stage.name, "validator_result", f"agent:{agent_name or agent_id}", agent_result)
                    if inspect.isawaitable(cb):
                        await cb
                final_status = agent_result.get("status", "failed")
                if final_status != "passed":
                    break

        return {"status": final_status, "score": final_score, "results": results}

    async def _run_agent_validator(
        self,
        agent_name: Optional[str],
        agent_id: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        agent = await self._load_agent_definition(agent_name, agent_id)
        if not agent:
            return {"status": "failed", "message": "Validator Agent不存在"}

        prompt = self._build_agent_prompt(agent, context)
        response = await self._generate(prompt)
        parsed = self._parse_validator_response(response)
        parsed["raw_response"] = response
        parsed["agent"] = agent.name
        return parsed

    async def _load_agent_definition(
        self,
        agent_name: Optional[str],
        agent_id: Optional[str]
    ) -> Optional[AgentDefinition]:
        if agent_id:
            result = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
            return result.scalar_one_or_none()
        if agent_name:
            result = await self.db.execute(
                select(AgentDefinition).where(
                    AgentDefinition.name == agent_name,
                    AgentDefinition.is_active == True
                )
            )
            return result.scalar_one_or_none()
        return None

    def _build_agent_prompt(self, agent: AgentDefinition, context: Dict[str, Any]) -> str:
        input_payload = json.dumps(context, ensure_ascii=False, indent=2)
        prompt_template = agent.prompt_template or "{{input}}"
        prompt_body = prompt_template.replace("{{input}}", input_payload)

        parts = []
        if agent.role:
            parts.append(f"角色设定：{agent.role}")
        if agent.goal:
            parts.append(f"目标：{agent.goal}")
        if agent.system_prompt:
            parts.append(agent.system_prompt)
        parts.append(prompt_body)

        return "\n\n".join(parts)

    async def _generate(self, prompt: str) -> str:
        # 调用生成，请求返回使用量
        gen_result = self.model_adapter.generate(prompt, return_usage=True)
        if inspect.isawaitable(gen_result):
            gen_result = await gen_result

        # 如果返回了使用量信息，则进行计费
        if isinstance(gen_result, dict) and "usage" in gen_result:
            content = gen_result["content"]
            usage = gen_result["usage"]

            # 计费逻辑
            if self.user_id:
                try:
                    from app.core.credits import CreditsService
                    from app.models.ai_model import AIModel

                    credits_service = CreditsService(self.db)

                    # 获取 model_id (通过 model_name 查找)
                    model_name = getattr(self.model_adapter, "model_name", None)
                    model_id = None
                    if model_name:
                        stmt = select(AIModel.id).where(AIModel.model_key == model_name)
                        model_res = await self.db.execute(stmt)
                        model_id = model_res.scalar_one_or_none()

                    # 计算积分
                    amount = await credits_service.calculate_model_credits(
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        model_id=str(model_id) if model_id else None
                    )

                    # 扣减积分
                    if amount > 0:
                        await credits_service.consume_credits(
                            user_id=str(self.user_id),
                            amount=amount,
                            description=f"AI生成消耗 ({model_name or '未知模型'})",
                            reference_id=self.task_config.get("batch_id")
                        )
                except Exception as e:
                    # 计费失败不应中断主流程，实际生产中应记录日志
                    pass

            return content

        return gen_result

    def _parse_validator_response(self, response: str) -> Dict[str, Any]:
        # 尝试解析 JSON
        try:
            data = json.loads(response)
            status = data.get("status") or data.get("result")
            if isinstance(status, str):
                status_norm = status.lower()
                if status_norm in ("pass", "passed", "ok", "success", "true"):
                    return {"status": "passed", "details": data}
                if status_norm in ("fail", "failed", "error", "false"):
                    return {"status": "failed", "details": data}
            # 没有明确 status，则认为失败但保留详情
            return {"status": "failed", "details": data}
        except Exception:
            pass

        upper = response.upper()
        if "PASS" in upper or "PASSED" in upper:
            return {"status": "passed", "details": response.strip()}
        if "FAIL" in upper or "FAILED" in upper:
            return {"status": "failed", "details": response.strip()}

        return {"status": "failed", "details": response.strip()}

    async def _load_chapters(self, batch_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(Chapter).where(Chapter.batch_id == batch_id).order_by(Chapter.chapter_number)
        )
        chapters = result.scalars().all()
        return [
            {
                "chapter_number": ch.chapter_number,
                "title": ch.title,
                "content": ch.content,
                "word_count": ch.word_count
            }
            for ch in chapters
        ]

    async def _load_breakdown_data(self, breakdown_id: str) -> Dict[str, Any]:
        result = await self.db.execute(
            select(PlotBreakdown).where(PlotBreakdown.id == breakdown_id)
        )
        breakdown = result.scalar_one_or_none()
        if not breakdown:
            return {}
        return {
            "conflicts": breakdown.conflicts,
            "plot_hooks": breakdown.plot_hooks,
            "characters": breakdown.characters,
            "scenes": breakdown.scenes,
            "emotions": breakdown.emotions
        }

    @staticmethod
    def _looks_like_uuid(value: str) -> bool:
        return bool(re.match(r"^[0-9a-fA-F-]{36}$", value))

    async def get_adapt_method(self) -> str:
        """获取适配方法配置（返回 Markdown 内容）"""
        if self._adapt_method is None:
            key = self.task_config.get("adapt_method_key", "adapt_method_default")
            resource = await self._load_resource(key, "methodology")
            self._adapt_method = resource.content if resource else ""
        return self._adapt_method

    async def get_quality_rule(self) -> str:
        """获取质检规则配置（返回 Markdown 内容）"""
        if self._quality_rule is None:
            key = self.task_config.get("quality_rule_key", "qa_breakdown_default")
            resource = await self._load_resource(key, "qa_rules")
            self._quality_rule = resource.content if resource else ""
        return self._quality_rule

    async def get_output_style(self) -> str:
        """获取输出风格配置（返回 Markdown 内容）"""
        if self._output_style is None:
            key = self.task_config.get("output_style_key", "output_style_default")
            resource = await self._load_resource(key, "output_style")
            self._output_style = resource.content if resource else ""
        return self._output_style

    async def _load_resource(self, key: str, category: str):
        """加载 AI 资源（按 name 或 id 查找）"""
        from app.models.ai_resource import AIResource

        # 先尝试按 name 查找
        result = await self.db.execute(
            select(AIResource)
            .where(AIResource.name == key)
            .where(AIResource.category == category)
            .where(AIResource.is_active == True)
            .limit(1)
        )
        resource = result.scalar_one_or_none()

        # 如果按 name 找不到，尝试按 id 查找（兼容传入 UUID 的情况）
        if not resource and self._looks_like_uuid(key):
            result = await self.db.execute(
                select(AIResource)
                .where(AIResource.id == key)
                .where(AIResource.is_active == True)
                .limit(1)
            )
            resource = result.scalar_one_or_none()

        return resource
