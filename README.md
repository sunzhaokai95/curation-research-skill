# curation-research-skill

策展前期资料获取 Codex skill。

用于策展、展览、展厅、主题馆、企业馆、博物馆、文化馆、文旅馆的前期资料调研、主题资料收集、甲方文档解读和公开资料整理。

默认输出可用 XMind 打开的资料型思维导图 `.xmind`。当用户明确要求报告、Word、docx 或完整交付时,可基于同一批证据卡追加资料报告型 `.docx`。

## 使用

将本目录安装到项目根目录:

```text
.codex/skills/curation-research/
```

项目 `AGENTS.md` 中加入:

```text
当我要求做策展/展览/展厅的前期调研、资料调研、或把某主题整理成思维导图时,读取并严格遵循 .codex/skills/curation-research/SKILL.md 的流程,用其中的 scripts/ 脚本生成 .xmind。
```

完整流程见 `SKILL.md`。所有脚本均使用 Python 3 标准库,无需 pip 安装。
