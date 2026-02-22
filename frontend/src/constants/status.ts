export const TASK_STATUS = {
  PENDING: 'pending',
  QUEUED: 'queued',
  RUNNING: 'running',
  RETRYING: 'retrying',
  IN_PROGRESS: 'in_progress',
  CANCELLING: 'cancelling',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELED: 'canceled',
} as const;

export const BATCH_STATUS = {
  PENDING: 'pending',
  QUEUED: 'queued',
  IN_PROGRESS: 'in_progress',  // 与后端 BatchStatus.IN_PROGRESS 统一
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;
