# 用户等级系统集成

## Goal
将已实现的配额服务集成到业务流程中，在创建项目和生成剧本时进行配额检查。

## Requirements

1. **项目创建配额检查**
   - 在 `projects.py` 的 `create_project` 函数中添加配额检查
   - 配额不足时返回 403 错误

2. **剧本生成配额检查**
   - 在 `scripts.py` 的 `generate_script` 函数中添加配额检查
   - 生成成功后消耗配额

3. **剧情拆解配额检查**
   - 在 `breakdown.py` 的 `start_breakdown` 函数中添加配额检查
   - 拆解成功后消耗配额

## Acceptance Criteria

- [ ] 创建项目时检查项目配额，超限返回 403
- [ ] 生成剧本时检查剧集配额，超限返回 403
- [ ] 剧情拆解时检查剧集配额，超限返回 403
- [ ] 配额消耗正确记录到用户表

## Technical Notes

使用已实现的 `QuotaService`:
```python
from app.core.quota import QuotaService

service = QuotaService(db)
quota = await service.check_project_quota(user)
if not quota["allowed"]:
    raise HTTPException(status_code=403, detail="项目配额已用尽")
```

需要修改的文件：
- `backend/app/api/v1/projects.py`
- `backend/app/api/v1/scripts.py`
- `backend/app/api/v1/breakdown.py`
