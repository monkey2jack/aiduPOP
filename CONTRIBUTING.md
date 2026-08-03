# 贡献指南 / Contributing

感谢你对 aiduPOP 的兴趣！/ Thanks for your interest in aiduPOP!

---

## 中文

### 提 Issue

- **Bug**：请附上 Hermes Agent 版本、aiduPOP 版本（`plugin.yaml` 的 `version`）、飞书卡片报错码（如 300314）和可复现步骤。
- **功能建议**：说明使用场景，而不只是实现方式。

### 提 PR

1. Fork 本仓库，从 `main` 切出功能分支（`feat/xxx` 或 `fix/xxx`）。
2. 保持改动聚焦 —— 一个 PR 只做一件事。
3. 遵循现有代码风格：类型标注、`_logger` 日志、中文注释可接受。
4. 运行测试：`python -m pytest tests/ -q`。
5. 版本号只改 `plugin.yaml` 的 `version` 字段（唯一来源），并在 `CHANGELOG.md` 补一条。

### 脱敏要求

**严禁**在代码、注释、测试、截图中提交任何真实凭据或私人信息：

- App ID / App Secret / Token / API Key
- 真实 `open_id`（`ou_...`）、`chat_id`（`oc_...`）、租户域名
- 私人聊天内容、真实姓名、内部服务器路径

示例请用占位符：`ou_xxxxxxxx`、`YOUR_APP_SECRET`。提交前自查：

```bash
grep -rn --exclude-dir=.git -iE 'app_secret|sk-|ou_[a-z0-9]{8}|oc_[a-z0-9]{8}' .
```

### 上游关系

aiduPOP 基于 [hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming)。通用性修复请一并反馈上游；爱嘟专属定制留在本仓库并记入 `CUSTOMIZATIONS.md`。

---

## English

### Filing Issues

- **Bugs**: include Hermes Agent version, aiduPOP version (`version` in `plugin.yaml`), the Feishu card error code (e.g. 300314), and reproduction steps.
- **Feature requests**: describe the use case, not just the implementation.

### Pull Requests

1. Fork the repo and branch off `main` (`feat/xxx` or `fix/xxx`).
2. Keep changes focused — one concern per PR.
3. Match the existing style: type hints, `_logger` for logging.
4. Run the tests: `python -m pytest tests/ -q`.
5. Bump the version **only** in `plugin.yaml` (single source of truth) and add a `CHANGELOG.md` entry.

### Redaction Requirements

**Never** commit real credentials or private information in code, comments, tests, or screenshots:

- App ID / App Secret / Token / API Key
- Real `open_id` (`ou_...`), `chat_id` (`oc_...`), tenant domains
- Private chat content, real names, internal server paths

Use placeholders such as `ou_xxxxxxxx` / `YOUR_APP_SECRET`. Self-check before committing:

```bash
grep -rn --exclude-dir=.git -iE 'app_secret|sk-|ou_[a-z0-9]{8}|oc_[a-z0-9]{8}' .
```

### Relationship with Upstream

aiduPOP builds on [hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming). Please send generic fixes upstream as well; Aidu-specific customizations stay here and are documented in `CUSTOMIZATIONS.md`.

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
