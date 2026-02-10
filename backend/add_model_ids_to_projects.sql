-- 添加模型 ID 字段到项目表
-- 执行时间: 2026-02-10

-- 1. 添加剧情拆解模型 ID 列
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS breakdown_model_id UUID;

-- 2. 添加剧本生成模型 ID 列
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS script_model_id UUID;

-- 3. 添加外键约束（剧情拆解模型）
ALTER TABLE projects 
ADD CONSTRAINT fk_projects_breakdown_model 
FOREIGN KEY (breakdown_model_id) 
REFERENCES ai_models(id) 
ON DELETE SET NULL;

-- 4. 添加外键约束（剧本生成模型）
ALTER TABLE projects 
ADD CONSTRAINT fk_projects_script_model 
FOREIGN KEY (script_model_id) 
REFERENCES ai_models(id) 
ON DELETE SET NULL;

-- 5. 添加注释
COMMENT ON COLUMN projects.breakdown_model_id IS '剧情拆解使用的 AI 模型 ID';
COMMENT ON COLUMN projects.script_model_id IS '剧本生成使用的 AI 模型 ID';

-- 6. 可选：设置默认模型（如果有默认模型）
-- UPDATE projects 
-- SET breakdown_model_id = (
--     SELECT id FROM ai_models 
--     WHERE is_enabled = true AND is_default = true 
--     LIMIT 1
-- )
-- WHERE breakdown_model_id IS NULL;

-- 7. 验证
SELECT 
    COUNT(*) as total_projects,
    COUNT(breakdown_model_id) as projects_with_breakdown_model,
    COUNT(script_model_id) as projects_with_script_model
FROM projects;
