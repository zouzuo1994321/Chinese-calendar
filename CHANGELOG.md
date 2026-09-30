# 更新日志

本文件记录农历日历 (SiYue Calendar) 的全部版本迭代。格式：，Build 为「年月日 + 当日迭代序号」。

## 版本历史

### v1.9.12 (Build 2609300013) — 2026-09-30

- **「分数区 / 八字推演」之间的分隔虚线改到二者正中（用户截图 image#1：「调整虚线位置 放在 分数 和 八字推演 居中位置」）**：
  - **现象**：分数区与八字推演之间那条**绿色虚线**原本画在 `y - 3`（`_paint_zodiac` 里 `y=540` → 绘制行 **536..537**），**紧贴左侧「吉/平/凶」方框的底线（行 535..536）**，看上去像方框的底边被拉长，而不是一条独立的分隔线。
  - **修法**：`drawLine` 的 y 由 `y - 3` → **`y + 2`**（绘制行 **541..542**）。即以「分数区最低点」（吉/平/凶 方框底线 536）与「八字推演文字墨迹顶」（548）之间的空白带 **537..547（共 11 行）**为目标，居中到最靠近的 **542 行**——上线为整行 541..542，**上方留白 4 行 / 下方留白 5 行**，视觉对称。
  - **实测**：离屏渲染逐行量测（`probe_inspect_v112.py`）——虚线行 = **541..542**、方框底线 = **536**、八字推演墨迹顶 = **548**，上下空行差 = **1** ✓。
- **修 README 截图「整节重建」自愈（本轮排查中的根因修复）**：
  - **现象**：本轮 `verify_ui` 跑出 `[10] README 四张截图已 base64 内嵌` **红**——根 `README.md` 从 1.33MB 缩回 27KB，「真实截图」表格里的 `![绿日](data:...)` 被**外部（编辑器/格式化）改回纯占位文字** `| 绿日 |`，四张图丢失（`dist/README.md` 备份仍完整）。
  - **根因**：旧 `_embed_shots_to_readme()` 只做 `![alt](url)` 的**定点替换**——一旦锚点被抹掉就 `n == 0` 静默跳过，**永远无法恢复**（此前每轮能过，只因锚点恰好还在）。
  - **修法**：改为用正则定位「`## 📸 真实截图` … 至下一个 `---`」**整块并重写**，无论此前被改成什么样都能自愈；仅在整节定位失败时退回定点替换。
  - **实测**：重跑 `verify_ui` → `[10]` 转 **PASS**（`data URI=4  alt齐=True`），README 恢复 1.33MB ✓。
- **验证**：`verify_ui.py` **136/136 → 137/137**（新增 `[20]` 组 1 条虚线居中断言；版本号断言随 v1.9.12 更新）✓ · `probe_inspect_v112.py`（新增）**4/4** ✓ · `probe_inspect_v111.py` **6/6** ✓ · `probe_inspect_v110.py` **10/10** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `font_weight_probe.py` **5/5**（真实平台）✓ · `pyflakes` 零输出 ✓。
- **改动文件**：`ui/page.py`（`_paint_zodiac` 虚线 y）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`（`_embed_shots_to_readme` 整节重建 + `[20]` 断言）、`tools/dev_checks/probe_inspect_v112.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.11 (Build 2609300012) — 2026-09-30

- **修「宜 / 忌 跨行居中错位」（用户截图 image#1：居中 跨行 因为最后一个、导致第二行与第一行错位）**：
  - **现象**：v1.9.10 把宜/忌内容改为水平居中（`Qt.AlignHCenter`）后，一旦列表**折成两行以上**，**行尾带「、」的那一行其墨迹会整体左移约半个顿号**，与相邻行看起来「错位」。14px DemiBold 下实测左偏约 **7.0px**。
  - **根因**：`_wrap_px` 按「标点不落行首」把顿号**粘在前一个条目之后**（`unit = part + "、"`）。于是当断行点落在某个完整条目之后时，**该行的行尾会残留一个全角「、」**；而 `Qt.AlignHCenter` 是**按整行字宽**（含这个行尾顿号）居中——顿号只占右侧近半个字的空白，居中后**可见文字整体被挤向左**，与不带顿号的相邻行错位。行末的顿号本身在换行处也是多余的（列表在下一行继续）。
  - **修法**：`_wrap_px` 断行完成后，**统一抹去每行的行尾顿号**（`lines = [ln[:-1] if ln.endswith("、") else ln for ln in lines]`），每行随即按**自身可见文字宽度**精确居中。断行决策仍在抹除之前完成，故**行数、断点位置不变**。
  - **备选方案（未采用）**：折行时保留行尾顿号、仅**排除其宽度**做「悬挂标点」（optical centering）。该法不丢字符，但会在居中行的右缘留下一个悬空的顿号，观感上易被误读为排版错误；抹除法改动最小、输出最干净，故选抹除。
  - **实测**：离屏渲染整页，扫描 **2026 全年 40 个确有跨行的日期**，逐行取宜/忌文字区（y 422..476）墨迹 bbox 并比较各行墨迹中点横坐标——**最差极差 1.00px**（像素取整所致，旧行为左偏 7.0px）。断行结果示例：`['会亲友', '出行、安床', '祭祀、祈福', '安葬']`（**无任何行以「、」结尾**）。
- **软件 logo 全量更新（用户截图 image#2：logo-2.png）**：
  - **新图标**：朱红底 + 鎏金云纹 + 金色「历」字（1024×1024）。
  - **落地**：`logo-2.png` → **覆盖 `logo.png`**（窗口图标 / 系统托盘 / 对话框 / exe 资源均引用该名，无需改代码）；按新图**重生成 `logo.ico`**（Pillow，多尺寸 16 / 24 / 32 / 48 / 64 / 128 / **256**²）。旧图标归档至 `history/logo_prev_1.9.10/`。
- **验证**：`verify_ui.py` **130/130 → 136/136**（新增 `[19]` 组 5 条：抹除行尾顿号 / 断行无行尾顿号 / 旧行为左偏量化 / logo.png 已换新 / logo.ico 多尺寸；另在版本组新增 1 条 logo 素材断言；版本号断言随 v1.9.11 更新）✓ · `probe_inspect_v111.py`（新增）**6/6** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `probe_inspect_v110.py` **10/10** ✓ · `font_weight_probe.py` **5/5**（真实平台）✓。
- **改动文件**：`ui/page.py`（`_wrap_px` 抹除行尾顿号 + 注释）、`calendar_app/version.py`、`logo.png` / `logo.ico`（更新）、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/probe_inspect_v111.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.10 (Build 2609300011) — 2026-09-30

- **底部四按钮距外框改 5px、提示行与行事历面板同步下移（用户截图 image#1）**：
  - **现象**：外框下沿 3px 线（`FRAME_OUT_BOTTOM=789`，实测占 y **787..790**）与底部四按钮（关于本软件 / 本月行事历 / 本日行事历 / 导入行事历）之间只剩 **2px** 空白，视觉上几乎贴着框线。
  - **修法**：`TAB_Y` **793 → 796**（`FRAME_OUT_BOTTOM + 7`）→ 按钮上沿线 796，与框线空白行 791..795 = **5px** ✓；页高 `PAGE_H` **838 → 841** 随之 +3，使「（双击按钮 打开/关闭 对应面板）」提示行（824..836）与下方 **本月 / 本日行事历面板同步下移 3px**，页底留白仍为 5px。
  - **实测**：离屏渲染逐行统计 —— 外框线 787..790、按钮上沿 796（空白 791..795，**5px**）。
- **八字推演行加粗（用户截图 image#2）**：`_paint_zodiac` 的推演行字体 `_font(12, ZH_SONG)` → **`_font(12, ZH_SONG, QFont.Bold)`**。内置 Noto Serif SC 带真实 Bold 面（真机字重实测 Normal 497 / **Bold 614** / Black 692 像素），故直接 `QFont.Bold` 即真实加粗——**不可用 `setItalic`**（会吞掉字重轴，见 `theme._font`）。
- **文案英文汉译（用户截图 image#3）**：生肖路径 `analyze_zodiac_day` 的相刑提示 `"与日支相刑， friction 易起…"` → **`"与日支相刑，摩擦易起，忍让为先，不宜争执硬顶"`**。另经 AST 全量扫描（`engine.py / page.py / ui_main.py / dialogs.py / theme.py / agenda.py / agenda_pdf.py`）确认：**全部用户可见文案中已无英文残留**（仅保留有意为之的品牌名 Copyright / 肆月Aperture、Build 版本标签与 Excel / CSV / PDF / Word 文件格式词）；12 生肖全部提示语实测含英文字符数 = **0**。
- **宜 / 忌 内容水平居中（用户截图 image#4）**：`_draw_para`（**仅** 供宜/忌两处调用）对齐由 `Qt.AlignLeft` → **`Qt.AlignHCenter`**，宜/忌列表按框宽居中排布。
- **验证**：`verify_ui.py` **127/127 → 130/130**（新增 `[18]` 组 3 条：八字推演加粗 / 宜忌居中 / 文案无英文；`[16]` 组 2 条改写为「按钮距外框 5px」「页高 841」；`[4]`/版本断言随页高与版本号更新）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `font_weight_probe.py` **5/5**（真实平台）✓ · `pyflakes` 零输出 ✓ · `probe_inspect_v110.py`（新增，合并 gap/居中/八字加粗三项实测）**10/10**：外框线 787..790、按钮上沿 796、空白 **5px**、宜/忌墨迹中点偏差 ≤8px、八字推演 Bold 存在 ✓。
- **改动文件**：`ui/page.py`（`PAGE_H` 841 / `TAB_Y` 796 / `_paint_zodiac` 加粗 / `_draw_para` 居中）、`calendar_app/engine.py`（相刑文案汉译）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/probe_inspect_v110.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.9 (Build 2609300010) — 2026-09-30

- **版权行与边框 5px、互不重叠（用户截图 image#1）**：
  - **现象**：版权行文字下缘**正压在内框线（776）上**，二者视觉重叠。
  - **修法**：外框/内框下沿改为**绝对坐标**（不再由 `PAGE_H` 推导）——外框 `FRAME_OUT_BOTTOM=789`、内框 `FRAME_IN_BOTTOM=783`；版权行框 762..778，到内框恰好 **5px**。实测版权行墨迹 767..777、内框线 782，间隔 **5px** ✓。改为绝对坐标后，缩短页高也不会把外框带着一起上移。
- **删除框外条那条浅灰横带（用户截图 image#2「红框部分好像有一个灰色的框，删除」）**：
  - **根因**：`_paint_stack`（底部「叠页」装饰）在 `y 802..820` 画了 4 条自内向外收窄的矩形，填充 `#eeebe0`（RGB 238,235,224）/`#f3f0e6`，满宽压在框外条区域——**颜色与截图实测横带完全一致**，确认即此装饰。
  - **修法**：删除 `_paint_stack` 及其调用（连带 `PAPER_EDGE` 在 `page.py` 的导入）。实测框外条区域 `#eeebe0` 最大同色行长 **0px**。
- **提示行下方留白过大（用户截图 image#3）**：
  - **现象**：页面固定 520×848，而外框下沿 789、TAB 行 793..819、提示行 821..833 —— 提示行以下还空 22px 纸面，再加布局间距 4px + 面板内缩 2px，**提示行到行事历面板约 28px 空白**。
  - **修法**：页高 `PAGE_H` **848 → 838**；TAB 行随外框下移到 `TAB_Y=793`，提示行 821..833，页底留白 **22px → 5px**（提示行到面板约 11px）。
- **八字运势得分重标定（用户提问：94年3月21日13时录入后分数普遍偏高，是计算问题还是本就这样）**：
  - **诊断结论：是计算问题（公式标定偏移），不是排盘错误、也不是命盘特性。** 原式 `score = clamp(fortune_score*0.5 + 50 + adj, 5, 98)` 的 **+50 固定偏移**使 `adj=0` 时得分已 ≈80（当日基础分中位 60）；2026 全年 365 天实测**中位 83、均值 82.3、64% 的天数 ≥80**。换 8 个不同出生日期（1963~2001）中位依旧 **82~83**，与八字无关——即「人人都是 80+」。
  - **四柱经核验正确**：1994-03-21 13:00（公历）→ **甲戌 · 丁卯 · 丙午 · 乙未**（1994 甲戌年 ✓、卯月丁卯 ✓（甲己之年丙作首）、未时乙未 ✓（丙辛日起戊子））。
  - **修法（本轮选定「中度强化」）**：`score = clamp(fortune_score*0.6 + 30 + adj, 5, 98)` → 中位 **69**、均值 68.3、范围 34..97（旧值中位 83、≥80 占 64%）；仍保留八字比生肖路径（`fortune_score + adj`，中位 64）更亮眼的「强化」定位，但不再人人 80+。
- **验证**：`verify_ui.py` **123/123 → 127/127**（新增 `[17]` 组 2 条八字标定断言；`[16]` 组 5 条重写；`[4]`/`[12]` 随页高/边框收敛）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `font_weight_probe.py` **5/5**（真实平台）✓ · `pyflakes` 零输出 ✓ · `probe_inspect_v199.py` 真机实测：页 520×838、版权行墨迹 767..777、内框线 782（间隔 5px）、框外条 `#eeebe0` 同色行长 0px、页底留白 5px ✓。
- **改动文件**：`ui/page.py`（`PAGE_H` + 新增 `FRAME_OUT_BOTTOM`/`FRAME_IN_BOTTOM` / `_paint_border` 绝对下沿 / `TAB_Y` / 删 `_paint_stack`）、`calendar_app/engine.py`（`bazi_day_report` 得分重标定）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/probe_inspect_v199.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.8 (Build 2609300009) — 2026-09-30

- **根修生肖下拉「整列仍显示…」（用户截图 image#3：生肖字体显示还是没有修复）**：
  - **现象**：顶栏选中生肖（如「戌狗」）已能正常显示，但**点开下拉列表后，12 项两字生肖被裁成「…」**——看起来仍像「没修好」。v1.9.7 的显式 `setFont` 只治好了「选中显示」，漏掉了**弹层自身的宽度**。
  - **真正根因**：`QComboBox` 的弹出视图默认**继承 combo 的宽度（仅 46px）**；扣除 10px 滚轴 + 左右 padding 后仅剩 ~20px，而两字生肖（12px 黑体）实测需 ~24px → 逐项 elide 成「…」。源码/离屏环境因弹层可自由撑开而未暴露（真实平台探针 `elide('子鼠', 46-26)='…'` 复现、`setMinimumWidth(96)` 即修复）。
  - **修法**：`_apply_zodiac_fonts()` 内对 `view()` 计算**全部 12 项最大字宽**，`view().setMinimumWidth(最宽 + 44)`（实测 68px），确保两字生肖完整显示。
- **八卦水印透明度 40% → 20%（用户截图 image#2：八卦透明度改到20%）**：宜/忌中缝八卦水印 `setOpacity(0.40)` → **`0.20`**，更淡、不抢五行神位文字；v1.9.7 的「加大(110) + 竖向居中」沿用。
- **版权行与外框底 5px + 框外条同步上移（用户截图 image#1：版权信息 和 边框 上移，与 出行/财务 距离 5px）**：
  - **更正 v1.9.7 的错解**：v1.9.7 将版权行下移到 781（贴外框下沿）**方向反了**——用户要的是版权行**回到**「出行/财务 建议卡底线(760) 下 5px」，即 `COPYRIGHT_Y` **781 → 762**（墨迹顶 ≈767）。
  - **外框上移**：`_paint_border` 外框下沿 `PAGE_H-100`(802) → **`PAGE_H-80`(782)**、内框 796 → **776**、角点 802 → **782**，由「外框上移」而非「版权行下移」达成底部紧凑。
  - **框外条同步**：TAB 按钮 `TAB_Y` **804 → 786**（贴住新外框下沿 782），提示行随 `TAB_Y` 联动。
- **验证**：`verify_ui.py` **121/121 → 123/123**（`[15]` 新增弹层撑宽 1 条 / `[16]` 版权+外框+框外条 3 条重写 / `[14]` 八卦 20% / `[4]` 角点 PAGE_H-66 / `[12]` 底部 786-26）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `font_weight_probe.py` **5/5** ✓ · `probe_inspect_v198.py` 真机实测：生肖框选中「午马」深墨 78px、占位「生肖」44px、**弹层宽 68px 且 elide('子鼠', 68-26)='子鼠'**（核心修复）、中缝八卦 tint=211(20%) 仍可见、神位墨迹中心 260.5（缝中心 261）、版权墨迹顶 767..775、外框下沿 782、TAB_Y=786 ✓。
- **改动文件**：`ui/page.py`（`_apply_zodiac_fonts` 弹层撑宽 / `_paint_yiji` 八卦 20% / `_paint_border` 外框上移 / `COPYRIGHT_Y` + `TAB_Y`）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/probe_inspect_v198.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.7 (Build 2609300008) — 2026-09-30

- **根修生肖字体「彻底不显示」+ 与八字字号不一致（用户截图 image#1/#2）**：
  - **现象**：生肖下拉选中 / 整列**完全不显示字形**；且生肖字号(15px)与紧邻「八字」按钮(12px)不一致。
  - **真正根因（推翻 v1.9.6 的诊断）**：`fontTools` 核验——随包 5 份内置字体子集（Noto Sans/Serif SC 各字重）**均含全部生肖字形**（7554 字形，GB2312 全集），故「黑体子集缺字形」**不成立**。真实变量是 **Qt 对 QSS `font-family` 多词族名的归一化**：QSS 里 `'Noto Sans SC'` 被归一为 `NotoSansSC`，**匹配不到已注册的『Noto Sans SC』**，真机回退链也命不中 → 字形整列不显示（源码/离屏环境恰有系统兜底，故旧探针全绿掩盖了它）。
  - **修法**：**不再用 QSS 声明字体**，改由 `_apply_zodiac_fonts()` 对 **combo / 行编辑 / 下拉视图三处显式 `setFont`**（`setFamilies(sans 优先)` + `setPixelSize(12)`）——与全页自绘文字同一条 `setFamilies` 路径（内置黑体优先、系统字体兜底），彻底绕开 QSS 族名解析。字号 15px → **12px**，与「八字」按钮同级。
- **加大八卦区域 + 神位方向字体加大加粗（用户截图 image#3）**：
  - 宜/忌中缝八卦水印 `wm_h` **88 → 110**，并由底部对齐改**竖向居中**，八卦区域更醒目；仍 40% 透明度绘于文字之下。
  - 五行神位文字（喜神/财神/福神/冲煞/禄）**11px → 13px Bold**（`row_h` 17 → 18），方向信息更醒目，仍水平居中于中缝。
- **版权行与外框下沿 5px + 框外条同步上移（用户截图 image#4）**：
  - 版权行 `COPYRIGHT_Y` **762 → 781**：v1.9.6 误移到「建议卡下 5px」，现改为**外框下沿(802) 上 5px**（墨迹顶 ≈786）。
  - 框外条（本月/本日行事历 TAB 按钮 + 提示行，位于外框之下）`TAB_Y` **808 → 804**，贴住外框下沿，与版权行形成对称紧凑的底部布局。
- **验证**：`verify_ui.py` **118/118 → 121/121**（`[15]` 生肖渲染根修 4 条重写 / `[16]` 版权+框外条 2 条重写 / `[14]` 八卦加大 / `[6]` 神位 13px Bold / `[12]` 底部 tab 804）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `pyflakes` 零输出 ✓ · `probe_inspect_v197.py` 渲染实测：生肖框选中「午马」**深墨 65px**、占位「生肖」**23px**（字形真的渲染）、combo/lineEdit/view 字号 12/12/12 + 内置黑体、神位墨迹中心 260（缝中心 261）、中缝八卦 tint=199、底部水印 tint=737、版权墨迹顶 786（外框下沿-16）✓。
- **改动文件**：`ui/page.py`（`_apply_zodiac_fonts` 新增 / `_theme_controls` 生肖 QSS 去字体 + setFont / `_paint_yiji` 八卦加大 + 神位 13px Bold / `COPYRIGHT_Y` + `TAB_Y`）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/probe_inspect_v197.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.6 (Build 2609300007) — 2026-09-30

> ⚠ **根因更正（v1.9.7）**：本节下方「内置黑体子集缺生肖字形 → 整列 --」的判断**已被推翻**——经 `fontTools` 核验，内置字体子集**均含全部生肖字形**；真正原因是 QSS 多词族名归一化（详见 v1.9.7 条目）。v1.9.6 改用宋体族只是巧合过了源码环境，真机仍不显示。

- **根修生肖下拉「整列显示 --」（用户截图 image#1）**：
  - **现象**：点开生肖下拉，12 个两字生肖（子鼠…亥猪）整列渲染成「--」，无一可读。
  - **当时判断（已更正，见上）**：`_theme_controls` 里 `QComboBox` / `QComboBox QAbstractItemView` 的 `font-family` 用的是 `calendar_app_fonts.sans_css()`——曾以为内置 **Noto Sans SC 子集缺生肖字形** → 落 `.notdef`。
  - **当时修法**：`fonts.py` 新增 `serif_css()`；QComboBox / 下拉视图 / 内嵌行编辑**三处全部改宋体族**（v1.9.7 已改为显式 `setFont`）。
- **选中生肖加大并居中（用户截图 image#2）**：Qt 的 QComboBox 非可编辑态显示文字无法用 QSS 对齐，改用 Qt 惯用法——**可编辑 + 只读 + 行编辑 `AlignCenter`**（`NoFocus` 防文本光标、`NoInsert` 防输入污染、`setTextMargins(0)`）；选中显示 12px → **15px** 居中，下拉列表 14px（item `min-height` 22 → 24px）。
- **宜 / 忌中缝版式（用户红框 image#3/#4 + 八卦素材 image#5）**：
  - 五行神位信息（喜神 / 财神 / 福神 / 冲煞 / 禄）**水平居中**（原 AlignLeft，实测墨迹中心 218 → 259.5，缝中心 261）；
  - 中缝叠加 **40% 透明度八卦水印**（`八卦.png`，底部对齐、绘于文字之下）——恢复 v1.8.x「中栏底部八卦底纹」特性（该特性在 v1.9.3/1.9.5 版式回退中丢失）。
- **生肖剪影水印回底部区块（用户 image#6 指认区域）**：撤销 v1.9.5 的「中缝居中」，恢复 v1.9.4 版式——**×0.9（高 189px）、水平居中（中线 260）、垂直居中压在 吉时/颜色+建议 卡片区块（574..760）上，20% 透明度**，绘于页脚前（版权行不受影响）。
- **版权行与卡片框体间隔 5px（用户红框 image#7）**：版权行由 `PAGE_H-70`（与建议卡底线间隔 23px，底部最后一个非 5px 间隔）上移到 **`COPYRIGHT_Y=762`**——建议卡底线(760) 下 5px 视觉间隔，与 R1~R4 的 5px 系列对齐。
- **验证**：`verify_ui.py` **118/118**（新增 `[14]` 八卦水印 / `[15]` 下拉字体+居中 3 条 / `[16]` 版权间隔）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `pyflakes` 零输出 ✓ · `probe_inspect_v196.py` 渲染实测：神位墨迹中心 259.5（缝中心 261）、中缝八卦灰墨可见、底部水印 tint=737、版权墨迹顶 767（卡片底线+5px 口径）、选中「午马」15px 居中 + data 单字联动不破 ✓。
- **改动文件**：`ui/page.py`（`_build_controls` 行编辑居中 / `_theme_controls` QSS 宋体+加大 / `_paint_yiji` 居中+八卦水印 / `_paint_zodiac_watermark` 底部区块 / `_paint_footer`+`COPYRIGHT_Y`）、`calendar_app/fonts.py`（`serif_css()`）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/probe_inspect_v196.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.5 (Build 2609300006) — 2026-09-30

- **根修 v1.9.3 / v1.9.4 八字「录入后不保存 + 生肖不同步」（用户反馈 v1.9.4 什么问题都没解决）**：
  - **现象**：真机录入八字点保存后信息不保存、生肖下拉也不联动更新。
  - **真正根因**：`ui_main._open_bazi` 里 `dlg.exec() == dlg.Accepted` —— PySide6 6.11 的 `Accepted` 枚举**只存在于类上**，在对话框**实例**上访问 `dlg.Accepted` 直接抛 `AttributeError`；异常被 Qt 槽静默吞掉，**保存 / 生肖联动 / 配置落盘一行都没执行**。此前 v1.9.4 定位的「只读目录配置失败」只是并发因素而非主因；离屏探针全部通过是因为它们直接调用方法，从未走到 `dlg.exec()` 这一行（离屏照不到的真机坑）。
  - **修法**：改为类级比较 `dlg.exec() == QDialog.DialogCode.Accepted`。
  - **验证**：`probe_bazi_full.py` 全链路探针（去掉 `try/except` 兜底）实测：修复前抛 `AttributeError`，修复后完整走通 保存 → `_sync_zodiac_from_bazi` 联动 → `_save_settings` 落盘 → 重启回显。
- **生肖统一两字显示**（用户点名：子鼠、丑牛、寅虎、卯兔、辰龙、巳蛇、午马、未羊、申猴、酉鸡、戌狗、亥猪）：
  - `engine.py` 新增 `SHENGXIAO_2CHAR`（两字表）与 `ANIMAL_TO_2CHAR`（单字 → 两字映射）；
  - 生肖下拉框**显示两字**、`data` 仍存单字（`findData(单字生肖)` 的八字联动零影响）；
  - 年生肖「乙巳年 · 巳蛇」、日生肖「庚辰日 · 属辰龙」、本日生肖 / 本日运势「午马」「巳蛇」、八字对话框预览「生肖：巳蛇」**全部转两字**。
- **宜 / 忌区域回退 v1.9.3 版式**（用户截图对比需求「这块区域回退到上一版本」）：
  - 撤销 v1.9.4 的满宽 224：宜 / 忌恢复**窄 150 双栏**（x=30 / x=340，高 95），喜神 / 财神 / 福神 / 冲煞 / 岁煞五行神位信息**回中缝竖排 5 行**；生肖剪影水印回退到**中缝居中**（×0.9 缩放保持）。
  - 窄栏 140px 文字宽下三年逐日最多 3 行（2026-01-06 宜共 23 字），文字区扩到 54px 高 + `_draw_para` 上限 3 行、末行 elide 兜底不裁切。
- **四处间隔统一 5px**（用户红框标注 R1/R2/R3/R4「间隔都改为5px」）：
  - **R1** 宜 / 忌框 ↔ 本日运势行：框高 82 → 95（384..479 ↔ 484）→ **5px**；
  - **R2** 左右栏列间距：吉时 / 颜色框 224+12 → **227 / 228 + 5px**（30..257 / 262..490），建议卡同步 227+5；
  - **R3** 时辰行 ↔ 事业行：建议卡 y 652 → 647（642 底 ↔ 647 顶）→ **5px**；
  - **R4** 事业行 ↔ 出行 / 财务行：行间距 +4 → +5（701 底 ↔ 706 顶）→ **5px**。
- **验证**：`verify_ui.py` **113/113**（新增 `[13b]` 组 3 条两字生肖断言；`[6][7][12][14]` 断言随版式回退重写）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `geom_probe.py` 通过 ✓ · `pyflakes` 零输出 ✓ · `probe_render_v195.py` 渲染实测 R1/R2/R3/R4 **全 5px** + 两字生肖 + 八字联动「巳蛇」✓。
- **改动文件**：`ui/page.py`（`_paint_yiji` 回退窄栏 + 中缝神位 / `_paint_hours_colors` / `_advice_rects` / `_paint_advice` 5px / `_paint_zodiac_watermark` 中缝居中 / 两字生肖）、`ui/dialogs.py`（预览两字）、`ui_main.py`（`dlg.Accepted` 根修）、`calendar_app/engine.py`（两字表）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/probe_render_v195.py`（新增）、`README.md`、`CHANGELOG.md`。

### v1.9.4 (Build 2609300005) — 2026-09-30

- **根修 v1.9.3 八字等配置「无法保存」（真机实测失效）**：
  - **现象**：v1.9.3 录入八字保存后无反应，生肖不联动、本日运势标签也不切换；代码逻辑（BaziDialog 保存 → `_sync_zodiac_from_bazi` 回显 → `_paint_fortune` 标签决策）经数据层核验本应正确。
  - **真正根因**：frozen 单文件 exe 的 `SETTINGS_PATH` 指向 **exe 同目录**；当用户把 exe 放在 `Program Files`、网络盘等**只读目录**时，`_save_settings` 写 `settings.json` **静默失败**（异常被吞），导致八字/生肖/本日运势三项全部「不生效」——并非逻辑 bug，而是配置落盘失败。
  - **修法**：新增 `settings_path()` —— frozen 下 exe 目录只读或尚未生成且不可写时，**回退到 `%APPDATA%/农历日历/settings.json`**（可读写）；`_save_settings` 写前 `os.makedirs(d, exist_ok=True)` 保证目录存在；`_apply_zodiac` 整体包 `try/except` 兜底，任一异常都 `set_zodiac_report(None)` 复位，避免整页绘制崩溃。
- **宜 / 忌 满宽化 224（用户截图红/蓝框对齐需求）**：
  - **需求**：截图标注「蓝框（宜/忌栏）统一成红框宽度」，红框即吉凶时辰/建议的 **224 满宽栏**。
  - **取舍**：页面存在两组列宽体系（窄栏 150 / 满宽 224），224×3 放不下，故采纳 **「宜忌满宽化 224」** 方案——宜/忌两栏由 150 改为 **满宽 224 双栏**（与吉凶时辰、建议卡完全对齐），中栏三栏（y=322）保持 150 不变。
  - **连带调整**：宜/忌框中间原 160px 中缝放着的 **喜神/财神/福神/冲煞/禄** 挪到宜/忌框**下方独立一行**（满宽 5 槽等分，每槽 92px，超长项 `elide` 兜底绝不溢出）。
- **生肖水印底图缩到 90%**（用户需求「把生肖的底图缩小到 90%」）：`_paint_zodiac_watermark` 高度基准 `210 → 189`（`× 0.9`），水平居中不变。
- **验证**：`verify_ui.py` **110/110**（新增 `[14]` 组 2 条：水印 90% / frozen 配置回退 APPDATA；`[6]` 神位信息行改测 elide 后宽度）✓ · `ui_agenda_probe.py` **43/43**（修正其测试钩子对 `theme.SETTINGS_PATH` 的 patch，因 `settings_path()` 改读 theme 全局）✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `font_weight_probe.py` **5/5** ✓ · `geom_probe.py` 通过 ✓。
- **改动文件**：`ui/page.py`（`_paint_yiji` 满宽 224 双栏 + 神位信息行下移 / `_paint_zodiac_watermark` 缩 90%）、`ui/theme.py`（`settings_path()`）、`ui_main.py`（`_save_settings` 写前建目录 / `_apply_zodiac` 兜底）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/ui_agenda_probe.py`、`README.md`、`CHANGELOG.md`。

### v1.9.3 (Build 2609300004) — 2026-09-30

- **根修悬停下拉闪烁**（用户 v1.9.2 截图反馈：仍在闪）：
  - **真正的根因**：v1.9.2 的收起判定 `self.zodiac_box.geometry().contains(QCursor.pos())` 拿的是**父坐标系**几何，而 `QCursor.pos()` 是**全局屏幕坐标** —— 页面居中于窗口内，两个坐标系原点不同，`contains` **恒为 False**。于是 popup 打开瞬间的伪 Leave 依旧被误判为「光标已离开」→ `hidePopup()` → 开关循环，闪烁只是减轻并未根除。
  - **修法**：用 `mapToGlobal(QPoint(0,0))` 把 combo 矩形映射到全局坐标系再与光标比较（`combo_rect = QRect(mapToGlobal(0,0), size())`），收起判定统一为全局坐标 —— 光标仍在 combo 上（伪 Leave）或仍在弹层上时都不收起。
  - **附修**：新增 `activated` 守卫 —— 鼠标选完生肖后 600ms 内不自动重弹（否则弹层关闭后因悬停立即再次弹出）。
- **生肖框与八字框等宽**（用户反馈「生肖列宽和八字列宽保持一致」）：生肖框 `44 → 46`px 与八字框一致，顶栏顺延 2px（前/后一日/撕页/今日右移，透明度滑块与窗控锚点不变）。
- **新增 八字↔生肖联动**（用户需求「输入八字后应该与生肖联动，自动识别生肖」）：
  - 录入八字保存后，由八字**年支生肖**自动选中页顶下拉框（`_sync_zodiac_from_bazi`：`findData(shengxiao)` → `setCurrentIndex`）；启动时已存八字同样回显到下拉框。行为探针实测：八字 1992-08-15 → 年支生肖**猴** → 下拉框自动选中「猴」→ 当日报告 name=猴。
- **「本日生肖」细化为「本日运势」**（用户需求）：已录入八字（当日报告带 `bazi_text`）时，分数旁标签由「本日生肖」换为「**本日运势**」（八字推演口径；未录八字仍显示「本日生肖」）。
- **验证**：`verify_ui.py` **106/106 → 110/110**（新增 `[13]` 组 4 条：mapToGlobal 根修 / activated 守卫 / 八字联动 / 本日运势标签）✓ · 联动行为探针 OK ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `font_weight_probe.py` **5/5** ✓ · `geom_probe.py` 通过 ✓。
- **改动文件**：`ui/page.py`（`eventFilter` mapToGlobal / `_open_zodiac_popup` 守卫 / `_zx_on_activated` / 顶栏几何 / `_paint_fortune` 标签）、`ui_main.py`（`_sync_zodiac_from_bazi` / `_open_bazi` / 启动回显）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`README.md`、`CHANGELOG.md`。

### v1.9.2 (Build 2609300003) — 2026-09-30

- **修复悬停下拉闪烁**（用户 v1.9.1 两张截图反馈）：鼠标悬停弹出生肖下拉后界面持续闪烁。
  - **现象**：悬停 150ms 弹出下拉的瞬间，下拉层反复开关、整段顶栏闪烁不停。
  - **根因**：`showPopup()` 打开瞬间 Qt 会给 combo 发一次**伪 Leave**，此时光标仍在 combo 自身几何内（并不在弹层窗口内）。旧 `Leave` 判定只排除「弹层窗口几何」，于是伪 Leave 被误判为「鼠标离开」→ 触发 `hidePopup()` → 弹出被关 → 重新悬停又弹，形成**开关循环 = 闪烁**。
  - **修法**：`eventFilter` 的 `Leave` 分支收起判定改为「光标**既不在 combo 自身几何、也不在弹层窗口几何**内才 `hidePopup()`」——把光标仍在 combo 上的情形（伪 Leave）一并排除（`self.zodiac_box.geometry().contains(gp) or view.window().frameGeometry().contains(gp)`），并将 `QCursor.pos()` 提出为局部变量 `gp` 复用。
- **修复生肖框右侧留白过多**（用户图 2 反馈）：未选生肖时「生肖」两字旁有大段空白。
  - **修法**：生肖框宽度 `64 → 44`px（仅贴住「生肖」两字），顶栏重排：八字 `x+=50`、生肖 `x+=47`、前/后一日 `x+=29/30`、撕页 `x+=43`、今日止于 348；透明度滑块顺势右移补位 `360..434`（`setGeometry(360, y, 74, h)`），窗控按钮锚点不动。
- **验证**：`verify_ui.py` **105/105 → 106/106**（新增「生肖框宽度 44」「闪烁修复：combo 自身几何排除」2 条断言）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `font_weight_probe.py` **5/5** ✓ · `geom_probe.py` 通过 ✓。
- **改动文件**：`ui/page.py`（`eventFilter` 伪 Leave 排除 + `_build_controls` 顶栏几何）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`README.md`、`CHANGELOG.md`。

### v1.9.1 (Build 2609300002) — 2026-09-30

- **修复生肖框与下拉弹层 UI**（用户 v1.9.0 两张截图反馈）：
  - **① 未选时显示「生肖」两字**：v1.9.0 的「生肖 ⋯」占位项被用户否定 —— 改为 Qt6 **占位文本**方案：删除占位列表项，`setPlaceholderText("生肖")` + `setCurrentIndex(-1)`，**下拉列表仅含 12 生肖**（不再有「生肖……」占位行）；`currentData()` 未选时仍为 `None`，选人逻辑零改动。
  - **② 红色箭头块移除**：v1.9.0 用 QSS 边框画的 `::down-arrow` 三角在真机上渲染成红色色块。现彻底隐藏（`::drop-down` 宽 0 + `::down-arrow` 尺寸 0），交互改由**悬停弹出**承担。
  - **③ 悬停即弹出下拉**：`zodiac_box` 挂 `eventFilter` —— `Enter` 启动 **150ms 停留计时**（防扫过顶栏误弹）后 `showPopup()`；`Leave` 停表，若弹层可见且**鼠标不在弹层窗口内**（允许 combo→弹层间隙）则 `hidePopup()`。
  - **④ 弹层滚轴随红绿主题**：`QAbstractItemView::item` 行高 22px + 内边距；`QScrollBar:vertical` 窄滚轴（宽 10px、圆角、淡底）、**把手取主题 `main` 色**（hover 加深为 `dark`）、上下按钮隐藏、页槽淡墨；选中行仍为主题 `main` 底 + 白字。
- **验证**：占位文本渲染探针（未选 72 墨迹 px / 选中 44 px / 复位恢复）通过；`verify_ui.py` **101/101 → 105/105**（新增占位文本、悬停弹出、离开收起、滚轴主题化、箭头移除 5 条断言）✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `font_weight_probe.py` **5/5** ✓ · `geom_probe.py` 通过 ✓。
- **改动文件**：`ui/page.py`（占位文本 / `eventFilter` / `_open_zodiac_popup` / `_zx_hover_timer` / `_theme_controls` 弹层 QSS）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`README.md`、`CHANGELOG.md`。

### v1.9.0 (Build 2609300001) — 2026-09-30

- **修复建议卡（事业 / 感情 / 出行 / 财务）显示不全**（用户图 1 反馈）：卡内文字折行后仍会被截断，鼠标**悬停停留**后弹出完整建议。
  - **现象**：四张建议卡片正文较长时，第二行 `elidedText` 省略号截断，用户看不到完整内容。
  - **根因**：卡片是 `CalendarPage` 自绘控件上的静态绘制，没有「查看全文」的交互入口。
  - **修法**：新增 `_advice_rects()`（与 `_paint_advice` 完全一致的几何），在 `mouseMoveEvent` 中命中卡片并启动 **350ms 停留计时器**（`_dwell_timer`），停留后才调用 `QToolTip.showText()` 把 `info["advice"][key]` 完整内容锚定到卡片下方显示；移出卡片或离开窗口立即收起并复位状态；悬停时给手型光标提示可交互。
  - ⚠ PySide6 无 `QToolTip.setStyleSheet`：tooltip 配色只能靠**应用级样式表**着色，故在 `_theme_controls()` 里 `QApplication.instance().setStyleSheet("QToolTip{...}")`，背景取 `box_bg`、文字取 `dark`、边框取 `main` —— **随红/绿主题一致**。
- **修复未选生肖时下拉框外观**（用户图 2 反馈）：未选时显示「生肖 ⋯」，下拉弹层样式与整体风格一致且随日期红绿变色。
  - **现象**：旧默认项只写「生肖…」，下拉弹层用静态色（`#faf8f0` 底 / `#eeeeee` 选中），与红绿主题脱节。
  - **修法**：默认项改为「生肖 ⋯」（三个点即下拉按钮的视觉提示）；`QComboBox` QSS 增加 `hover` 态、`::down-arrow` 主题色箭头，弹层 `QAbstractItemView` 用主题变量填充（`background:%s`+`box_bg`、`selection-background-color:%s`+`main`、`selection-color:#ffffff`），随红/绿切换。
- **新增 `[12]` 组 11 条断言**（`verify_ui.py` **90/90 → 101/101**）：建议卡几何方法存在且返回 4 张卡、几何与绘制一致、落在页内不压底部、hover 接住 + dwell 计时 + 真正 `showText` + 手型光标 + 离开收起；生肖框默认文本「生肖 ⋯」、tooltip 全局配色含主题变量、下拉弹层主题化。
- **验证**：`verify_ui.py` **101/101** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `font_weight_probe.py` **5/5** ✓ · `geom_probe.py` 通过 ✓。
- **改动文件**：`ui/page.py`（`_advice_rects` / `_show_advice_tip` / `mouseMoveEvent` / `leaveEvent` / `_build_controls` 默认项 / `_theme_controls` tooltip+弹层 QSS）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`README.md`、`CHANGELOG.md`。

### v1.8.9 (Build 2609290001) — 2026-09-29

- **新增「今日成语」**（用户红框标注需求）：年份行与巨大数字之间的居中空带，按当日分数显示对应成语。
  - **分数口径**：**优先本日生肖分数**（页顶已选生肖时的 `zodiac_report["score"]`，如「三合火局（80分）」）；**未选生肖则用本日分数**（`fortune_score`，如「68分」）。
  - **十段映射**：0–9 否极泰来 · 10–19 绝处逢生 · 20–29 转危为安 · 30–39 化险为夷 · 40–49 逢凶化吉 · 50–59 时来运转 · 60–69 渐入佳境 · 70–79 万事顺遂 · 80–89 吉星高照 · 90–100 圆满无缺（`idx = min(score,100)//10` 封顶 9）。
  - **字体**：同箴 / 谶标题 —— 华文中宋（`ZH_FONT`）`QFont.Black` 24px；**颜色随主题红绿**（取调色板 `dark`）。
  - **几何**：`IDIOM_RECT = (150, 103, 220, 30)`，`AlignCenter` 居中于页中线。巨大数字 168px 的墨迹顶约 y=144，本带下沿 133，不相压；左「丙午年·马」墨迹止于 ~114、右「节气」起于 ~369，均不冲突。
- **新增 `[11]` 组 8 条断言**（`verify_ui.py` **82/82 → 90/90**）：
  - 分数段映射 **23 个边界值**（每段首尾 + 100 封顶）全对；
  - 源码断言：生肖分优先口径、字体 `ZH_FONT`+`Black`、颜色 `QPen(dark)`、`IDIOM_RECT` 居中绘制；
  - **真实渲染**：红 / 绿两日成语带内均有墨迹（n>200）、bbox 中心在页中线 260±12、墨迹留在 y 98–138 带内不压巨大数字。
- **实测**：红日（44 分）→「逢凶化吉」、绿日（62 分）→「渐入佳境」，均居中显示、随主题变色。
- **验证**：`verify_ui.py` **90/90** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `font_weight_probe.py` **5/5** ✓ · `geom_probe.py` 通过 ✓ · pyflakes 零输出 ✓。
- **改动文件**：`ui/page.py`（`IDIOM_RECT` / `IDIOM_BY_BAND` / `idiom_for_score()` / `_paint_header` 绘制）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`README.md`、`CHANGELOG.md`。

### v1.8.8 (Build 2609280029) — 2026-09-28

- **目录整理**（用户要求「整理目录下的临时文件和缓存文件」）：
  - 清理 `build/` 下残留的 `_probe_box_*` / `_stale_*` / `_cleanup_*` 目录（**4.0 GB → 0**，只留 PyInstaller 正式产物）；
  - 清理 `history/` 旧版 exe，**只保留最近 3 个版本**（v1.8.6 / v1.8.5 / v1.8.4，**6.6 GB → 0.8 GB**）；
  - 清理 `__pycache__` / `.pyc`、root 下误生的 `1` beacon 日志、`dist/` 下的运行期 `settings.json` / `agenda_cache.json` / `agenda_edit.json`。
  - 合计释放约 **9.8 GB**。
- **截图 base64 内嵌进 README**（用户要求「把软件截图直接加入 readme 中避免每次还要外链，并且有图片丢失的可能」）：
  - 现象：v1.8.7 的 README 用 `docs/screenshots/*.png` 相对路径引用 —— 图片仍是独立文件，存在丢失 / 漏提交风险；用户希望图片**直接成为 README 的一部分**。
  - 修法：`verify_ui.py` 新增 `_embed_shots_to_readme()`，每次跑完截图渲染就把四张 PNG **base64 内嵌为 `data:image/png;base64,...`**。每次重渲染都会刷新，README 里的图永远是最新版。
  - README 体积 21 KB → 1.3 MB，GitHub 正常渲染。
  - `[10]` 组断言同步更新：从「README 含 `docs/screenshots/` 路径」改为「README 含 ≥4 个 `data:image/png;base64,` 且四张图的 alt 标记齐备」。
- **全量回归**：`verify_ui.py` **82/82** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · `test_process.py` **18/18** ✓ · `font_weight_probe.py` 真实平台 **5/5** ✓ · `geom_probe.py` 通过 ✓ · pyflakes 零输出 ✓。
- **改动文件**：`calendar_app/version.py`、`README.md`、`tools/dev_checks/verify_ui.py`、`CHANGELOG.md`。

### v1.8.7 (Build 2609280028) — 2026-09-28

- **修复 README 中的软件截图**（用户反馈）。查下来是**两个独立问题**叠加：
  - **① README 的截图表格里根本没有图片**。表格两行四格全是占位文字（`` `绿日` ``、`红日`、`窗口`、`高光`），从未引用 `docs/screenshots/` 下的实际文件 —— 也就是 README 上一直只显示文字、看不到图。
    - 修法：改为标准 Markdown 图片引用 `![绿日](docs/screenshots/screenshot-green.png)` 等四张。
  - **② 「红日」截图实际是绿色的**。`verify_ui.py` 的 `shot()` 用 `page.update() + app.processEvents()` 渲染，而**主窗口有一个每 30s 的跨日轮询定时器** —— `processEvents()` 会把它驱动起来，把 `page.info` **重置回「今天」（2026-09-28，绿色主题）**。结果 `shot(RED, ...)` 存下来的是一张绿日图，README 里红绿对比形同虚设。这正是 SKILL.md「离屏像素断言的正确姿势」里记录的老坑，只是当时没覆盖到截图路径。
    - 修法：`shot()` 改走 `page.repaint()` 同步重绘（不驱动事件循环），并加上 **`assert page.info["date"] == d`** 自检 —— 万一将来有人改回去，截图当场就报错而不是悄悄存错。`bright()`（高光相位亮度取样）与 `screenshot-window.png` / `screenshot-sheen.png` 的生成路径有同样的问题，一并修正。
  - **实测**：`screenshot-red.png` 现在正确显示 **2026-09-27 中秋节法定假日**（红色主题 `#c62828`，页头 `SEPTEMBER` 亦确认不出框），`screenshot-green.png` 为 2026-10-10 平日（绿色 `#1f9c3d`）。
- **新增 `[10]` 组 4 条断言**（`verify_ui.py` **78/78 → 82/82**）：
  - 截图 / `bright` 的**渲染路径不含 `processEvents`**（防红日再被重置成绿日）；
  - 两者都带 **`page.info` 日期自检**；
  - **四张截图文件齐备**；
  - **README 已用真实图片引用四张截图**（非占位文字）—— 直接钉死问题 ①。
  - 实现备注：源码扫描要**剔掉 docstring**，因为 `shot()` / `bright()` 的 docstring 里有意写着「不能用 processEvents」作为警示，按普通文本扫描会误报。改用 AST 取非 docstring 语句的行号来判定。
- **验证**：`verify_ui.py` **82/82** ✓ · `test_process.py` **18/18** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · pyflakes 零输出 ✓。
- **改动文件**：`README.md`（截图表格改真实图片引用）、`tools/dev_checks/verify_ui.py`（`shot`/`bright` 去掉 `processEvents` + 加日期自检 + 新增 `[10]` 组）、`calendar_app/version.py`、`CHANGELOG.md`。

### v1.8.6 (Build 2609280027) — 2026-09-28

- **修复页头英文月份「仍然出框」**（用户二次反馈，明确指出「应该是往右边移动」）。**v1.8.5 没修对方向**——当时只盯了「右边会不会超宽」，而真正的现象是**左边压线**：
  - **真正根因**：`_paint_header` 用 `_painter_shear()` 做切变（`SHEAR = -0.25`），且**以 `area.left()` 为切变轴**。切变让字形顶部向左倾 `|SHEAR| × ascent`，叠加字形自身左缘的倾斜后，**整条月名的墨迹左缘会比 `area.left` 再左移约 20px**。原先 `EN_MONTH_RECT` 的 `left = 36`，于是 `SEPTEMBER` 的墨迹左缘落到 **x=16**，而页边**内框线在 x=21** —— 文字直接压到框线外侧，就是用户反复看到并两次截图标红的「出框」。
  - **为什么 v1.8.5 没解决**：那一版只改了「宽度判断要扣掉切变溢出」和「字号 26 → 21」，**完全没有检查左边界**；断言也只写了 `adv + shear_extra <= width`，同样是只管右边。方向判断错了，改再多也不会好。
  - **修法（三处）**：
    - `EN_MONTH_RECT` 的 left **36 → 50**，把切变造成的左移量补偿回来（实测墨迹左缘落回 x=30）；
    - 新增常量 `EN_MONTH_MIN_X = 26`（内框线 21 + 5px 安全余量）；
    - `_paint_header` 增加**左缘兜底右移**分支：若按 `|SHEAR| × ascent` 估算的左缘仍低于 `EN_MONTH_MIN_X`，就按差额把绘制矩形整体右移，保证任何月名、任何字号下都不压线。
  - **实测**：12 个月名墨迹左缘 **27~31**（全部 ≥ 26，内框线在 21，留 5px 以上余量），最右 167（年份区起点约 180，无侵占）。加粗与斜体观感不变。
- **补上真正管用的断言**（`verify_ui.py` **76/76 → 78/78**）——两条都针对「左边界」，这是前两版一直缺的：
  - **`[8]` 真实渲染量测**：把月名单独画到空白画布（**不叠加整页**，否则页边外框 x=14 / 内框 x=21 会混进墨迹统计，早期就因此把 12 个月名都「量」成 x=14），逐像素求墨迹包围盒，断言**左缘 ≥ `EN_MONTH_MIN_X`**。
  - **`[8]` 源码断言**：要求 `_paint_header` 必须含左缘兜底右移分支（`EN_MONTH_MIN_X` + `est_left`），防止有人回退。
- **验证**：`verify_ui.py` **78/78** ✓ · `font_weight_probe.py`（真实平台）**5/5** ✓ · `test_process.py` **18/18** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · pyflakes 零输出 ✓。
- **教训**：**几何缺陷必须"四个边界"一起量**。前两版盯着字宽算，漏了水平起点；断言也只覆盖了「不超宽」。凡涉及切变 / 倾斜 / 描边这类几何变换，右侧溢出、**左侧溢出**、基线位置都要各自断言，且**只能用真实渲染量测**，抽象估算（advance、估算左缘）在这个问题上连续骗过两次。
- **改动文件**：`ui/page.py`（`EN_MONTH_RECT` left 36→50、新增 `EN_MONTH_MIN_X`、`_paint_header` 加左缘兜底分支）、`tools/dev_checks/verify_ui.py`（+2 条断言）、`calendar_app/version.py`、`CHANGELOG.md` / `README.md`。

### v1.8.5 (Build 2609280026) — 2026-09-28

- **修复页头英文月份「加粗后出框」**（用户反馈：v1.8.4 的加粗已生效，但 `SEPTEMBER` / `OCTOBER` 撑出了可用区）。这是 v1.8.4 那轮改动的**副作用**——当时为了消除"加粗不明显"把基准字号定到 26px，并只按字形的**几何 advance** 判断是否放得下：
  - **根因**：页头月名走 `_painter_shear()` 做仿射切变（`SHEAR = -0.25`）模拟斜体。切变以文字左缘为轴，字形**底部向右伸出 `|SHEAR| × descent`、顶部向左伸出 `|SHEAR| × ascent`**。而旧代码只比较 `horizontalAdvance(month) <= area.width()`：26px 的 `SEPTEMBER` advance = 178px、可用 196px，**判断为"放得下"**，但加上切变溢出 7.5px 后实际渲染 185.5px，左缘已顶到页边内框线——用户看到的就是出框。
  - **修法（两处）**：① `ui/page.py` 把**切变溢出量计入宽度判断**（`avail = area.width() - abs(SHEAR) × (ascent+descent)`），超宽才等比缩字号；② 基准字号 **26 → 21px**（`EN_MONTH_PX`），并把页头月名可用区提为常量 `EN_MONTH_RECT = (36, 56, 190, 40)` 便于断言与调参。
  - **实测**：21px 下最宽 `SEPTEMBER` = 128px + 切变 7.5px = **135.5px / 可用 182.5px**（余量 47px），12 个月名全部从容放下，加粗与斜体观感不变（`font_weight_probe.py` 仍 **5/5**：切变后 Normal=869 / Black=1341，**+54%**）。
- **删除 3 条超 10 字的箴言**（用户点名）——竖排区块上限是 **5 行 × 2 列 = 10 字**，超出的会被 `_wisdom_chars()` 静默截断、条目显示不全：
  - `忍耐是金，退一步海阔天空。`（11 字）
  - `岁寒，然后知松柏之后凋也。`（12 字）
  - `三军可夺帅也，匹夫不可夺志也。`（13 字）
  - 箴言库 **60 → 57 条**；谶言库保持 60 条。⚠ 两库长度**不再相等**，`get_daily_wisdom()` 文档字符串里"组合周期 = 60 天"的说法已作废并更正（两库周期分别 57 / 60 天，最小公倍数 1140 天）。
- **新增护栏**（`verify_ui.py` **74/74 → 76/76**）：
  - `[9]` 组**新增「全部条目字数 ≤10」硬断言**——这是本次问题的直接护栏，以后新增条目超限会立刻红；
  - `[9]` 组条目计数断言改为实际值（箴 57 / 谶 60），避免有人"顺手补齐"又把超长条目塞回来；
  - `[8]` 组「月名不超页头可用宽」断言**修正为真实几何口径**（原先硬编码 196px 且未计切变，正是它放过了本次 bug），并新增一条「绘制代码必须把切变溢出计入宽度判断」的源码断言。
- **验证**：`verify_ui.py` **76/76** ✓ · `font_weight_probe.py`（真实平台）**5/5** ✓ · `test_process.py` **18/18** ✓ · `ui_agenda_probe.py` **43/43** ✓ · `agenda_checks.py` **34/34** ✓ · pyflakes 零输出 ✓。
- **改动文件**：`ui/page.py`（`EN_MONTH_PX` 26→21 + 新增 `EN_MONTH_RECT` + `_paint_header` 计入切变溢出 + 导入 `SHEAR`）、`calendar_app/engine.py`（删 3 条箴言 + 文档字符串更正）、`tools/dev_checks/verify_ui.py`（+2 条断言、修正 1 条）、`calendar_app/version.py`、`CHANGELOG.md` / `README.md`。

### v1.8.4 (Build 2609280025) — 2026-09-28

- **修复「双击 exe 后长时间没反应」的启动卡顿**。一次冻结冒烟里，从 `enter-main` 到窗口显示耗时异常，逐段计时后定位到 **`kill_stale_instances()` 会无条件吃满超时预算**：
  - **现象**：`main()` 第一行的路标 `enter-main` 与后续路标之间被拖住 **17s+**（另一次实测整体 30s+），用户观感就是「双击了没动静」，容易误判为程序没启动而反复双击。源码模式（非冻结）启动仅 **1.4s**，说明是冻结 exe 特有路径。
  - **根因**：旧实现是 `if killed:` 就进入等待循环 —— **只要杀过任何一个残留进程，无论对方是否真的还活着**，都会一路轮询到 `timeout_ms`（默认 3s，叠加多次进程表全量枚举后实际远超）。而残留清理的唯一作用是「让旧实例腾开文件句柄」，**对本实例的界面没有任何依赖**，放在 `QApplication` 之前同步执行纯属自找阻塞。
  - **修法（两处）**：
    - `calendar_app/process.py`：`kill_stale_instances()` 改为**只等待真正被终止过的 PID**，且轮询不再反复全表枚举，改用 `OpenProcess(PROCESS_QUERY_LIMITED)` + `GetExitCodeProcess` 判定单个进程是否已消失（句柄取不到 = 已退出；取到则看退出码是否已脱离 `STILL_ACTIVE`），**无目标时直接返回 0**。
    - `main.py`：把残留清理**整体移到 `win.show()` 之后**，并放进守护线程执行（`_background_kill`）。界面先可见，清理在后台补做，用户感知不到任何延迟。
  - **实测**：`window shown` → `kill-stale done` 仅 **0.10s**（旧实现同一路径 17s+）；单实例下 `kill_stale_instances()` 直调 **0.012s**。
- **新增针对启动阻塞的回归断言**（`tools/dev_checks/test_process.py` 由 **14/14** 扩到 **18/18**）：
  - 无残留时 `kill_stale_instances(timeout_ms=3000)` 必须 **< 0.2s** 返回（钉死「不得无条件轮询」，本次事故的直接护栏）；
  - `main.py` 静态检查三条：清残留**晚于** `win.show()`、跑在**守护线程**里、`QApplication` 之前**不得**再有同步调用点。
- **验证**：`verify_ui.py` **74/74** ✓、`font_weight_probe.py`（真实平台）**5/5** ✓、`test_process.py` **18/18** ✓、`ui_agenda_probe.py` **43/43** ✓、`agenda_checks.py` **34/34** ✓。
- **附带清理**：`%TEMP%` 下积累了 **4 个泄漏的 `_MEI` 解包目录（约 2.07 GB）**——它们是此前若干次冒烟里引导进程被强杀、没能完成回收留下的（引导进程负责删解包目录，被 `taskkill` 掉就没机会删）。已清理。**注意**：这些目录会拖慢冷启动（系统要扫描/杀软要实时扫描），若你自己机器上 `%TEMP%` 里也堆了 `_MEI*`，可放心手动删除（本程序的「自愈清理」线程也会在启动后自动回收超过 10 分钟的旧目录）。
- **改动文件**：`calendar_app/process.py`（`kill_stale_instances` 重写等待逻辑）、`main.py`（清理迁移到窗口显示后的后台线程）、`tools/dev_checks/test_process.py`（+4 条断言）、`calendar_app/version.py`、`CHANGELOG.md` / `README.md`。

### v1.8.3 (Build 2609280024) — 2026-09-28

- **修复「英文加粗在真实运行环境中失效」**（用户反馈：截图里看着是粗的，实际运行只是变大没变粗）。这是一处**离屏测试照不到的盲区**，根因有两层，都在字体注册层面：
  - **① 内置字体的 PostScript 名重复（主因）**。`tools/build_fonts.py` 的 `set_names()` 只改写了 nameID 1/2/4/16/17，**漏了 nameID 6（PostScript 名）与 nameID 3（唯一标识）**。而 `instancer.instantiateVariableFont(..., updateFontNames=False)` 会把可变字体的原始 PS 名原样带过来，于是：
    ```
    NotoSerifSC-Regular.ttf / -Bold.ttf / -Black.ttf  →  nameID 6 全是 NotoSerifSC-ExtraLight
    NotoSansSC-Regular.ttf  / -Bold.ttf               →  nameID 6 全是 NotoSansSC-Thin
    ```
    **Windows / Qt 以 PostScript 名作字体注册键**，三份重名的字重相互覆盖 —— 请求 `Bold` / `Black` 全部落回同一个面（实测深墨像素 Normal=719、Bold=587、Black=587，加粗后反而更细），页头英文因此怎么调都不变粗。**`QT_QPA_PLATFORM=offscreen` 恰好不读这条路径**，所以 v1.8.2 的 61/61 全绿却完全掩盖了线上问题。
    - 修法：`set_names()` 补上 nameID 3 / 6 的写入（逐字重唯一），另加 `tools/fix_font_names.py` 可对**已构建的字体就地修复**、无需源可变字体；5 份字体已修复，实测 `Noto Serif SC` 恢复 Normal=719 → Bold=982 → Black=1149（**+60%**）。
  - **② `QFont.setItalic(True)` 会吞掉字重轴（次因）**。内置 Noto 系**没有斜体面**，一旦 `setItalic(True)`，Qt 走合成斜体分支、**完全忽略字重轴** —— Normal / Bold / Black 全部退化成同一字形（实测三者深墨一律 **587**，比 Regular 的 719 还细）。页头月名原本写 `_font(..., italic=True)`，恰好踩中。
    - 修法：`ui/theme.py` 新增 `_painter_shear(p, center_x)`，用画笔仿射切变（`SHEAR = -0.25`，约 14°）模拟斜体 —— 只做几何变换，字形仍按选定字重光栅化，**字重真实保留**（实测切变后 Normal=869 / Black=1341，**+54%**）。`_paint_header` 改用切变并以文字左缘为轴，不越出可用区；`_font()` 的 `italic` 参数加注释警示，内置族勿用。
- **删除旧的箴言 / 谶言库，换用用户提供的各 60 条新库**（`calendar_app/engine.py` 的 `WISDOM_MAXIMS` / `OMENS`）。旧库为 32 条格言 + 21 条征兆且混入了「今日宜静心养气」这类**当日运势口吻**的句子；新库严格按**箴言 = 修身格言、谶言 = 谶纬征兆**两类分开，各 60 条、无重复，仍由日期种子取模分配（同一天固定、逐日轮转，两库等长故组合周期 60 天）。
  - **排版适配**：新条目字数跨度大（5～13 字），旧代码固定「两列 × 每列 5 字、超过 10 字硬截」，会出现空列与半个空块。新增 `CalendarPage._wisdom_chars()`（剔标点、按上限截断）与 `_paint_wisdom()` —— **列数按实际字数自适应**：≤5 字走**单列居中**（与标题对齐），6～10 字走两列，超过 10 字截断。实测短条（`生于忧患，死于安乐。`）单列居中、长条（`青气上升，赤气下降。`）双列，两块均不溢出 5 行块高。
- **验证**：`verify_ui.py` 由 **61/61** 扩到 **74/74** ✓ —— 新增 `[8]` 组补上**平台无关的字体 name 表校验**（nameID 3/6 全库不重复、`Noto Serif SC` 三字重 PS 名互异、墨迹梯度、页头不得用 italic）与 `[9]` 组 8 条（箴谶各 60 条、无重复、竖排 1～10 字、标点不进竖排、列数自适应、两块均有字、行数不超 5）。**新增 `tools/dev_checks/font_weight_probe.py`**：**必须在真实平台插件下运行**（显式不设 `QT_QPA_PLATFORM=offscreen`），直接量渲染墨迹断言 `Normal < Bold < Black`，并断言「italic 确实会吞字重」以防有人改回去 —— 这正是旧测试照不到的那条路径，5/5 通过。`ui_agenda_probe.py` **43/43** ✓、`agenda_checks.py` **34/34** ✓、`test_process.py` **14/14** ✓、`geom_probe.py` 通过 ✓。
- **改动文件**：`tools/build_fonts.py`（`set_names` 补 nameID 3/6）、`tools/fix_font_names.py`（新增）、`fonts/*.ttf`（5 份就地修复）、`ui/theme.py`（`_font` 注释 + `SHEAR` / `_painter_shear`）、`ui/page.py`（`_paint_header` 改切变 + 新增 `_wisdom_chars` / `_paint_wisdom` / `_paint_big_day` 拆分）、`calendar_app/engine.py`（箴谶两库全量替换）、`calendar_app/version.py`、`tools/dev_checks/verify_ui.py`、`tools/dev_checks/font_weight_probe.py`（新增）、`CHANGELOG.md` / `README.md`。


### v1.8.2 (Build 2609280023) — 2026-09-28

- **英文加粗**（用户反馈）。排查后发现「英文看起来不粗」其实是**两个问题叠加**：
  - **① 字重没吃满**：页头月名原写 `_font(msize, EN_FONT, QFont.Black, italic=True)` —— 参数本身是 Black(900)，但**字号被分支切成两档**（`msize = 26 if len(month) <= 6 else 20`），于是 `MAY / JUNE / MARCH` 用 26px、而 `JANUARY / SEPTEMBER / NOVEMBER / DECEMBER` 等长月名被压到 **20px**，同一个页头上英文月名忽大忽小，长月名细看明显偏小偏细。
  - **② 字重选择其实有效但不够**：实测内置 `Noto Serif SC` 的 Black 静态实例墨迹比 Regular 厚 **+75%**（`OCTOBER` 深墨像素 664 → 1165），字重本身没问题 —— 所以「不粗」的观感主要来自上面那个 20px 分支。
  - **修法**：`_paint_header` 改为**基准字号 + 整字等比自适应** —— 新增常量 `CalendarPage.EN_MONTH_PX = 26`，用 `QFontMetricsF` 量出实际宽度，**只有真的放不下才整体缩小**（`setPixelSize`，下限 12px），不再按字符数硬切两档。12 个月名实测全部落在 26px，最宽 `SEPTEMBER = 169.0px`（可用 196px，余量 27px），**大小与粗细终于一致**。
  - 顺带统一另外两处英文：**英文星期**（中栏 `MONDAY` 等）由 `QFont.Bold` 升为 **`QFont.Black`**，与页头字重同源，不再一处粗一处细；**页脚版权行**的英文品牌名（`Copyright 2026 肆月Aperture`）改为**加粗**、中文说明保持常规 —— 用 `QFontMetricsF` 分别量宽后分两段左对齐绘制（`fm_b` / `w_brand` / `w_tail`），整行仍水平居中，既满足「英文加粗」又保住这行浅灰弱化的观感。
- **验证**：`verify_ui.py` 由 **54/54** 扩到 **61/61** ✓，新增 `[8]` 组 7 条 —— 「12 个月名英文均不超页头可用宽（基准 26px）」、「长月名不再缩字号（统一 26px）」、「英文月份 Black(900) 墨迹显著多于 Normal(400)（真加粗，实测 +75%）」、「页头英文月份走 Black(900) 且字号自适应」、「英文星期改用 Black(900) 与页头字重一致」、「页脚版权行英文品牌名加粗、中文说明保持常规」、「英文星期在 150px 框内不溢出（`WEDNESDAY` = 73px）」。`ui_agenda_probe.py` **43/43** ✓、`agenda_checks.py` **34/34** ✓、`test_process.py` **14/14** ✓、`pyflakes` 除 `ui_main.py` 有意保留的兼容再导出外**零告警** ✓。
- **改动文件**：`ui/page.py`（`_paint_header` / `_paint_middle_band` / `_paint_footer` + 新增 `EN_MONTH_PX` 常量与 `QFontMetricsF` 导入）、`calendar_app/version.py`（版本号）、`tools/dev_checks/verify_ui.py`（`[8]` 组）、`CHANGELOG.md` / `README.md`。

### v1.8.1 (Build 2609280022) — 2026-09-28

- **修复中栏「喜神 / 财神 / 福神 / 冲煞 / X命互禄」第 5 行被整行裁掉（显示不全）**：根因是 v1.8.0 换成内置字体后暴露的**行距差异** —— 旧代码用 `drawText(rect, ..., "\n".join(rows))`，Qt 的换行行距取自字体的 `ascent + descent + leading`；系统宋体（SimSun）约 1.15em，而内置 **Noto Serif SC 为 1.42em（14px → 20px）**，五行需 **100px**，中栏实际可用高仅 **86px**，于是第 5 行「X命互禄 Y命进禄」被整行裁掉。
  - 修法：新增 `CalendarPage._draw_rows(p, rows, rect)`，**按 rect 高度等分定位、逐行 `AlignCenter | TextDontClip` 绘制**，行距只由 rect 决定、与字体行距完全解耦，此后换任何字体都不会缺行。
  - 同时把中栏文字区由 `QRect(192, y+5, 136, h-10)` 放宽为 `QRect(184, y+3, 152, h-6)`（左 184 / 右 336，恰在宜框右缘 180 与忌框左缘 340 之间），高度 90px 等分 5 行 = **18px/行**；三年逐日扫描最宽一行 `酉命互禄 丙,戊命进禄` = **134px**，在 152px 内余量 18px，横竖都不再裁切。字号维持 14px（与宜 / 忌正文一致）。
- **同类隐患一并修复：宜 / 忌 文本第 3 行被裁**（排查中栏时用像素扫描发现）。同一根因——内置字体行距变大：三维扫描（2026 起 1096 天 × 宜忌）显示最多需 **3 行 = 60px**，而旧文字区 `QRect(38, y+42, 140, h-48)` 只有 **48px**，2026-01-06 宜的第三行「会亲友」被切掉（实测可见）。
  - 新增 `CalendarPage._draw_para(p, text, rect, max_lines)` + `_wrap_px(fm, text, width)`：**手工按像素断行**（以「、」为优先断点，标点绝不落行首；单条目超宽才逐字硬断），再**按实际行数自适应行距** `step = min(字体行高, rect高 / 行数)`，超出上限时末行省略号收尾。文字区改为 `QRect(38, y+40, 140, 54)`（圆圈底 y+36 与方框底 y+96 之间），3 行时行距 18px。实测三行日末行墨迹底 **y=476 / 文字区底 478**，不再触边。
- **八卦水印透明度 20% → 40%**：中栏底部的八卦底纹由 `setOpacity(0.2)` 调为 **`setOpacity(0.4)`**，与用户预期一致。（底部生肖剪影水印的 20% 未动。）
- **修掉校验脚本的一个「量错日期」陷阱**：`verify_ui.py` 的像素探针原用 `page.update() + app.processEvents() + grab()` 取图，而 `processEvents()` 会驱动主窗口每 30s 的跨日轮询定时器，把 `page.info` **重置回「今天」**——于是「三行日 2026-01-06」量到的其实是 2026-09-28 的画面（表现为断言时对时错）。全部改为**同步 `page.repaint()` + 不处理事件**，取图日期从此确定。
- **顺手修掉三个校验脚本的沙盒泄漏（`build/` 膨胀元凶）**：`agenda_checks.py` / `ui_agenda_probe.py` / `test_process.py` 各自 `os.makedirs(BOX)` 却**从不删除**，跑一次就在 `build/` 留一个目录，数月累积把 `build/` 撑到 **~11 GB**（v1.8.0 清理时才发现）。新增 `tools/dev_checks/_box.py::make_box()`——统一在 `build/` 下建 `<tag>_<pid>` 沙盒并 `atexit.register(shutil.rmtree, ...)` 兜底，断言失败 / 抛异常 / `sys.exit()` 都会回收；实测连跑四套脚本后 `build/` 只剩 PyInstaller 自己的目录。
- **代码整洁**：清掉 v1.8.0 机械拆包时残留的未使用导入（`ui/page.py` 的 `QTime / QVariantAnimation / QImage / QPixmap / QCursor / QApplication / PAPER`，`ui/dialogs.py` 的 `date / QCheckBox / bazi_day_report / _tinted_pixmap / ZH_SONG`，`ui/agenda.py` 的 `calendar_app_fonts / use_builtin_fonts`），删掉 `engine.py::_lunar_month_size` 里的死变量 `nxt / cur`；`ui_main.py` 的兼容再导出块加注释 + `# noqa: F401` 标明「有意为之，勿删」。现 `pyflakes ui/*.py main.py calendar_app/*.py` **零告警**。
- **验证**：`verify_ui.py` 由 **37/37** 扩到 **54/54** ✓，新增 `[6]` 组 7 条 —— 红 / 绿两态「五行全部有字」（逐槽统计深墨像素，阈值 120 可滤掉 40% 的八卦）、「文字未溢出到方框之外」（越界像素必须为 0）、「中栏改逐行等分绘制」（源码断言，且禁止出现 `"\n".join(rows)`）、「八卦透明度已调至 40%」、「三年内最宽一行仍可容于中栏」；`[7]` 组 10 条 —— 「宜/忌 三年内最多 3 行」、「三行日 / 两行日 每一行均有墨」、「末行墨迹未触底边」、「改手工断行绘制（不再用 TextWordWrap）」、「行距由 rect/行数决定」、「断行优先在「、」处、标点不落行首」。`ui_agenda_probe.py` **43/43** ✓、`agenda_checks.py` **34/34** ✓、`test_process.py` **14/14** ✓、`geom_probe.py` 通过 ✓。冻结 exe 复验：路标 `fonts installed 2` → `MainWindow built` → `window shown` → `autoquit timer fired` → `exec returned rc=0` → `about to os._exit`，干净退出；`八卦.png` / `logo.png` / 三份字体子集均确认已在包内。exe 体积 **270.8 MB**（与 v1.8.0 持平），旧版归档 `history/农历日历_v1.8.0_2609280021.exe`。

### v1.8.0 (Build 2609280021) — 2026-09-28

- **内置全部字体（设备无关字形）**：不同 Windows 设备的中文字体差异（缺华文中宋、楷体被替换等）会直接导致排版错位。新增 `calendar_app/fonts.py` + `fonts/` 目录，随 exe 打包 **Noto Serif SC（Regular / Bold / Black）+ Noto Sans SC（Regular / Bold）** 共 5 份子集 TTF（**12.96 MB / 每份 7554 字形**）。由 `tools/build_fonts.py` 用 `fontTools.varLib.instancer` 把 OFL 可变字体实例化为静态字重，再按 **GB2312 全集 + ASCII 0x20–0x7E + 全角空格 + 源码内全部非 ASCII 字 + 补充符号**子集化裁剪（若只收非 ASCII 会导致数字变豆腐块，已修）。运行时在 `QApplication` 之后 `addApplicationFont` 注册，并把族名插到 `ZH_FONT / ZH_SONG / ZH_WISDOM / NUM_FONT / EN_FONT` 五条回退链最前（`ui/theme.py` 的 `use_builtin_fonts()`）；注册失败自动回退系统字体，不影响启动。
  - **踩坑**：`QFontDatabase.addApplicationFont` 在**没有任何 `QGuiApplication` 实例**时调用会直接 **Segmentation fault（exit 139）**。已在 `install_fonts()` 加守卫 `if QGuiApplication.instance() is None: return []`，并在 `main.py` 中把它排在 `QApplication()` 之后、任何控件创建之前。
- **代码结构整理（2177 行单文件 → `ui/` 包）**：`ui_main.py` 机械拆分为 `ui/theme.py`（素材路径 / 调色板 / 三级图片缓存 / 字体回退链，203 行）、`ui/page.py`（`CalendarPage` 撕页日历自绘主体，676 行）、`ui/agenda.py`（行事历面板 + 导入 / 导出对话框，432 行）、`ui/dialogs.py`（祭拜三清 + 八字对话框，345 行）；`ui_main.py` 瘦身为 `MainWindow` + 兼容再导出（581 行）。拆分用 `tools/split_ui.py` 按 AST 行区间机械切割，切完立刻跑 AST 解析 + pyflakes 扫描补齐缺失导入（`QIcon / QRectF / QBrush / QPushButton / QSlider / QVariantAnimation / COLOR_CHIPS / os / _tone_of` 等），并**额外发现并修掉一处回归**：拆包后 `_PIX_CACHE / _PIX_SCALED_CACHE / _PAPER_CACHE` 未再导出，导致缓存容器断言失败，已在 `ui_main.py` 补回再导出。
- **目录整理与 `.gitignore`**：新增 `tools/clean_workspace.py`（清理 `build/`、各 `__pycache__`、`tools/_font_src/`、`_sheen_tmp.png`，`--apply` 才真删）；新增 `.gitignore` 屏蔽 `__pycache__/`、`*.py[cod]`、`build/`、`dist/`、`history/`、`settings.json`、`agenda_cache.json`、`agenda_edit.json`、`tools/_font_src/`、`.workbuddy/`、`nul`、`*.tmp`，使工程可直接 `git init && git add .` 发布。`build/` 下累积的 ~11 GB 历史探针目录已清理（本机 `cmd rd /s /q` 比逐文件 `rm` 快两个数量级）。
- **README 改版为 GitHub 发布格式**：顶部徽章（版本 / 平台 / Python / Qt / 离线 / 许可）、**四张真实截图**（`docs/screenshots/`，由 `verify_ui.py` 离屏渲染，已能显示真实中文字形）、折叠式功能清单、下载与运行、内置字体说明、**宜忌数据口径与更新周期**专章、目录结构、构建与开发校验、许可与联系。完整迭代记录拆出为独立的 `CHANGELOG.md`，README 只保留版本速览表。
- **宜忌数据源调研结论**（见 README「宜忌数据口径与更新周期」）：本软件宜忌是 **lunar_python 天文历算 + 建除/值神规则表逐日合成**，不是抄纸质通书。农历 / 干支 / 节气 / 建除 / 值神实测 **1900–3000 全部可用**（抽查 1900 / 1920 / 1950 / 2026 / 2033 / 2060 / 2100 / 2200 / 2500 / 3000），**不存在「数据用完」的问题**；唯一会过期的是 `calendar_app/engine.py` 里的 **`STATUTORY_RANGES`（法定假日表，现仅 2026 / 2027）**，国务院每年 10–11 月发布次年安排，建议**每年 Q4 加一年**。过期后自动降级为「节日当日兜底识别」，只少标红不报错、不算错宜忌。
- **验证**：`verify_ui.py` **37/37** ✓（新增内置字体注册与族名断言、截图改输出到 `docs/screenshots/`、版本号断言升到 `1.8.0 / 2609280021`）；`ui_agenda_probe.py` **43/43** ✓、`agenda_checks.py` **34/34** ✓、`test_process.py` **14/14** ✓、`geom_probe.py` 通过 ✓。冻结 exe 端到端：路标日志 `fonts installed 2`（5 个 TTF → 2 个族：`Noto Serif SC` / `Noto Sans SC`）→ `MainWindow built` → `exec returned rc=0` → `os._exit`，干净退出。exe 体积 **270.8 MB**（较上版 +9.9 MB，即内置字体），旧版归档 `history/农历日历_v1.7.2_2609280020.exe`。

### v1.7.2 (Build 2609280020) — 2026-09-28

- **行事历文字随红 / 绿主题切换**：本月 / 本日面板正文墨色不再是固定墨绿，改随当日主题 —— 红日深红 `#8e1a1a`、绿日墨绿 `#136b29`（取自印刷调色板的 `dark` 色），与标题带、编辑 / 保存按钮、滚动条滑块同一主题来源。
- **窗口贴边吸附（不隐藏）**：拖动窗口距屏幕工作区任一边缘 ≤14px 时自动吸附贴边（`moveEvent` 内计算 + `_snapping` 防递归），多显示器下跟随窗口所在屏幕；**只贴边，绝不自动隐藏**。
- **记住上次窗口位置**：位置随 `settings.json`（`win_pos`）持久化——拖动停稳 0.6s 防抖写盘，关闭 / 隐藏 / 退出时亦保存；再次打开自动回到上次位置。无记录、或记录坐标不在任何屏幕（如拔掉显示器）时自动回桌面正中央。
- **托盘菜单新增「初始化位置」**：位于「显示 / 隐藏」之下，点击后窗口立即回桌面正中央并记忆——是窗口跑丢 / 拖出屏幕后的兜底出口。
- **修复历史错位：无边框拖动 / closeEvent 曾挂在 BaziDialog 上**：`mousePressEvent / mouseMoveEvent / mouseReleaseEvent / closeEvent` 四个方法在源码中物理位置位于 `class BaziDialog` 之后，按 Python 作用域实际成为八字对话框的方法——MainWindow 一直**没有** `closeEvent`（此前「关闭到托盘」仅靠 `setQuitOnLastWindowClosed(False)` 表现一致，且关闭时未保存设置）。已整块归位到 `MainWindow`：现在拖动吸边生效、关闭即存位置、`_save_settings` 在关闭时真正执行。
- **验证**：`ui_agenda_probe.py` 扩到 **43/43** ✓（新增：红/绿正文墨色切换、首次居中、左/上/右/下四边贴边、中间不吸附、贴边后完整可见、初始化位置回正中、`win_pos` 落盘、再次打开回上次位置、异常坐标兜底）；`verify_ui.py` **35/35** ✓、`agenda_checks.py` **34/34** ✓、`test_process.py` **14/14** ✓、`geom_probe.py` 通过 ✓。exe 体积 **261.0 MB**，旧版归档 `history/农历日历_v1.7.1_2609280019.exe`。

### v1.7.1 (Build 2609280019) — 2026-09-28

- **行事历正文过长可滚动**：本月 / 本日面板正文由 `paintEvent` 直绘改为**常驻 `QPlainTextEdit`**（只读、无框、透明背景，观感与纸面印刷一致）。文字过多时右侧出现**当日主题色细滚动条**（8px 圆角滑块，槽透明，颜色随红 / 绿日自动切换），可滚轮翻看，不再截断；「编辑」时解除只读并切换为纸色底 + 主题色边框的编辑态。记录切换 / 导入 / 保存后自动刷新正文并回到顶部。
- **「✎ 本条内容已手工修改」移位**：从面板左下角移&#x5230;**「编辑」按钮左侧同行**（右对齐于按钮排），不再与「共 X 条」计数挤在角落。
- **页角圆点归位**：外框四角装饰圆点的圆心此前右缘写成 `PAGE_W - 20`，偏离外框顶点 6px（左缘 `14` 正确）——红 / 绿两态的右上、右下两颗肉眼可见「不在顶点上」。改为 `(14, 14) / (PAGE_W-14, 14) / (14, PAGE_H-46) / (PAGE_W-14, PAGE_H-46)`，四颗全部恰落顶点。新增 `verify_ui.py` 像素级校验：直接取样四个顶点坐标判定颜色命中（红 / 绿各 4/4）。
- **验证**：`ui_agenda_probe.py` 扩到 **31/31** ✓（新增：常驻只读态、正文刷入编辑器、透明样式、滚动条主题色、长文滚动量 >40px、编辑态边框、「✎」标记绘制位置墨迹对照 有覆写 264px / 无覆写 0px）；`verify_ui.py` **35/35** ✓（新增红 / 绿两态四顶点圆点命中）；`agenda_checks.py` **34/34** ✓、`test_process.py` **14/14** ✓、`geom_probe.py` 通过 ✓。exe 体积 **260.9 MB**，旧版归档 `history/农历日历_v1.7.0_2609280018.exe`。

### v1.7.0 (Build 2609280018) — 2026-09-28

- **龙凤左右贴边（不留白）**：龙凤水印由「固定左右内缩」改为**以页面中线为轴对称贴边** —— 新增常量 `CalendarPage.LF_INSET = 186`，龙的墨迹右缘 / 凤的墨迹左缘锚在 `中线 ± 186`，再按源图比例反算宽度。实测龙墨迹 `x=74..157`、凤墨迹 `x=360..445`（页面宽 520），左右留白 **74 / 75 px** 基本对称，两侧不再有空白带。
- **行事历模板改为表格**：「下载行事历模板」默认产出 **`月度行事历模板.xlsx`**（openpyxl 生成）：表头 `农历月 / 干支 / 公历起 / 公历止 / 重点内容`（绿底白字、细边框、冻结首行、列宽 10/10/10/10/68），首行「月度行事历（模板）」+ 说明 + `2026 丙午年`，预填正月～腊月 12 行。旧版 PDF 模板仍保留（下拉可选）。
- **导入同步支持表格**：新增 `extract_xlsx_rows` / `extract_csv_rows` / `rows_to_text` 与结构化 `parse_table()`（表头模糊映射：农历月/月/月份；干支/月干支；公历起/起/开始；公历止/止/结束；重点内容/内容/要点/备注），无表头时按「首列月名」兜底，年份从标题行 `2026 丙午年` 自动识别。导入入口按扩展名分派 `.xlsx/.xlsm/.csv/.pdf/.docx/.xls/.doc/.txt`。
- **内置离线智能解析（Word / PDF 不再失败）**：解析改为**两层**，先看结构化表格，再走宽松逐行锚点，对断行 / 段落 / 手写排版都不敏感：
  - `_parse_strict`——《月度行事历》原格式精确匹配，支持合并月写法（`十 / 冬月丁亥（约 11.10–1.7）：`）；
  - `_parse_loose`——逐行锚点，`[月名][月][干支][(约 a-b)][：]` 五项均可省略，阿拉伯数字月份（`9月`）、`冬 / 腊` 等别名均可识别，多行正文自动归属上一条目，并剥离 `引用 N 篇资料`。
  - 修掉严格解析下**合并月条目被误丢**的问题：`十 / 冬月` 整体匹配后，内部嵌套的 `冬月` 重复匹配会让正文切片取到 `[67:48]`（空串）而整条被丢弃。改为**先剔除嵌套重复项再切片**（`kept` 列表），现正确产出 2 条。
  - 整个过程**纯本地、不联网、不依赖任何模型**，仅用正则与规则推理，即所谓「离线 AI 解析」。
- **修复导入崩溃 `%d format: a real number is required, not list`**：根因是 `ui_main.py` 用 `"%d" % n`，而 `import_agenda()` 返回的是**记录列表**（PDF / Word 其实都解析成功了，只是提示语崩了）。改为 `records = import_agenda(path); n = len(records)`。
- **本日 / 本月行事历面板右下角新增「编辑 / 保存」**：面板内置 `QPlainTextEdit` + 两个按钮（46×22，位于 `PANEL_H-32`、右对齐）。点「编辑」展开输入框并变「取消」，点「保存」写入覆写层 `agenda_edit.json`；未保存则点「取消」回退。覆写层**优先于导入内容**显示，并在面板左下角标注「✎ 本条内容已手工修改」。键规则：本月面板按 `干支年|农历月`（导入新行事历后同月条目仍复用同一份手写内容），本日面板按 `YYYY-MM-DD`（可逐日手写备注）。按钮与输入框随当日红/绿主题色联动。
- **新增「导出行事历」（可选日期区间）**：导入对话框升级为「行事历 · 导入 / 导出」（三按钮），新增 `AgendaExportDialog` —— 两个 `QDateEdit`（`yyyy-MM-dd`、带日历弹窗，默认今天 ~ 今天+1 月）+ 格式下拉（Excel / CSV / 文本）。按「与条目公历区间有交集」筛选，跨年条目（如冬月 `12.10-1.7`）自动推算为 `2026-12-10 ~ 2027-01-07`；起止反序自动纠正；空区间给出可读提示而非崩溃。导出表含 `年份 / 干支年 / 农历月 / 月干支 / 公历区间 / 重点内容` 六列。
- **修复 `AttributeError: 'QDate' object has no attribute 'toPyDate'`**：导出对话框误用了 PyQt 的 API。PySide6 中 `QDate → datetime.date` 是 **`toPython()`**，`toPyDate()` 只存在于 PyQt —— 该 bug 在真机点「导出」时必崩，已由离屏 UI 探针捕获并修复。
- **打包调整**：spec `hiddenimports` 加入 `pypdf`、`openpyxl`，并 `collect_submodules('openpyxl')`，保证表格导入/导出在单文件 exe 中可用。
- **验证**：新增三套可复跑回归 —— 行事历数据层 `agenda_checks.py` **34/34** ✓（严格/宽松/表格解析、xlsx+pdf 模板往返、区间筛选与跨年推算、xlsx/csv/txt 导出、覆写层）；行事历 UI 探针 `ui_agenda_probe.py` **23/23** ✓（编辑/保存落盘与取消回退、按钮位置、导入崩溃回归、导出四种分支）。**冻结环境端到端探针 `frozen_agenda_probe.py` 12/12** ✓（先打成独立 exe 再跑，实测 `openpyxl 3.1.5` / `pypdf 6.17.0` / `reportlab 5.0.1` 均已入包，模板→导入→区间导出→覆写全链路通）；原有 `verify_ui.py` **33/33** ✓、`test_process.py` **14/14** ✓、`geom_probe.py` 几何判定**通过**（龙凤左右留白 74/75）。exe 体积 **261.0 MB**，旧版归档 `history/农历日历_v1.6.0_2609270017.exe`。


### v1.6.0 (Build 2609270017) — 2026-09-27

- **龙凤缩小 + 随红绿换图**：大日期两侧左龙右凤水印高度由 230px 缩至 168px，改从 `龙凤/` 目录按当日主题取图 —— 红日取 `龙（红）.png` / `凤（红）.png`，绿日取 `龙（绿）.png` / `凤（绿）.png`（`_tone_of` 判色 + `_lf_asset` 组路径），40% 透明度、绘于文字之下、左右对称。
- **龙凤对位修正**：旧版固定 `y=187..355`，比巨大数字中心低 68px，会下坠压到云纹与中栏上沿。改为以数字框 `NUM_RECT`（`y=110..296`，中心 203）垂直居中，现为 `y=119..287`，底部恰好停在云纹（y=300）之上。数字框、印影框、字号提取为 `NUM_RECT` / `NUM_SHADOW_RECT` / `NUM_FONT_PX` 常量，避免多处硬编码。
- **「X日 · 属X」云纹**：新增 `_paint_cloud`，在干支行（`戊申日 · 属猴`）左右两侧各绘制一条 156×15 云纹装饰带，同样随主题红绿取 `云纹（红）.png` / `云纹（绿）.png`，左右对称、居中于干支行。
- **巨大数字斜向高光流动**：新增 `_paint_sheen`，用 **45° 线性渐变画刷重绘同一段数字**——渐变只在字形内部着色，天然被字形轮廓裁切，无需手工构造字形路径或逐帧遮罩；亮带沿 `x+y` 轴推进，自左上扫向右下，4.8 秒一轮（30fps，峰值透明度 68/255），一轮结束后有短暂静默期。仅 `update(SHEEN_RECT)` 刷新数字区域。
- **卡顿修复（性能）**：绘制过程中直接 `QPixmap(路径)` 会在**每一帧**重新读盘 + 解码 + 平滑缩放。实测整页 `paintEvent` **57.4ms/帧（≈17fps）**，其中 `_paint_dragon_phoenix` 4.54ms、`_paint_yiji` 1.43ms、`_paint_paper` 0.70ms —— 拖动窗口、切换页面时明显发滞。新增 `_PIX_CACHE` / `_PIX_SCALED_CACHE` / `_PAPER_CACHE` 三级缓存与 `_pix_cached()` / `_pix_scaled()` / `_paper_pixmap()` 三个取用函数，龙凤·云纹·八卦·生肖水印与纸面底纹全部改为命中缓存。修复后整页 **3.0ms/帧（≈330fps）**，`_paint_dragon_phoenix` 降至 0.15ms（**31×**）。
- **单文件 exe 临时目录泄漏修复（重要，四层）**：PyInstaller onefile 的引导进程会**以同名 exe 再启动一个子进程**承载真正的 Python 代码；删除 `%TEMP%\_MEIxxxxxx` 解包目录是**引导父进程**的职责。实测本机已累积 **284 个目录 / 52.0 GB / 254,413 个文件**（单份解包约 187MB、2256 个文件）。四层修复：
  1. **不再误杀自己的引导父进程**：旧版 `kill_stale_instances()` 只按映像名清理「其它同名进程」，子进程启动时会把自己的引导父进程当残留实例杀掉 → 引导父进程永远没机会回收解包目录。新增 `_ancestor_pids()` 沿父链上溯，`find_sibling_pids(skip=...)` 与 `kill_stale_instances()` 均排除本进程及其全部祖先。
  2. **子进程立即退出，让引导父进程拿到退出信号**：即便不再被误杀，子进程走常规解释器 finalize 时会被仍在运行的 Qt / 后台线程拖住，引导父进程长时间收不到退出信号、迟迟不回收解包目录。改为 `app.exec()` 返回后 `os._exit(rc)` 直接结束进程（需要落盘的 settings.json 已在各自 `with` 块内 flush）。
  3. **只清「应用本体」，绝不杀「引导父进程」**：引导父进程与子进程**映像名完全相同**，只能靠父子关系区分 —— 应用本体的父进程同名（或父进程已消失＝孤儿），引导父进程的父进程是 explorer / cmd 等异名存活进程。`find_sibling_pids()` 据此只返回应用本体；杀掉旧实例的引导父进程 = 永久残留一份完整解包（开第二个实例必泄漏）。进程表通过 `iter_processes()` 抽出以便注入式单测。
  4. **自愈清理**：新增 `cleanup_orphan_temp_dirs()`，启动后在后台线程回收历史残留的 `_MEI*` 目录（只处理 `%TEMP%` 直接子项中 `_MEI` 开头的目录、跳过本进程自身的解包目录、只处理 mtime 早于 10 分钟的目录、先 `os.replace` 做占用探测、单次限 120 个 / 20 秒）。另附一次性回收脚本 `tools/clean_orphan_mei.py`（`--apply` 才真正删除）。
  - 另新增 `SYY_AUTOQUIT_MS`（毫秒后正常退出）与 `SYY_BEACON=<文件>`（启动/退出阶段路标日志）两个环境变量，用于端到端校验干净退出与临时目录回收。
  - **归因证据**：① 最小 PyInstaller 单文件探针（无 Qt/无业务代码）在同环境下 **4.7s 全部收尾、解包目录被正确删除、rc=0** → 证明 onefile 收尾机制本身正常，问题在应用侧；② 路标日志显示应用本体一路走到 `exec returned rc=0` → `about to os._exit`，**应用自身干净退出**；③ 注入假进程表的判定单测覆盖单实例 / 双实例 / 收尾中 / 孤儿 / 三实例级联五种场景。
- **全软件图标统一 logo.png**：启动时 `app.setWindowIcon(QIcon(logo.png))`（主窗口与各对话框继承）；系统托盘图标改由 `logo.png` 生成（缺失时兜底手绘红底「历」字）；打包 `icon='logo.ico'`（多尺寸 16–256，含 256 超大图标）。新增 `logo.png` / `logo.ico` 随 exe 打包。
- **打包调整**：spec `datas` 以 `('龙凤/*.png','龙凤')` 替换原 `龙.png` / `凤.png` 单图，并加入 `('logo.png','.')`；PSD 源文件不入包。
- **验证**：源码态 UI 综合复核 **33/33** ✓（红绿换图、龙凤竖向居中对齐数字中心 203、云纹、图标、三级缓存命中、`3.24ms/帧≈309fps`、45° 渐变高光相位推进与本区域刷新、红绿调色板与版本号回归）；进程判定注入式单测 **14/14** ✓；双实例端到端 **核心断言全过** ✓（真实进程下：新实例启动 1.0s 内清理旧实例应用本体、旧实例引导父进程存活、其解包目录最终被回收）；几何量测：龙墨迹竖向中心 **204.5**、凤 **202.5**（数字中心 203，偏差 ≤1.5px），龙右缘 197 / 凤左缘 322（锚点 198 / 322），云纹左锚 22 / 右缘 495；exe 体积 **257.0 MB**、图标资源 6 档（16/32/48/64/128/**256**）；真机预览 `preview_v160_red.png` / `preview_v160_green.png` / `preview_v160_window.png` / `preview_v160_sheen.png`；旧版 exe 归档：`history/农历日历_v1.5.0_2609270016.exe`。
  - 注 1：无头验证环境 `QFontDatabase.families()` 为 **0**（无任何字体），故预览图中所有文字呈缺字方框，属验证环境限制，与软件本身无关。
  - 注 2：本机（含校验环境）**删除单文件约 206ms**，一份解包 2256 个文件外推需 **≈465 秒** —— 这是校验环境下「引导父进程长期滞留」的直接原因；真实使用中无此拦截，删除为毫秒级（最小 PyInstaller 单文件探针实测 0.5s 内完整收尾）。

### v1.5.0 (Build 2609270016) — 2026-09-27

- **生肖框显示完整**：生肖选择框由 48px 恢复到 64px（下拉箭头收窄 18→14px），「生肖…」占位与所选生肖均完整显示。
- **默认以托盘图标形式运行**：新增系统托盘图标（自绘红底「历」字图标），右键菜单含「显示/隐藏 · 关于本软件 · 退出」；点击窗口 ✕ 仅隐藏到托盘，双击/左键托盘图标恢复，`setQuitOnLastWindowClosed(False)`。
- **左龙右凤水印**：大日期两侧叠加「龙.png」（左）/「凤.png」（右）剪纸水印，40% 透明度、绘于文字之下、左右对称；白底 JPG 已做白转透明处理为 RGBA 素材并随 exe 打包。
- **关于本软件 · 联系作者**：新增联系作者区块，含 GitHub（github.com/zouzuo1994321）、哔哩哔哩（space.bilibili.com/13715）、微博（weibo.com/u/5189652182）、邮箱（<921103025@qq.com>）四项，图标着色为墨色、链接可点击跳转。
- 离屏冒烟 `_smoke_v150.py` 30/30 ✓；真机预览 `preview_v150_main.png` / `preview_v150_about.png`；旧版 exe 归档：`history/农历日历_v1.4.0_2609270015.exe`。

### v1.4.0 (Build 2609270015) — 2026-09-27

- **页顶时分**：页头「9月大」右侧新增当前时分（HH:MM），定时器每 15 秒刷新。
- **每天 0:00 自动撕页**：新增跨日检测定时器（每 30 秒轮询，兼顾休眠唤醒），跨日后带撕页动效自动推进到当天。
- **关于移至底部**：顶栏「关于」下移到底部按钮行最左侧并更名「关于本软件」；底部四个按钮（关于本软件 / 本月行事历 / 本日行事历 / 导入行事历）等宽 105px、间距 14px 平均分布。
- **顶栏调整**：「八字」按钮加宽 34→46（文字完整显示），生肖选择框缩窄 58→48。
- **中栏八卦水印**：喜神/财神/福神/冲煞/寅命互禄 中栏底部叠加「八卦.png」水印（20% 透明度，绘于文字之下，底部对齐）；素材随 exe 打包（spec `datas` 加 `('八卦.png','.')`）。
- **敬香烟雾**：燃香时长不变（21 秒），烟雾出现量与上升速度下调（生成概率 0.5→0.22、上升 1.2~~2.2→0.6~~1.1 px/帧、粒子尺寸与透明度收窄、粒子上限 160→90）。
- 离屏冒烟 `_smoke_v140.py` 22/22 ✓；真机预览 `preview_v140_main.png`；旧版 exe 归档：`history/农历日历_v1.3.1_2609270014.exe`。

### v1.3.1 (Build 2609270014) — 2026-09-27

- **标题行拖动窗口**：按住左上角「农历日历」标题行区域即可拖动窗口位置（`TITLE_RECT` 命中区，CalendarPage 内直接驱动 `window().move()`，与原空白处拖动并存，松开即停）。
- **顶栏透明度滑块**：顶栏「今日」与最小化之间新增横向滑块（30%–100%），实时调整整个窗口的透明度；数值随 `settings.json`（`opacity`）持久化，重启自动恢复。
- **分项建议空白压缩**：事业/感情/出行/财务区块上移并加高单元格（y 666→652、单元格高 46→54），与上方吉时行间距 24→10px、与下方版权行间距 16→14px，上下留白收紧；单元格内标签与两行文字偏移同步调整。
- 顶栏重排：八字 / 生肖 / ◀▶ / 撕页 / 关于 / 今日 / 透明度滑块 / — ✕ 一行排开，互不重叠。
- 离屏冒烟 `_smoke_v131.py` 19/19 ✓（标题行拖动位移、透明度生效/持久化/重启恢复、建议块几何、八字推演回归）；旧版 exe 归档：`history/农历日历_v1.3.0_2609270013.exe`。

### v1.3.0 (Build 2609270013) — 2026-09-27

- **去掉黑色外框**：中央 widget 背景由深色 `#3a3a34` 改为纸色 `#f3f0e6`，与叠页纸面一致，消除窗口四周深色边。
- **底部生肖剪影水印**：新增 `_paint_zodiac_watermark`，按当日生肖（`day_shengxiao`）与主题红/绿取 `生肖/` 下对应剪影 PNG（`生肖（红）.png` / `生肖（绿）.png`），等比缩放至高约 210px 居中压在底部区块，透明度 20%；24 张剪影随 exe 打包（spec 仅带 `生肖/*.png`，排除 2.1MB 的 `生肖.psd` 源文件）。
- **八字录入与推演强化**：顶栏「属相」旁新增「八字」按钮，打开 `BaziDialog` —— 公历/农历切换 + 年/月/日/时（24h）SpinBox，实时预览四柱与生肖，可「保存」或「清除」。保存后 `compute_eightchar` 排盘（日柱固定 12 点规避子时换日歧义，时柱用 `getTimeInGanZhi`），`bazi_day_report` 以「日主 vs 当日干支」做五合/相冲/五行生克/六合/六冲/六害/相刑/生肖合冲三合推演，叠加到本日生肖区块并以「八字推演：日主X（X命）｜ 标签」呈现，运势分取生肖分与八字分均值。八字与录入参数持久化至 `settings.json`（`bazi` / `bazi_input`），重启后自动恢复。
- 离屏冒烟 13/13 ✓；归档 `history/农历日历_v1.2.2_2609270012.exe`。

### v1.2.2 (Build 2609270012) — 2026-09-27

- **谶言列贴齐右边框**：右列 x 432/456 → 456/480，与左侧箴言对称贴边，消除右侧留白。
- **分项建议文字完整显示**：按像素宽度自动断行（第一行标签右侧放不下即折到第二行整行），替换原「截断 20 字 + 省略号」逻辑；同时修正 fontMetrics 在设字前取值导致的宽度误判。
- **中部留白压缩**：吉时/颜色行 586 → 574（贴近上方生肖提示行），分项建议块 658 → 666（贴近版权行）。
- 旧版 exe 归档：`history/农历日历_v1.2.1_2609270011.exe`。

### v1.2.1 (Build 2609270011) — 2026-09-27

- **英文月份字号缩小**：SEPTEMBER 等长月名 27px → 20px（短月名 34 → 26px），不再与年份重叠。
- **箴言/谶言再缩小**：正文 22px → 18px，行距 28 → 22、列宽 32 → 24，标题 30 → 24px。
- **吉/凶框改正方形**：运势带左框 122×52 → 52×52 正方形，分数、本日生肖、值神尾行整体左移。
- **导入行事历升级**：支持 PDF 与 Word（.docx 直接解析，旧版 .doc 兜底）；「导入行事历」按钮从顶栏移至底部，与「本月行事历 / 本日行事历」同排（右端）。
- **宜/忌下方留白压缩**：宜/忌框高 114 → 96，运势带 / 生肖提示 / 吉时颜色 / 分项建议整体上移 18px。
- 旧版 exe 归档：`history/农历日历_v1.2.0_2609270010.exe`。

### v1.2.0 (Build 2609270010) — 2026-09-27

- **敬香燃速减缓**：燃香动画 4.2 秒 → 21 秒（速度 20%）。
- **箴言/谶言排版重做**：箴/谶标题在双列块顶部水平居中；正文换楷体系手书风、保持两列、自左向右读，字号锁定 22px。
- **宜/忌内容右侧不留白**：文本区扩展至框缘。
- **年份与农历日期全软件居中**：页顶「2026」与大数字下方「己酉日 · 属鸡」均以整页中线居中。
- **新增「今日」按钮**：顶栏一键回到当日（带翻页动画）。
- **导入行事历独立弹窗**：支持一键下载《月度行事历》PDF 模板（按解析格式生成，reportlab CID 字体），再选择填好的 PDF 导入。
- **运势带重排**：本日生肖移至分数之后；值神/吉凶神与运势提示合并一行；吉/平/凶框保持方正。
- 旧版 exe 归档：`history/农历日历_v1.1.9_2609270009.exe`。

### v1.1.9 (Build 2609270009) — 2026-09-27

- **对齐修正**：吉时/颜色两框以页面中线对称等宽；宜/忌框与上方「十七日」「星期日」框左右对齐，宜/忌字圈框内水平居中。
- **箴言/谶言放大**：字号 11→24（约 2.2 倍），允许两列竖排（自右向左读），箴/谶首字加大至 30。
- **字体统一**：正文楷体/仿宋观感统一改为宋体（SimSun）。
- **神煞区放大**：喜神/财神/福神/冲煞/黄命互禄 12→14。
- 旧版 exe 归档：`history/农历日历_v1.1.8_2609270008.exe`。

### v1.1.8 (Build 2609270008) — 2026-09-27

- **边框位置修正**：页面红框下沿上移至版权行与行事历按钮之间，不再穿过按钮。
- **香炉与香修正**：香炉贴底下移；三炷香改为先画、炉体后画，香脚藏于炉内（不再漂在炉外）；香烟改为粒子系统（上升、扩散、变淡），燃尽后余烟自然散尽。
- **字体放大**：事业/感情/出行/财务块字号 11→13/12；行事历面板标题 16→18、正文 12→14、副行与统计行同步放大并收紧留白。
- 旧版 exe 归档：`history/农历日历_v1.1.7_2609270007.exe`。

### v1.1.7 (Build 2609270007) — 2026-09-27

- **香炉与香调整**：祭拜三清弹窗中香炉素材缩小至 70%，三炷香长度加倍（香间距随炉收窄），燃香动画比例同步调整。
- **底部footer重排（修复重叠）**：页面加高 830→840；版权行下移至分项建议块之下，行事历双按钮、双击提示依次排开，不再互相压盖、提示不再越界裁切。
- 旧版 exe 归档：`history/农历日历_v1.1.6_2609270006.exe`。

### v1.1.6 (Build 2609270006) — 2026-09-27

- **祭拜三清换画像素材**：三清牌位改为《祖师爷.png》圣像（太清道德天尊 · 玉清元始天尊 · 上清灵宝天尊），香炉改为《香炉.png》整尊绘制（八卦太极金纹炉）；「敬香」后三炷香插入炉中缓缓燃短、香头红光、青烟袅袅。素材随 exe 打包附带，缺失时自动回退自绘牌位/炉体。
- **行事历开关改双按钮**：日历底部「▴ 收起行事历」单一提示改为「本月行事历」「本日行事历」两个按钮，**双击**对应按钮打开 / 再次双击关闭对应面板（两面板独立开关，按钮 ▴ 实心=开启、▾ 空心=关闭）；开关状态随设置持久保存。
- 旧版 exe 归档：`history/农历日历_v1.1.5_2609270005.exe`。

### v1.1.5 (Build 2609270005) — 2026-09-27

- **软件更名**：名称「肆月日历」→「农历日历」（APP_NAME 与标题同步；版权署名仍保留 *Copyright 2026 肆月Aperture*）。
- **开机自动启动**：关于页新增「开机自动启动」开关，写入当前用户注册表 `Run` 键（无需管理员）。
- **祭拜三清彩蛋**：在巨大日期区连续点击 10 次触发（参考《钦天监》祖师爷圣像彩蛋），弹窗列三清道祖（玉清元始天尊 / 上清灵宝天尊 / 太清道德天尊），可「敬香」并给出祈福语，纯民俗体验不联网。
- **本日行事历重点**：在「本月行事历重点」下方新增并列面板「本日行事历重点」，显示当日公历 + 农历，并同样自动匹配导入 PDF 的当前农历月内容；两个面板均新增展示「导入日期」与「结束日期」（结束日期取自记录区间 `约 X–Y` 的结束点）。
- 旧版 exe 归档：`history/肆月日历_v1.1.4_2609270004.exe`。

### v1.1.4 (Build 2609270004) — 2026-09-27

- **整体字号放大、留白收紧**：头部月份/年份/月大小 30→34/36/23px，巨大日期 150→168px，中带、宜忌、运势、生肖、吉时颜色、分项建议各区块字号普遍 +1~2px，区块间距全面压缩。
- **大日期两侧改为竖排箴言 / 谶言**：左侧箴言（修身格言 31 条）、右侧谶言（当日征兆 22 条），与《钦天监》page_today 同源数据，按日期种子逐日轮换；竖排无框直印，首字「箴/谶」深色印字。
- **顶部去红框**：年份、公历月大小不再画框，直接印字；副行字号 12→13px。
- **行事历面板可收起/展开**：点击日历底部提示区（▴ 收起行事历 / ▾ 展开行事历）切换，窗口高度 1045↔850 自适应，面板状态即时刷新。
- 旧版 exe 归档：`history/肆月日历_v1.1.3_2609270003.exe`。

### v1.1.3 (Build 2609270003) — 2026-09-27

- **修复顶栏控件重叠**：标题 / 生肖框 / 翻页 / 导入 / 撕页 / 关于 / 最小化 / 关闭重新排版为一行，右端窗控按钮锚定边框右缘，互不压盖。
- **修复标题底色异常**：标题改为 paintEvent 自绘（避免 central 背景样式被子控件继承），红/绿主题下均为纸底印字。
- **整体紧凑化**：页面 880→830px，行事历面板 220→195px，窗口 536×1045；大数字、中带、宜忌、运势、吉时颜色、分项建议各区块间距收紧。
- 旧版 exe 归档：`history/肆月日历_v1.1.2_2609270002.exe`。

### v1.1.2 (Build 2609270002) — 2026-09-27

- **去外框**：移除顶部深色工具条，生肖选择 / 导入行事历 / 翻页 / 撕页 / 关于 / 最小化 / 关闭全部内嵌进日历纸面（随主题变色）。
- 新增**吉时**：当日黄道吉神当值时辰（干支 + 时间段，双栏展示）。
- 新增**吉凶颜色**：穿衣五行大吉 / 次吉 / 不宜色，附代表色圆点。
- 新增**分项建议**：事业 / 感情 / 出行 / 财务四栏，由建除、值神、吉凶神煞规则合成。
- 新增**法定假日红色主题**：内置 2026–2027 放假表（元旦 / 春节 / 清明 / 劳动 / 端午 / 中秋 / 国庆）+ 节日当日兜底识别，命中当日整页切换红色印制并在副行标注假名（10.1 国庆、9.27 中秋实测通过）。
- UI 优化：页面加高至 880px，版权行移入边框内，行事历面板标题带颜色与当日主题联动。
- 旧版 exe 已归档至 `history/肆月日历_v1.1.1_2609270001.exe`。

### v1.1.1 (Build 2609270001) — 2026-09-27


- 首个功能版本。
- 桌面无边框撕页老黄历界面（绿单色印刷、纸色底、竖排对联、叠纸效果、翻页/撕页动效）。
- 农历通胜引擎：lunar-python + 两广·港澳通书宽松口径宜忌合成、整体运势打分。
- 本日生肖运势（合冲派：三合/六合/值日/六冲/六害/相刑/自刑）。
- 月度行事历 PDF 导入：解析农历节气月条目（2026–2030 共 37 条验证通过），自动匹配当前农历月重点显示，导入结果缓存至 `agenda_cache.json`。
- 预留钦天监对接接口 `calendar_app/bridge.py`。
- 进程管理：启动清理残留进程，退出自清理。
- 版权与声明：Copyright 2026 肆月Aperture，开源软件，未授权禁止商用。

## 版本号规则

- 对外版本：`vMAJOR.MINOR.PATCH`，**MINOR 为大版本迭代位，PATCH 为小版本迭代位**。
- 内部版本号（Build）：`YYMMDDNNNN`（日期年月 + 当日迭代序号），如 `2609270001`。

## 打包

```bash
VENV=/c/Users/zouzu/.workbuddy/binaries/python/envs/default
"$VENV/Scripts/python.exe" -m PyInstaller --noconfirm 农历日历.spec
```

- 打包参数（名称 `农历日历`、`console=False`、`icon='logo.ico'`、`datas` 素材清单）全部写在 `农历日历.spec` 内，不再用命令行长参数。
- 增量构建触发 PyInstaller 清理旧 `build/<name>/` 时，若被宿主环境的批量删除守卫拦下，可先把 `build/农历日历` 改名移走再构建。完整重建约 3.5 分钟。
- 最新版 exe 放 `dist/`，历史版本归档至 `history/`（命名 `农历日历_vX.Y.Z_BUILD.exe`）。
- 运行期数据文件（`settings.json`、`agenda_cache.json`）生成在 exe 同目录。
- 打包后务必清理 PyInstaller 的 `__pycache__` / `build/` 残留，否则体积会异常膨胀。

## 开发校验

`tools/dev_checks/` 下为可复跑的回归脚本（全部离屏运行，无需真实显示器）：

| 脚本                                        | 作用                                                                       |
| ----------------------------------------- | ------------------------------------------------------------------------ |
| `verify_ui.py`                            | 源码态 UI 综合复核：红绿换图、龙凤对位、云纹、图标、三级缓存命中、逐帧绘制耗时、高光相位与刷新区域、调色板/版本号回归，并重生成预览图    |
| `test_process.py`                         | 进程清理判定的注入式单测（单实例 / 双实例 / 收尾中 / 孤儿 / 三实例级联）+ 孤儿解包目录自愈清理行为                 |
| `geom_probe.py`                           | 单独渲染龙凤/云纹并量测墨迹包围盒，精确校验对位（不受缺字环境影响）                                       |
| `exe_smoke.py <exe> [autoquit_ms] [观察秒数]` | 在空沙箱 `TEMP` 下运行单文件 exe，观察双进程结构与解包目录回收                                    |
| `dual_instance_test.py`                   | 双实例端到端：验证新实例只清理旧实例的应用本体、不碰其引导父进程                                         |
| `agenda_checks.py`                        | 行事历数据层：严格/宽松/表格解析、xlsx+pdf 模板往返、区间筛选与跨年推算、导出、覆写层（全部写独立沙盒，不碰用户数据）         |
| `ui_agenda_probe.py`                      | 行事历 UI 离屏探针：编辑/保存落盘与取消回退、按钮位置、导入崩溃回归、导出各分支                               |
| `frozen_agenda_probe.py`                  | **冻结环境**端到端：先打成独立 exe 再跑，实测 openpyxl/pypdf/reportlab 是否真的进了包（源码态测不出打包缺失） |

环境变量（仅校验用，不设则对正常使用零影响）：

- `SYY_AUTOQUIT_MS=毫秒` —— 到点自动正常退出。
- `SYY_BEACON=<文件路径>` —— 记录启动/退出各阶段路标日志（注意：在删除/写入被拦截的环境下，写日志本身会停顿，仅建议在无拦截环境下使用）。

## 目录结构

```
日历软件/
├── main.py                 # 入口：清理残留进程 → 启动 UI（含自动退出/路标钩子）
├── ui_main.py              # 主界面（撕页日历自绘 + 行事历面板 + 顶栏）
├── logo.png / logo.ico     # 全局图标源文件（窗口 / 托盘 / exe 资源）
├── 生肖/                   # 12 生肖剪影（红 / 绿，底部水印用）
├── 龙凤/                   # 龙 / 凤 / 云纹（红 / 绿，大日期两侧与干支行用）
├── 八卦.png                # 八卦水印素材（中栏底部，20% 透明）
├── 图标/                   # 联系作者图标（GitHub / 哔哩哔哩 / 微博）
├── calendar_app/
│   ├── engine.py           # 农历/宜忌/运势/生肖引擎（两广·港澳宽松口径）
│   ├── agenda_pdf.py       # 行事历：表格/PDF/Word 导入解析、模板生成、区间导出、手写覆写
│   ├── bridge.py           # 钦天监对接接口（预留）
│   ├── process.py          # 进程清理 + 孤儿解包目录自愈清理
│   └── version.py          # 版本信息
├── tools/
│   ├── clean_orphan_mei.py # 一次性回收 %TEMP%\_MEIxxxxxx（默认演练，--apply 才删）
│   └── dev_checks/         # 可复跑的回归脚本（见「开发校验」）
├── dist/                   # 打包产物
├── history/                # 历史版本归档
└── README.md
```
