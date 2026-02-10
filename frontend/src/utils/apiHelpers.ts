/**
 * API 响应处理辅助函数
 */

/**
 * 从 API 响应中提取数组数据
 * 支持分页格式 { items: [], total: ... } 和直接数组格式
 */
export function extractArrayData<T>(data: any): T[] {
  if (!data) {
    return [];
  }
  
  // 如果是分页格式
  if (typeof data === 'object' && 'items' in data && Array.isArray(data.items)) {
    return data.items;
  }
  
  // 如果是直接数组格式
  if (Array.isArray(data)) {
    return data;
  }
  
  console.warn('意外的响应格式:', data);
  return [];
}

/**
 * 从 API 响应中提取分页信息
 */
export function extractPaginationInfo(data: any): {
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
} {
  if (typeof data === 'object' && 'total' in data) {
    return {
      total: data.total || 0,
      page: data.page || 1,
      pageSize: data.page_size || 20,
      totalPages: data.total_pages || 0,
    };
  }
  
  // 如果是数组格式，返回默认分页信息
  const items = Array.isArray(data) ? data : [];
  return {
    total: items.length,
    page: 1,
    pageSize: items.length,
    totalPages: 1,
  };
}
