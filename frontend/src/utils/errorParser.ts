/**
 * 错误解析工具
 * 统一处理各种错误格式，提取错误代码和消息
 */

export interface ParsedError {
  code: string;
  message: string;
}

/**
 * 解析错误消息
 * @param error - 任意格式的错误对象或字符串
 * @returns 标准化的错误对象
 */
export const parseErrorMessage = (error: any): ParsedError => {
  try {
    // 如果是字符串，尝试解析为 JSON
    const errorData = typeof error === 'string' ? JSON.parse(error) : error;

    return {
      code: errorData.code || 'UNKNOWN_ERROR',
      message: errorData.message || String(error)
    };
  } catch {
    // 解析失败，返回原始错误信息
    return {
      code: 'UNKNOWN_ERROR',
      message: String(error)
    };
  }
};
