"""模型凭证管理 API"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.utils.masking import mask_api_key
from app.models.ai_model_credential import AIModelCredential
from app.models.ai_model_provider import AIModelProvider
from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse
)
from app.api.v1.admin import check_admin

router = APIRouter()


@router.get("", response_model=List[CredentialResponse])
async def get_credentials(
    provider_id: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取凭证列表（API Key 脱敏显示）

    Args:
        provider_id: 可选，按提供商筛选
    """
    # 构建查询
    query = select(AIModelCredential, AIModelProvider).join(
        AIModelProvider,
        AIModelCredential.provider_id == AIModelProvider.id
    ).order_by(AIModelCredential.created_at.desc())

    # 如果指定了提供商，添加筛选条件
    if provider_id:
        query = query.where(AIModelCredential.provider_id == provider_id)

    result = await db.execute(query)

    credentials = []
    for credential, provider in result:
        # 脱敏显示 API Key
        masked_key = mask_api_key(credential.api_key)

        # 计算剩余配额
        quota_remaining = None
        if credential.quota_limit is not None:
            quota_remaining = credential.quota_limit - credential.quota_used

        credential_dict = {
            "id": str(credential.id),
            "provider": {
                "id": str(provider.id),
                "provider_key": provider.provider_key,
                "display_name": provider.display_name
            },
            "credential_name": credential.credential_name,
            "api_key_masked": masked_key,
            "is_active": credential.is_active,
            "is_system_default": credential.is_system_default,
            "quota_limit": credential.quota_limit,
            "quota_used": credential.quota_used,
            "quota_remaining": quota_remaining,
            "expires_at": credential.expires_at,
            "last_used_at": credential.last_used_at,
            "created_by": str(credential.created_by) if credential.created_by else None,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at
        }
        credentials.append(credential_dict)

    return credentials


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """获取凭证详情（API Key 脱敏显示）"""
    # 查询凭证及其提供商
    result = await db.execute(
        select(AIModelCredential, AIModelProvider)
        .join(AIModelProvider, AIModelCredential.provider_id == AIModelProvider.id)
        .where(AIModelCredential.id == credential_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="凭证不存在")

    credential, provider = row

    # 脱敏显示 API Key
    masked_key = mask_api_key(credential.api_key)

    # 计算剩余配额
    quota_remaining = None
    if credential.quota_limit is not None:
        quota_remaining = credential.quota_limit - credential.quota_used

    return {
        "id": str(credential.id),
        "provider": {
            "id": str(provider.id),
            "provider_key": provider.provider_key,
            "display_name": provider.display_name
        },
        "credential_name": credential.credential_name,
        "api_key_masked": masked_key,
        "is_active": credential.is_active,
        "is_system_default": credential.is_system_default,
        "quota_limit": credential.quota_limit,
        "quota_used": credential.quota_used,
        "quota_remaining": quota_remaining,
        "expires_at": credential.expires_at,
        "last_used_at": credential.last_used_at,
        "created_by": str(credential.created_by) if credential.created_by else None,
        "created_at": credential.created_at,
        "updated_at": credential.updated_at
    }


@router.post("", response_model=CredentialResponse)
async def create_credential(
    credential_data: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(check_admin)
):
    """创建凭证（明文存储，已移除加密）"""
    # 检查提供商是否存在
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.id == credential_data.provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 创建凭证（明文存储）
    credential = AIModelCredential(
        provider_id=credential_data.provider_id,
        credential_name=credential_data.credential_name,
        api_key=credential_data.api_key,
        api_secret=credential_data.api_secret,
        quota_limit=credential_data.quota_limit,
        expires_at=credential_data.expires_at,
        created_by=current_user.id
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)

    # 脱敏显示
    masked_key = mask_api_key(credential_data.api_key)

    # 计算剩余配额
    quota_remaining = None
    if credential.quota_limit is not None:
        quota_remaining = credential.quota_limit - credential.quota_used

    return {
        "id": str(credential.id),
        "provider": {
            "id": str(provider.id),
            "provider_key": provider.provider_key,
            "display_name": provider.display_name
        },
        "credential_name": credential.credential_name,
        "api_key_masked": masked_key,
        "is_active": credential.is_active,
        "is_system_default": credential.is_system_default,
        "quota_limit": credential.quota_limit,
        "quota_used": credential.quota_used,
        "quota_remaining": quota_remaining,
        "expires_at": credential.expires_at,
        "last_used_at": credential.last_used_at,
        "created_by": str(credential.created_by) if credential.created_by else None,
        "created_at": credential.created_at,
        "updated_at": credential.updated_at
    }


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    credential_data: CredentialUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """更新凭证"""
    # 查询凭证及其提供商
    result = await db.execute(
        select(AIModelCredential, AIModelProvider)
        .join(AIModelProvider, AIModelCredential.provider_id == AIModelProvider.id)
        .where(AIModelCredential.id == credential_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="凭证不存在")

    credential, provider = row

    # 更新字段
    update_data = credential_data.model_dump(exclude_unset=True)

    # 直接更新 API Key（明文存储）
    if "api_key" in update_data:
        credential.api_key = update_data["api_key"]
        del update_data["api_key"]

    # 直接更新 API Secret（明文存储）
    if "api_secret" in update_data:
        credential.api_secret = update_data["api_secret"]
        del update_data["api_secret"]

    # 更新其他字段
    for field, value in update_data.items():
        setattr(credential, field, value)

    await db.commit()
    await db.refresh(credential)

    # 脱敏显示
    masked_key = mask_api_key(credential.api_key)

    # 计算剩余配额
    quota_remaining = None
    if credential.quota_limit is not None:
        quota_remaining = credential.quota_limit - credential.quota_used

    return {
        "id": str(credential.id),
        "provider": {
            "id": str(provider.id),
            "provider_key": provider.provider_key,
            "display_name": provider.display_name
        },
        "credential_name": credential.credential_name,
        "api_key_masked": masked_key,
        "is_active": credential.is_active,
        "is_system_default": credential.is_system_default,
        "quota_limit": credential.quota_limit,
        "quota_used": credential.quota_used,
        "quota_remaining": quota_remaining,
        "expires_at": credential.expires_at,
        "last_used_at": credential.last_used_at,
        "created_by": str(credential.created_by) if credential.created_by else None,
        "created_at": credential.created_at,
        "updated_at": credential.updated_at
    }


@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """删除凭证"""
    # 查询凭证
    result = await db.execute(
        select(AIModelCredential).where(AIModelCredential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")

    # 如果是系统默认凭证，不允许删除
    if credential.is_system_default:
        raise HTTPException(status_code=400, detail="无法删除系统默认凭证，请先设置其他凭证为默认")

    # 删除凭证
    await db.delete(credential)
    await db.commit()

    return {"message": "凭证已删除"}


@router.post("/{credential_id}/toggle", response_model=CredentialResponse)
async def toggle_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """启用/禁用凭证"""
    # 查询凭证及其提供商
    result = await db.execute(
        select(AIModelCredential, AIModelProvider)
        .join(AIModelProvider, AIModelCredential.provider_id == AIModelProvider.id)
        .where(AIModelCredential.id == credential_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="凭证不存在")

    credential, provider = row

    # 如果是系统默认凭证且要禁用，不允许
    if credential.is_system_default and credential.is_active:
        raise HTTPException(status_code=400, detail="无法禁用系统默认凭证，请先设置其他凭证为默认")

    # 切换状态
    credential.is_active = not credential.is_active
    await db.commit()
    await db.refresh(credential)

    # 脱敏显示
    masked_key = mask_api_key(credential.api_key)

    # 计算剩余配额
    quota_remaining = None
    if credential.quota_limit is not None:
        quota_remaining = credential.quota_limit - credential.quota_used

    return {
        "id": str(credential.id),
        "provider": {
            "id": str(provider.id),
            "provider_key": provider.provider_key,
            "display_name": provider.display_name
        },
        "credential_name": credential.credential_name,
        "api_key_masked": masked_key,
        "is_active": credential.is_active,
        "is_system_default": credential.is_system_default,
        "quota_limit": credential.quota_limit,
        "quota_used": credential.quota_used,
        "quota_remaining": quota_remaining,
        "expires_at": credential.expires_at,
        "last_used_at": credential.last_used_at,
        "created_by": str(credential.created_by) if credential.created_by else None,
        "created_at": credential.created_at,
        "updated_at": credential.updated_at
    }


@router.post("/{credential_id}/test")
async def test_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_admin)
):
    """测试凭证有效性

    根据提供商类型调用对应的 API 进行真实测试
    使用提供商绑定的模型进行测试
    """
    from app.utils.credential_tester import test_credential as test_cred

    # 查询凭证及其提供商
    result = await db.execute(
        select(AIModelCredential, AIModelProvider)
        .join(AIModelProvider, AIModelCredential.provider_id == AIModelProvider.id)
        .where(AIModelCredential.id == credential_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="凭证不存在")

    credential, provider = row

    # 查询该提供商绑定的模型列表
    from app.models.ai_model import AIModel
    model_result = await db.execute(
        select(AIModel.model_key)
        .where(AIModel.provider_id == provider.id)
        .where(AIModel.is_enabled == True)
    )
    model_names = [row[0] for row in model_result.all()]

    # 调用测试函数，传入模型列表
    success, message = await test_cred(
        provider_type=provider.provider_type,
        api_key=credential.api_key,
        api_endpoint=provider.api_endpoint,
        api_secret=credential.api_secret,
        model_names=model_names if model_names else None
    )

    return {
        "success": success,
        "message": message,
        "provider_type": provider.provider_type,
        "provider_name": provider.display_name,
        "credential_name": credential.credential_name,
        "tested_models": model_names if model_names else []
    }
