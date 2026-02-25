/**
 * 错误解析工具
 * 统一处理各种错误格式，提取错误代码和消息
 */

export interface ParsedError {
  code: string;
  message: string;
  suggestion?: string;
}

/**
 * 解析错误消息（完整版，支持 suggestion）
 * @param error - 任意格式的错误对象或字符串
 * @returns 标准化的错误对象
 */
export const parseErrorMessage = (error: any): ParsedError => {
  let errorCode = 'UNKNOWN_ERROR';
  let errorMessage = '操作失败';
  let errorSuggestion = '';

  try {
    // 如果是 Axios 错误响应，提取 response.data
    const errorData = error?.response?.data || error;

    // 优先使用 error_display（人性化错误信息）
    if (errorData?.error_display && typeof errorData.error_display === 'object') {
      errorCode = errorData.error_display.code || errorCode;
      errorMessage = errorData.error_display.description || errorData.error_display.message || errorMessage;
      errorSuggestion = errorData.error_display.suggestion || '';
    } else if (errorData?.error_message) {
      // 回退到解析 error_message
      const errorMsg = errorData.error_message;
      try {
        const parsed = typeof errorMsg === 'string' ? JSON.parse(errorMsg) : errorMsg;
        errorCode = parsed.code || errorCode;
        errorMessage = parsed.message || errorMsg;
      } catch {
        errorMessage = errorMsg;
      }
    } else if (errorData?.detail) {
      // 直接使用 detail
      errorMessage = errorData.detail;
    } else if (typeof error === 'string') {
      // 如果是字符串，尝试解析为 JSON
      try {
        const parsed = JSON.parse(error);
        errorCode = parsed.code || errorCode;
        errorMessage = parsed.message || error;
      } catch {
        errorMessage = error;
      }
    }
  } catch {
    // 解析失败，返回原始错误信息
    errorMessage = String(error);
  }

  return {
    code: errorCode,
    message: errorMessage,
    suggestion: errorSuggestion
  };
};
