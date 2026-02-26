# 用户资料编辑与密码修改功能完善

## 概述

完善用户个人设置功能，包括资料编辑（用户名、昵称、头像）和密码修改。

## 背景

当前系统中用户下拉菜单已有"编辑资料"和"修改密码"入口（`MainLayout.tsx:161-173`），但点击后仅显示"功能即将上线"提示，需要实现完整功能。

---

## 一、功能设计

### 1.1 用户资料编辑

#### 可编辑字段
| 字段 | 说明 | 校验规则 |
|-----|------|---------|
| username | 用户名 | 3-20字符，字母数字下划线，唯一 |
| full_name | 昵称/全名 | 可选，最长50字符 |
| avatar_url | 头像 | 可选，URL或上传 |

#### API 端点
```
PUT /auth/profile
```

#### 请求体
```json
{
  "username": "new_username",
  "full_name": "新昵称",
  "avatar_url": "https://..."
}
```

#### 响应
```json
{
  "id": "uuid",
  "username": "new_username",
  "email": "user@example.com",
  "full_name": "新昵称",
  "avatar_url": "https://...",
  "message": "资料更新成功"
}
```

### 1.2 修改密码

#### API 端点
```
PUT /auth/password
```

#### 请求体
```json
{
  "current_password": "旧密码",
  "new_password": "新密码",
  "confirm_password": "确认新密码"
}
```

#### 校验规则
- 旧密码必须正确
- 新密码长度 >= 6 字符
- 新密码与确认密码一致
- 新密码不能与旧密码相同

#### 响应
```json
{
  "success": true,
  "message": "密码修改成功"
}
```

---

## 二、数据模型

当前 `User` 模型已包含所需字段，无需迁移：

```python
# backend/app/models/user.py
class User(Base):
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    hashed_password = Column(String(255), nullable=False)
```

---

## 三、后端实现

### 3.1 API 端点 (auth.py)

```python
# 新增 Pydantic 模型
class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=20)
    full_name: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str

# 新增端点
@router.put("/profile")
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户资料"""
    # 检查用户名唯一性
    if data.username and data.username != current_user.username:
        exists = await db.execute(
            select(User).where(User.username == data.username)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(400, "用户名已被使用")
        current_user.username = data.username

    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url

    await db.commit()
    return {"message": "资料更新成功", ...}


@router.put("/password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "当前密码错误")

    # 验证新密码
    if data.new_password != data.confirm_password:
        raise HTTPException(400, "两次输入的新密码不一致")

    if data.current_password == data.new_password:
        raise HTTPException(400, "新密码不能与旧密码相同")

    # 更新密码
    current_user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"success": True, "message": "密码修改成功"}
```

---

## 四、前端实现

### 4.1 文件清单

| 文件 | 说明 |
|-----|-----|
| `components/modals/ProfileEditModal.tsx` | 资料编辑弹窗 |
| `components/modals/PasswordChangeModal.tsx` | 密码修改弹窗 |
| `components/MainLayout.tsx` | 集成弹窗 |
| `services/api.ts` | 添加 API 方法 |

### 4.2 ProfileEditModal 设计

```tsx
// 表单字段
- 用户名输入框（带唯一性校验提示）
- 昵称输入框
- 头像预览 + 上传按钮（可选：使用 DiceBear 随机头像）

// 按钮
- 取消
- 保存
```

### 4.3 PasswordChangeModal 设计

```tsx
// 表单字段
- 当前密码（密码输入框）
- 新密码（密码输入框 + 强度提示）
- 确认新密码

// 按钮
- 取消
- 确认修改
```

### 4.4 MainLayout 集成

```tsx
// 修改 MainLayout.tsx:161-173
<button onClick={() => setIsProfileEditOpen(true)}>编辑资料</button>
<button onClick={() => setIsPasswordChangeOpen(true)}>修改密码</button>

// 添加弹窗
{isProfileEditOpen && <ProfileEditModal onClose={...} onSuccess={...} />}
{isPasswordChangeOpen && <PasswordChangeModal onClose={...} />}
```

---

## 五、子任务拆分

| 序号 | 任务 | 类型 | 预估 |
|-----|------|-----|------|
| 1 | 实现 PUT /auth/profile API | 后端 | 1h |
| 2 | 实现 PUT /auth/password API | 后端 | 1h |
| 3 | 创建 ProfileEditModal.tsx | 前端 | 2h |
| 4 | 创建 PasswordChangeModal.tsx | 前端 | 1.5h |
| 5 | 修改 MainLayout.tsx 集成弹窗 | 前端 | 0.5h |
| 6 | 添加 API 方法到 api.ts | 前端 | 0.5h |
| 7 | 测试完整流程 | 测试 | 1h |

**总预估**: 约 8 小时（1 天）

---

## 六、验收标准

- [ ] 用户可修改用户名（唯一性校验）
- [ ] 用户可修改昵称
- [ ] 用户可修改头像（URL 或上传）
- [ ] 用户可修改密码（旧密码验证）
- [ ] 修改成功后界面实时更新
- [ ] 错误提示友好清晰
- [ ] 密码修改后不强制重新登录（可选）

---

## 七、UI 设计参考

### 资料编辑弹窗
```
┌─────────────────────────────────────┐
│  编辑资料                      [X]  │
├─────────────────────────────────────┤
│                                     │
│      ┌─────┐                        │
│      │ 头像 │  [更换头像]           │
│      └─────┘                        │
│                                     │
│  用户名                             │
│  ┌─────────────────────────────┐   │
│  │ current_username            │   │
│  └─────────────────────────────┘   │
│                                     │
│  昵称                               │
│  ┌─────────────────────────────┐   │
│  │ 可选填写                     │   │
│  └─────────────────────────────┘   │
│                                     │
│         [取消]    [保存]            │
└─────────────────────────────────────┘
```

### 密码修改弹窗
```
┌─────────────────────────────────────┐
│  修改密码                      [X]  │
├─────────────────────────────────────┤
│                                     │
│  当前密码                           │
│  ┌─────────────────────────────┐   │
│  │ ••••••••                    │   │
│  └─────────────────────────────┘   │
│                                     │
│  新密码                             │
│  ┌─────────────────────────────┐   │
│  │ ••••••••                    │   │
│  └─────────────────────────────┘   │
│  密码强度: ████░░ 中等              │
│                                     │
│  确认新密码                         │
│  ┌─────────────────────────────┐   │
│  │ ••••••••                    │   │
│  └─────────────────────────────┘   │
│                                     │
│         [取消]    [确认修改]        │
└─────────────────────────┘
```
