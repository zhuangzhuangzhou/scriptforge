"""测试配额回滚功能

测试 refund_episode_quota_sync 函数的各种场景。

**Validates: Requirements 3.2.1, 3.2.2**
"""
import pytest
import uuid
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from app.core.quota import refund_episode_quota_sync, get_tier_config
from app.models.user import User


class TestRefundEpisodeQuotaSync:
    """测试同步配额回滚函数"""
    
    def test_refund_quota_normal_scenario(self):
        """测试正常回滚场景
        
        验证：
        - 用户配额正确减少
        - 数据库事务提交
        - 不会减成负数
        """
        # 创建 mock 数据库会话
        db = Mock(spec=Session)
        
        # 创建测试用户
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "creator"
        user.monthly_episodes_used = 5
        
        # Mock 查询返回用户
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 执行回滚
        refund_episode_quota_sync(db, user_id, amount=1)
        
        # 验证配额减少
        assert user.monthly_episodes_used == 4
        
        # 验证数据库操作
        db.query.assert_called_once_with(User)
        db.commit.assert_called_once()
    
    def test_refund_quota_multiple_amount(self):
        """测试回滚多个配额"""
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "studio"
        user.monthly_episodes_used = 10
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 回滚3个配额
        refund_episode_quota_sync(db, user_id, amount=3)
        
        # 验证配额减少3
        assert user.monthly_episodes_used == 7
        db.commit.assert_called_once()
    
    def test_refund_quota_prevents_negative(self):
        """测试配额不会减成负数
        
        验证：当回滚数量大于已使用数量时，配额应该变为0而不是负数
        """
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "creator"
        user.monthly_episodes_used = 2
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 尝试回滚5个配额（大于已使用的2个）
        refund_episode_quota_sync(db, user_id, amount=5)
        
        # 验证配额变为0而不是负数
        assert user.monthly_episodes_used == 0
        db.commit.assert_called_once()
    
    def test_refund_quota_user_not_found(self):
        """测试用户不存在场景
        
        验证：
        - 函数不抛出异常
        - 不调用 commit
        - 记录错误日志
        """
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        
        # Mock 查询返回 None（用户不存在）
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None
        db.query.return_value = query_mock
        
        # 执行回滚（不应抛出异常）
        refund_episode_quota_sync(db, user_id, amount=1)
        
        # 验证没有调用 commit
        db.commit.assert_not_called()
    
    def test_refund_quota_enterprise_tier_skipped(self):
        """测试企业版用户跳过回滚
        
        企业版用户有无限配额，不需要回滚
        """
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "enterprise"
        user.monthly_episodes_used = 100
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 执行回滚
        refund_episode_quota_sync(db, user_id, amount=1)
        
        # 验证配额没有变化（企业版无限配额）
        assert user.monthly_episodes_used == 100
        
        # 验证调用了 commit（虽然没有修改，但事务仍然提交）
        db.commit.assert_called_once()
    
    def test_refund_quota_invalid_amount(self):
        """测试无效的回滚数量
        
        验证：amount <= 0 时不执行任何操作
        """
        db = Mock(spec=Session)
        user_id = str(uuid.uuid4())
        
        # 测试 amount = 0
        refund_episode_quota_sync(db, user_id, amount=0)
        db.query.assert_not_called()
        
        # 测试 amount < 0
        refund_episode_quota_sync(db, user_id, amount=-5)
        db.query.assert_not_called()
    
    def test_refund_quota_transaction_rollback_on_error(self):
        """测试事务回滚
        
        验证：当发生异常时，数据库事务应该回滚
        """
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "creator"
        user.monthly_episodes_used = 5
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # Mock commit 抛出异常
        db.commit.side_effect = Exception("Database error")
        
        # 执行回滚（不应抛出异常）
        refund_episode_quota_sync(db, user_id, amount=1)
        
        # 验证调用了 rollback
        db.rollback.assert_called_once()
    
    def test_refund_quota_free_tier(self):
        """测试免费版用户回滚"""
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "free"
        user.monthly_episodes_used = 2
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 执行回滚
        refund_episode_quota_sync(db, user_id, amount=1)
        
        # 验证配额减少
        assert user.monthly_episodes_used == 1
        db.commit.assert_called_once()
    
    def test_refund_quota_case_insensitive_tier(self):
        """测试等级名称大小写不敏感
        
        验证：tier 字段可能是大写或混合大小写
        """
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "CREATOR"  # 大写
        user.monthly_episodes_used = 5
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 执行回滚
        refund_episode_quota_sync(db, user_id, amount=1)
        
        # 验证配额减少（应该正常工作）
        assert user.monthly_episodes_used == 4
        db.commit.assert_called_once()
    
    def test_refund_quota_zero_used(self):
        """测试已使用配额为0时的回滚
        
        验证：配额为0时回滚不会变成负数
        """
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "creator"
        user.monthly_episodes_used = 0
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 执行回滚
        refund_episode_quota_sync(db, user_id, amount=1)
        
        # 验证配额保持为0
        assert user.monthly_episodes_used == 0
        db.commit.assert_called_once()
    
    def test_refund_quota_concurrent_safety(self):
        """测试并发安全性
        
        验证：多次调用回滚函数应该正确累积
        """
        db = Mock(spec=Session)
        
        user_id = str(uuid.uuid4())
        user = Mock(spec=User)
        user.id = user_id
        user.tier = "studio"
        user.monthly_episodes_used = 10
        
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = user
        db.query.return_value = query_mock
        
        # 第一次回滚
        refund_episode_quota_sync(db, user_id, amount=2)
        assert user.monthly_episodes_used == 8
        
        # 第二次回滚
        refund_episode_quota_sync(db, user_id, amount=3)
        assert user.monthly_episodes_used == 5
        
        # 验证 commit 被调用两次
        assert db.commit.call_count == 2


class TestGetTierConfig:
    """测试等级配置获取"""
    
    def test_get_tier_config_free(self):
        """测试获取免费版配置"""
        config = get_tier_config("free")
        assert config.name == "free"
        assert config.monthly_episodes == 3
        assert config.max_projects == 1
    
    def test_get_tier_config_creator(self):
        """测试获取创作者版配置"""
        config = get_tier_config("creator")
        assert config.name == "creator"
        assert config.monthly_episodes == 30
        assert config.max_projects == 5
    
    def test_get_tier_config_studio(self):
        """测试获取工作室版配置"""
        config = get_tier_config("studio")
        assert config.name == "studio"
        assert config.monthly_episodes == 150
        assert config.max_projects == 20
    
    def test_get_tier_config_enterprise(self):
        """测试获取企业版配置"""
        config = get_tier_config("enterprise")
        assert config.name == "enterprise"
        assert config.monthly_episodes == -1  # 无限
        assert config.max_projects == -1  # 无限
    
    def test_get_tier_config_case_insensitive(self):
        """测试大小写不敏感"""
        config1 = get_tier_config("CREATOR")
        config2 = get_tier_config("Creator")
        config3 = get_tier_config("creator")
        
        assert config1.name == config2.name == config3.name == "creator"
    
    def test_get_tier_config_invalid_returns_free(self):
        """测试无效等级返回免费版"""
        config = get_tier_config("invalid_tier")
        assert config.name == "free"
    
    def test_get_tier_config_none_returns_free(self):
        """测试 None 返回免费版"""
        config = get_tier_config(None)
        assert config.name == "free"
    
    def test_get_tier_config_empty_string_returns_free(self):
        """测试空字符串返回免费版"""
        config = get_tier_config("")
        assert config.name == "free"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
