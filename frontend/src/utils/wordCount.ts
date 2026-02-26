/**
 * 剧本字数计算工具
 *
 * 与后端 calculate_word_count() 保持一致的计算逻辑
 */

/**
 * 计算剧本字数（去除格式标记）
 *
 * 规则：
 * - 去除场景标记：※ 场景名称（时间）
 * - 去除动作标记：△
 * - 去除特效标记：【xxx】
 * - 去除所有空白字符
 *
 * @param text 剧本文本
 * @returns 字数（不包括格式标记）
 */
export function calculateWordCount(text: string): number {
  if (!text) {
    return 0;
  }

  let cleanText = text;

  // 去除场景标记：※ 场景名称（时间）
  cleanText = cleanText.replace(/※.*?（.*?）/g, '');

  // 去除动作标记：△
  cleanText = cleanText.replace(/△/g, '');

  // 去除特效标记：【xxx】
  cleanText = cleanText.replace(/【.*?】/g, '');

  // 去除所有空白字符（空格、换行、制表符等）
  cleanText = cleanText.replace(/\s+/g, '');

  return cleanText.length;
}

/**
 * 计算四段式结构的总字数
 *
 * @param structure 四段式结构对象
 * @returns 总字数
 */
export function calculateStructureWordCount(structure: {
  opening?: { content: string };
  development?: { content: string };
  climax?: { content: string };
  hook?: { content: string };
}): number {
  const sections = ['opening', 'development', 'climax', 'hook'] as const;

  return sections.reduce((total, section) => {
    const content = structure[section]?.content || '';
    return total + calculateWordCount(content);
  }, 0);
}
