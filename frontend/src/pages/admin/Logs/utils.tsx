import { Tag, message } from 'antd';
import dayjs from 'dayjs';

/**
 * 格式化完整时间
 */
export const formatFullTime = (timeStr: string | null): string => {
  if (!timeStr) return '-';
  return dayjs(timeStr).format('YYYY-MM-DD HH:mm:ss');
};

/**
 * 获取任务状态标签
 */
export const getStatusTag = (status: string) => {
  const config: Record<string, { color: string; text: string }> = {
    queued: { color: 'default', text: '排队中' },
    running: { color: 'processing', text: '运行中' },
    pending: { color: 'default', text: '等待中' },
    completed: { color: 'success', text: '已完成' },
    failed: { color: 'error', text: '失败' },
    success: { color: 'success', text: '成功' }
  };
  const { color, text } = config[status] || { color: 'default', text: status };
  return <Tag color={color}>{text}</Tag>;
};

/**
 * 获取任务类型标签
 */
export const getTaskTypeTag = (taskType: string) => {
  const config: Record<string, { color: string; text: string }> = {
    breakdown: { color: 'blue', text: '剧情拆解' },
    script_generation: { color: 'purple', text: '剧本生成' },
    batch_breakdown: { color: 'cyan', text: '批量拆解' },
    batch_script: { color: 'magenta', text: '批量剧本生成' },
    ai_agent: { color: 'green', text: 'AI智能体' }
  };
  const { color, text } = config[taskType] || { color: 'default', text: taskType };
  return <Tag color={color}>{text}</Tag>;
};

/**
 * 处理API错误
 */
export const handleApiError = (error: unknown, defaultMsg = '操作失败'): string => {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const axiosError = error as { response?: { data?: { detail?: string } } };
    if (axiosError.response?.data?.detail) {
      return axiosError.response.data.detail;
    }
  }
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return (error as { message: string }).message;
  }
  return defaultMsg;
};
