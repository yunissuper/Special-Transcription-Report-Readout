# 案例：结直肠原发 + 肝原发肿瘤 两样本解读

这是一次真实交付的**脱敏归档**。原始项目把 `scripts/` 里的通用脚本按本项目的数据契约
落成了两个具体生成器，这里保留其**结构与文案逻辑**，隐去全部可识别信息。

> 脱敏处理：项目名/样本编号 → `sample_A` / `sample_B`；绝对路径 → `<PROJECT_ROOT>`；
> 同事原始数据路径、本地工具路径、PPTX 输出名全部替换。**无患者信息、无院内路径**。

## 文件

| 文件 | 作用 |
|------|------|
| `collect_results.py` | 把各阶段表格汇总成唯一 `report_data_current.json` |
| `build_leader_report.py` | 生成单文件自包含中文 HTML（本案例版，含具体文案） |
| `build_ppt_leader.py` | 生成 18 页结论优先 PPT |
| `validate_ppt.py` | 校验页数/图数/越界/禁用词/数字可追溯 |
| `plot_consensus_panels.py` | 每样本 3 张面板图（分区/主要类型/恶性证据），短图注在下方 |

## 与本仓库通用版的差异

通用版（`scripts/`）用 `--root` + `report_config.json` 驱动，可移植；
本案例版为交付方便，把样本名与文案**内联**在源码里。两者数据契约一致——
`report_data_current.json` 的字段名完全相同。要复用本案例的文案风格，
把这里的常量搬回 `templates/report_config.example.json` 即可。

## 本案例的两个关键教训（已写入主 SKILL.md）

1. **参考必须匹配疾病身份**：肝原发肿瘤用肝癌参考（HCC/ICC），
   误用结直肠参考会把正常肝上皮投影成 “CRC malignant”。
2. **图注短、放图下方**：最初把整句英文图注放图右侧，图被挤成窄条、
   PPT 里无法阅读；改为**短名 + 两列 + 图下方**后，地图占满面板。
