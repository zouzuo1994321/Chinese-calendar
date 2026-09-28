# -*- coding: utf-8 -*-
"""肆月日历 - 钦天监对接接口（预留）。

为后续与《钦天监 (QinTianJian)》桌面应用（两广·港澳通书、八字命盘、
生肖运势等模块）对接预留统一入口。对接方式规划：

  方式 A（源码级）：把钦天监项目目录加入 sys.path，直接导入
      qintianjian.core.calendar_day.DayReport / qintianjian.core.zodiac
      获得更精细的排盘与文案 —— 检测到环境可用时 get_day_report 自动切换。
  方式 B（文件级）：读取钦天监导出的 JSON 通胜数据（预留 data_dir）。
  方式 C（进程级）：未来通过本地 socket / 命令行调用钦天监 exe（预留）。

当前版本：日历软件内置 engine.py 精简引擎，口径与钦天监一致
（两广·港澳通书宽松口径），接口签名保持稳定，未来切换无感。
"""

from __future__ import annotations

import os
import sys
from datetime import date

# 钦天监默认安装位置（按需调整）
QINTIANJIAN_DIR = r"E:\【01】自研软件\【26-15】钦天监（正式版）"


class QinTianJianBridge:
    """钦天监对接桥。所有方法均为无副作用查询。"""

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or QINTIANJIAN_DIR
        self._available = None

    def is_available(self) -> bool:
        """探测钦天监源码包是否可直接导入。"""
        if self._available is None:
            pkg = os.path.join(self.data_dir, "qintianjian")
            self._available = os.path.isdir(pkg)
        return self._available

    def _ensure_path(self):
        if self.data_dir not in sys.path:
            sys.path.insert(0, self.data_dir)

    def get_day_report(self, d: date = None) -> dict:
        """获取当日完整通胜报告。

        若钦天监可用，优先调用其 DayReport（方式 A）；
        否则回退到本软件内置引擎（口径一致）。
        :return: {"source": "qintianjian" | "builtin", "report": {...}}
        """
        d = d or date.today()
        if self.is_available():
            try:
                self._ensure_path()
                from lunar_python import Solar
                from qintianjian.core.calendar_day import build_report  # noqa
                lunar = Solar.fromYmd(d.year, d.month, d.day).getLunar()
                rep = build_report(lunar)
                return {"source": "qintianjian", "report": rep}
            except Exception:
                pass
        from calendar_app.engine import get_day_info
        return {"source": "builtin", "report": get_day_info(d)}

    def get_zodiac_report(self, shengxiao: str, d: date = None) -> dict:
        """获取指定生肖当日运势（预留：未来切换钦天监 analyze_zodiac 多派择优）。"""
        from calendar_app.engine import get_day_info, analyze_zodiac_day
        info = get_day_info(d or date.today())
        return analyze_zodiac_day(info, shengxiao)


# 全局单例，主界面直接使用
BRIDGE = QinTianJianBridge()
