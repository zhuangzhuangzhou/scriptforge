# 文档版本号规范

## 目标
为规范类文档提供统一的版本与更新记录方式，便于团队协作和历史追溯。

---

## 一、适用范围

以下文档需要维护版本号：
- `docs/spec-workflow.md`
- `docs/spec-config-driven.md`
- `docs/spec-storage-contract.md`
- `docs/spec-document-policy.md`
- `docs/spec-document-versioning.md`

建议维护版本号：
- `docs/plan-implementation.md`
- `docs/product-business-analysis.md`

---

## 二、版本号格式

采用语义化版本：
- **主版本号**：流程或规则发生重大调整
- **次版本号**：新增规则或模块
- **修订号**：小幅文字修正或表述更新

格式示例：
```
版本：v1.0.0
更新日期：2026-02-05
```

---

## 三、更新记录（可选）

规范文档建议在末尾增加“更新记录”区块：
```
更新记录：
- 2026-02-05 v1.0.0 统一流程口径与质检闭环
```

---

## 四、更新规则

1. 每次修改规范文档时必须更新版本号与日期
2. 变更后需同步 `README.md` 与 `docs/index.md`
3. 若更新仅为表述修正，升级修订号
