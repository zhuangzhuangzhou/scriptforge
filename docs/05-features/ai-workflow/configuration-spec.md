# AI Configuration Specification

本文档定义了 AI Engine 中动态配置的数据结构和规范。

## 1. Adaptation Method (改编方法论)

改编方法论定义了 AI 如何理解和重构小说。

### Schema
```typescript
interface AdaptMethodConfig {
  id: string;
  name: string;
  description: string;
  version: string;

  // 核心规则参数
  parameters: {
    target_audience: string; // e.g., "Teenagers", "Young Adults"
    episode_duration: string; // e.g., "1-2 minutes"
    word_count_range: [number, number]; // e.g., [500, 800]
    style_keywords: string[]; // e.g., ["Fast-paced", "Visual", "Emotional"]
  };

  // 提示词模板覆盖 (Optional)
  // 如果不提供，使用系统默认 Prompt
  prompts?: {
    conflict_extraction?: string;
    plot_breakdown?: string;
    script_generation?: string;
  };

  // 规则集 (用于 Reviewer)
  rules: {
    conflict_density: "Low" | "Medium" | "High";
    min_hooks_per_episode: number;
    forbidden_elements: string[]; // e.g., ["Internal Monologue", "Flashbacks > 10s"]
  };
}
```

### 默认配置示例
```json
{
  "name": "Default Webtoon Style",
  "parameters": {
    "episode_duration": "1-2 minutes",
    "word_count_range": [500, 800],
    "style_keywords": ["Visual", "Conflict-driven", "Fast-paced"]
  },
  "rules": {
    "conflict_density": "High",
    "min_hooks_per_episode": 1,
    "forbidden_elements": ["Long narration", "Complex psychological description"]
  }
}
```

---

## 2. Reviewer Configuration (质检配置)

定义 Reviewer 的行为模式和严格程度。

### Schema
```typescript
interface ReviewerConfig {
  id: string;
  name: string;

  // 严格程度
  strictness: "Lenient" | "Standard" | "Strict";

  // 自动修正设置
  auto_fix: {
    enabled: boolean;
    max_retries: number; // default: 3
  };

  // 检查维度开关
  checks: {
    format_compliance: boolean; // 格式是否符合模板
    word_count: boolean; // 字数是否在范围内
    conflict_check: boolean; // 是否包含足够冲突
    pacing_check: boolean; // 节奏是否拖沓
    visual_check: boolean; // 是否便于视觉化
    consistency_check: boolean; // 前后逻辑一致性
  };

  // 评分权重 (Total = 100)
  weights: {
    structure: number;
    plot: number;
    character: number;
    pacing: number;
  };
}
```

### 默认配置示例
```json
{
  "name": "Standard Review",
  "strictness": "Standard",
  "auto_fix": {
    "enabled": true,
    "max_retries": 3
  },
  "checks": {
    "format_compliance": true,
    "word_count": true,
    "conflict_check": true,
    "pacing_check": true,
    "visual_check": true,
    "consistency_check": false // 拆解阶段通常不做深度一致性检查
  }
}
```
