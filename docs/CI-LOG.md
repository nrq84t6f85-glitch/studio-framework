# CI 运行记录（失败史留档，先留证再清理）

> 原则：**失败不隐藏**——先把失败与根因写进本文件，再清理已被后续提交修复的红色运行，使 Actions 页反映当前真实状态。

## 一 · 失败运行（均已由后续提交修复）

| run id | 提交 | 现象 | 根因 | 修复提交 |
|---|---|---|---|---|
| 38242143319 | feat: studio-framework 0.1.0 | `dry-run` 报 `missing runtime registry .../teams/studio-local/runtime.json` | fixture 目录名为 `teams/demo`，与 runner 默认团队名不一致 | 2d576bd（目录改为 studio-local） |
| 38244082725 | feat: weighted gates + dispatch spec guard | `guard passes compliant dispatch` FAIL(2 gaps: C1-identity / C7) | ① identity 正则 `identity[=:]\S+` 不允许冒号后空格；② 正例缺少 read-back 措辞 | 1cfbe15 + fedbdad |
| 38244156349 | fix(guard): precise C6 phrasing | 同上（C1-identity 仍缺） | 同上（正则未修，只改了措辞与 C6） | fedbdad（正则容错） |

## 二 · 当前状态（2026-10-12 05:0x PDT 核对）

| 仓库 | 最新 run | 结论 |
|---|---|---|
| shangtou-studio (private) | 38244232668 | **success** |
| studio-framework (public) | 38244224973 | **success** |

## 三 · 教训（已固化）
- CI 抓出的都是**真问题**（fixture 路径、正则过严），不是环境噪音 → 保留双仓 CI 作为硬门禁；
- 本地自测通过 ≠ CI 通过（CI 在干净环境跑，路径/权限差异会暴露）→ **推送前必须审视 CI 输出**，不以本地绿为准；
- 失败提交不可"重跑"修复（同一 SHA 代码即错）→ 只能新提交修复，并在此留档。
