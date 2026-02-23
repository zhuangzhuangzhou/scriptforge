"""批次状态管理单元测试

测试场景：
1. 拆解任务失败，有之前的成功结果 → 应恢复为 completed
2. 拆解任务失败，无之前的成功结果 → 应标记为 failed
3. 剧本任务失败 → 不应影响 breakdown_status
4. 管理员停止拆解任务（有历史）→ 应触发智能回滚
5. 管理员停止剧本任务 → 不应影响 breakdown_status
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from app.core.status import BatchStatus, TaskStatus


class MockBatch:
    """模拟批次对象"""
    def __init__(self, batch_id=None, breakdown_status="pending", script_status="pending"):
        self.id = batch_id or uuid4()
        self.breakdown_status = breakdown_status
        self.script_status = script_status


class MockTask:
    """模拟任务对象"""
    def __init__(self, task_id=None, batch_id=None, task_type="breakdown", status="running"):
        self.id = task_id or uuid4()
        self.batch_id = batch_id
        self.task_type = task_type
        self.status = status


class TestUpdateBatchStatusSafely:
    """测试 _update_batch_status_safely 函数"""

    def test_breakdown_task_failed_with_previous_success(self):
        """场景1: 拆解任务失败，但有之前的成功结果 → 应恢复为 completed"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(breakdown_status=BatchStatus.IN_PROGRESS)
        task = MockTask(batch_id=batch.id, task_type="breakdown")
        mock_db = Mock()
        mock_logger = Mock()

        # Mock: 有之前的成功结果
        with patch('app.tasks.breakdown_tasks._check_previous_breakdown_success', return_value=True):
            _update_batch_status_safely(
                batch=batch,
                task=task,
                new_status=BatchStatus.FAILED,
                db=mock_db,
                logger=mock_logger
            )

        # 验证：状态应恢复为 completed
        assert batch.breakdown_status == BatchStatus.COMPLETED
        mock_logger.info.assert_called()

    def test_breakdown_task_failed_without_previous_success(self):
        """场景2: 拆解任务失败，无之前的成功结果 → 应标记为 failed"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(breakdown_status=BatchStatus.IN_PROGRESS)
        task = MockTask(batch_id=batch.id, task_type="breakdown")
        mock_db = Mock()
        mock_logger = Mock()

        # Mock: 无之前的成功结果
        with patch('app.tasks.breakdown_tasks._check_previous_breakdown_success', return_value=False):
            _update_batch_status_safely(
                batch=batch,
                task=task,
                new_status=BatchStatus.FAILED,
                db=mock_db,
                logger=mock_logger
            )

        # 验证：状态应为 failed
        assert batch.breakdown_status == BatchStatus.FAILED

    def test_script_task_failed_should_not_affect_breakdown_status(self):
        """场景3: 剧本任务失败 → 不应影响 breakdown_status"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(
            breakdown_status=BatchStatus.COMPLETED,
            script_status=BatchStatus.IN_PROGRESS
        )
        task = MockTask(batch_id=batch.id, task_type="script")
        mock_db = Mock()
        mock_logger = Mock()

        _update_batch_status_safely(
            batch=batch,
            task=task,
            new_status=BatchStatus.FAILED,
            db=mock_db,
            logger=mock_logger
        )

        # 验证：breakdown_status 应保持不变
        assert batch.breakdown_status == BatchStatus.COMPLETED
        # 验证：script_status 应更新为 failed
        assert batch.script_status == BatchStatus.FAILED

    def test_episode_script_task_failed_should_not_affect_breakdown_status(self):
        """场景3b: episode_script 任务失败 → 不应影响 breakdown_status"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(
            breakdown_status=BatchStatus.COMPLETED,
            script_status=BatchStatus.IN_PROGRESS
        )
        task = MockTask(batch_id=batch.id, task_type="episode_script")
        mock_db = Mock()
        mock_logger = Mock()

        _update_batch_status_safely(
            batch=batch,
            task=task,
            new_status=BatchStatus.FAILED,
            db=mock_db,
            logger=mock_logger
        )

        # 验证：breakdown_status 应保持不变
        assert batch.breakdown_status == BatchStatus.COMPLETED
        # 验证：script_status 应更新为 failed
        assert batch.script_status == BatchStatus.FAILED

    def test_admin_stop_breakdown_with_previous_success(self):
        """场景4: 管理员停止拆解任务（有历史）→ 应触发智能回滚"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(breakdown_status=BatchStatus.IN_PROGRESS)
        task = MockTask(batch_id=batch.id, task_type="breakdown")
        mock_db = Mock()
        mock_logger = Mock()

        with patch('app.tasks.breakdown_tasks._check_previous_breakdown_success', return_value=True):
            _update_batch_status_safely(
                batch=batch,
                task=task,
                new_status=BatchStatus.FAILED,
                db=mock_db,
                logger=mock_logger
            )

        assert batch.breakdown_status == BatchStatus.COMPLETED

    def test_admin_stop_script_task(self):
        """场景5: 管理员停止剧本任务 → 不应影响 breakdown_status"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(
            breakdown_status=BatchStatus.COMPLETED,
            script_status=BatchStatus.IN_PROGRESS
        )
        task = MockTask(batch_id=batch.id, task_type="script")
        mock_db = Mock()
        mock_logger = Mock()

        _update_batch_status_safely(
            batch=batch,
            task=task,
            new_status=BatchStatus.FAILED,
            db=mock_db,
            logger=mock_logger
        )

        assert batch.breakdown_status == BatchStatus.COMPLETED
        assert batch.script_status == BatchStatus.FAILED

    def test_unknown_task_type_defaults_to_breakdown(self):
        """未知任务类型默认更新 breakdown_status"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(breakdown_status=BatchStatus.IN_PROGRESS)
        task = MockTask(batch_id=batch.id, task_type="unknown_type")
        mock_db = Mock()
        mock_logger = Mock()

        with patch('app.tasks.breakdown_tasks._check_previous_breakdown_success', return_value=False):
            _update_batch_status_safely(
                batch=batch,
                task=task,
                new_status=BatchStatus.FAILED,
                db=mock_db,
                logger=mock_logger
            )

        # 验证：默认更新 breakdown_status
        assert batch.breakdown_status == BatchStatus.FAILED
        # 验证：记录了警告日志
        mock_logger.warning.assert_called()

    def test_successful_status_update(self):
        """成功状态更新不触发智能回滚"""
        from app.tasks.breakdown_tasks import _update_batch_status_safely

        batch = MockBatch(breakdown_status=BatchStatus.IN_PROGRESS)
        task = MockTask(batch_id=batch.id, task_type="breakdown")
        mock_db = Mock()
        mock_logger = Mock()

        # 不需要 mock _check_previous_breakdown_success，因为只有 FAILED 状态才会检查
        _update_batch_status_safely(
            batch=batch,
            task=task,
            new_status=BatchStatus.COMPLETED,
            db=mock_db,
            logger=mock_logger
        )

        # 验证：状态直接更新为 completed
        assert batch.breakdown_status == BatchStatus.COMPLETED


class TestValidateStatusConsistency:
    """测试 _validate_status_consistency 函数"""

    def test_breakdown_completed_status_correct(self):
        """拆解任务完成，状态正确"""
        from app.tasks.breakdown_tasks import _validate_status_consistency

        batch = MockBatch(breakdown_status=BatchStatus.COMPLETED)
        task = MockTask(task_type="breakdown", status=TaskStatus.COMPLETED)
        mock_logger = Mock()

        _validate_status_consistency(batch, task, mock_logger)

        # 应该记录成功日志
        mock_logger.info.assert_called()
        mock_logger.warning.assert_not_called()

    def test_breakdown_completed_status_incorrect(self):
        """拆解任务完成，但状态不正确"""
        from app.tasks.breakdown_tasks import _validate_status_consistency

        batch = MockBatch(breakdown_status=BatchStatus.IN_PROGRESS)
        task = MockTask(task_type="breakdown", status=TaskStatus.COMPLETED)
        mock_logger = Mock()

        _validate_status_consistency(batch, task, mock_logger)

        # 应该记录警告日志
        mock_logger.warning.assert_called()

    def test_script_failed_affects_breakdown_status_error(self):
        """剧本任务失败错误地影响了 breakdown_status"""
        from app.tasks.breakdown_tasks import _validate_status_consistency

        batch = MockBatch(
            breakdown_status=BatchStatus.FAILED,
            script_status=BatchStatus.FAILED
        )
        task = MockTask(task_type="script", status=TaskStatus.FAILED)
        mock_logger = Mock()

        _validate_status_consistency(batch, task, mock_logger)

        # 应该记录错误日志
        mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
