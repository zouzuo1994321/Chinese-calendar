# -*- coding: utf-8 -*-
"""肆月日历 - 农历 / 宜忌 / 运势引擎。

数据参考：钦天监（正式版）两广·港澳通书（宋韶光 / 永经堂 / 广经堂 宽松口径），
以「建除十二神 + 黄道黑道值神」为正文主干，神煞作加减修正。
底层历法计算使用 lunar-python。
"""

from __future__ import annotations

from datetime import date

from lunar_python import Solar

# --------------------------------------------------------------------------
# 一、建除十二神 → 宜 / 忌（通胜正文主干，引自钦天监通书数据）
# --------------------------------------------------------------------------

ZHIXING_YIJI = {
    "建": (["出行", "赴任", "见贵", "求财", "祈福", "祭祀", "会亲友", "签约", "进人口"],
           ["动土", "开仓", "掘井", "安葬", "诉讼"]),
    "除": (["祭祀", "祈福", "求医", "治病", "扫舍", "解除", "出行", "上任", "疗病"],
           ["嫁娶", "开市", "安葬", "搬床", "栽种"]),
    "满": (["开市", "立券", "交易", "纳财", "祭祀", "祈福", "进人口", "安床", "收纳"],
           ["服药", "栽种", "安葬", "出行", "求医"]),
    "平": (["修饰垣墙", "平治道涂", "嫁娶", "订婚", "纳采", "会亲友",
            "求医", "治病", "解除", "安床", "走访"],
           ["开渠放水", "栽种", "掘井", "行丧", "争讼"]),
    "定": (["祭祀", "祈福", "订婚", "纳采", "嫁娶", "安床", "入学", "定盟",
            "立券", "交易", "纳财", "修造", "动土", "开市", "开业", "扫舍", "清理"],
           ["诉讼", "出行", "交涉", "搬迁", "移徙", "入宅", "乔迁"]),
    "执": (["捕捉", "造屋", "收敛", "纳财", "签约", "立券", "搬迁"],
           ["开市", "出行", "安葬", "动土", "求医", "治病", "探病", "就医"]),
    "破": (["破屋坏垣", "拆卸", "求医", "治病", "解除"],
           ["嫁娶", "开市", "动土", "安葬", "签约", "出行", "求财"]),
    "危": (["安床", "祭祀", "祈福", "会亲友", "出行", "安葬"],
           ["登高", "行船", "搬迁", "开业", "栽种", "嫁娶"]),
    "成": (["开市", "入学", "结婚", "立券", "交易", "纳财", "动土", "修造",
            "安床", "出行", "赴任", "求医", "签约", "会亲友"],
           ["诉讼", "争执", "拆卸"]),
    "收": (["纳财", "进人口", "收账", "讨债", "催款", "栽种", "捕捉",
            "立券", "入学", "讨要旧欠"],
           ["出行", "安葬", "搬迁", "开市", "放水"]),
    "开": (["开市", "动土", "安床", "求医", "入学", "祭祀", "祈福", "会亲友",
            "出行", "乔迁", "搬迁", "签约"],
           ["安葬", "放水", "哭泣", "安床收账"]),
    "闭": (["筑堤", "安葬", "修补", "收纳", "立券", "收敛", "整理", "扫舍",
            "订婚", "纳采", "嫁娶", "交易", "修造"],
           ["开市", "开业", "出行", "远行", "手术", "上任", "开光", "就医",
            "入宅", "移徙", "搬迁", "乔迁", "求人", "见贵", "求官", "求职"]),
}

# --------------------------------------------------------------------------
# 二、黄道 / 黑道值神 → 宜 / 忌
# --------------------------------------------------------------------------

TIANSHEN_YIJI = {
    "青龙": (["嫁娶", "开市", "出行", "会亲友", "动土", "纳财", "立券", "交易",
              "求职", "见贵", "签约", "搬迁"], []),
    "明堂": (["会亲友", "谈判", "签约", "立券", "文书", "见贵", "求职", "出行",
              "商务洽谈"], []),
    "金匮": (["纳财", "开市", "立券", "交易", "收藏", "提现", "收账", "催款",
              "储蓄"], []),
    "天德": (["祈福", "祭祀", "行善", "嫁娶", "会亲友", "求职", "见贵", "和解"], []),
    "玉堂": (["入学", "考试", "上书", "求职", "见贵", "文案", "会亲友", "面试"], []),
    "司命": (["安床", "修造", "祭祀", "入宅", "乔迁", "立券", "交易", "合作",
              "求职", "搬迁", "见贵"], []),
    "天刑": ([], ["诉讼", "争执", "斗殴", "求财"]),
    "朱雀": ([], ["争吵", "签约", "远行", "口舌"]),
    "白虎": ([], ["手术", "丧葬", "冒险", "见血", "出行"]),
    "天牢": ([], ["出行", "求财", "诉讼", "搬迁"]),
    "玄武": ([], ["夜行", "交易", "泄密", "签约"]),
    "勾陈": ([], ["动土", "搬迁", "诉讼", "追讨", "投资", "合伙", "理财"]),
}

HUANG_DAO_SHEN = {"青龙", "明堂", "金匮", "天德", "玉堂", "司命"}

# 建除十二神性质分值（用于整体运势打分）
ZHIXING_SCORE = {"建": 6, "除": 5, "满": 6, "平": 4, "定": 7, "执": 5,
                 "成": 8, "收": 6, "开": 8, "闭": -2, "破": -10, "危": -4}

# --------------------------------------------------------------------------
# 三、生肖关系（合冲派：日支 ↔ 生肖支）
# --------------------------------------------------------------------------

LIU_HE = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
          "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}

SAN_HE_GROUPS = [("申", "子", "辰"), ("亥", "卯", "未"), ("寅", "午", "戌"), ("巳", "酉", "丑")]
SAN_HE_NAME = {("申", "子", "辰"): "水局", ("亥", "卯", "未"): "木局",
               ("寅", "午", "戌"): "火局", ("巳", "酉", "丑"): "金局"}

CHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
         "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}

HAI = [("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"), ("申", "亥"), ("酉", "戌")]

ZHI_SHENGXIAO = {"子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔", "辰": "龙", "巳": "蛇",
                 "午": "马", "未": "羊", "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪"}
SHENGXIAO_ZHI = {v: k for k, v in ZHI_SHENGXIAO.items()}
SHENGXIAO_LIST = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

WEEK_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
WEEK_EN = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
MONTH_EN = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
            "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

# 农历月别称 → 标准月名（用于行事历匹配）
LUNAR_MONTH_ALIAS = {"正": "正", "一": "正", "二": "二", "三": "三", "四": "四", "五": "五",
                     "六": "六", "七": "七", "八": "八", "九": "九", "十": "十",
                     "冬": "冬", "十一": "冬", "腊": "腊", "十二": "腊"}

# --------------------------------------------------------------------------
# 六、吉凶颜色（穿衣五行：大吉=生我者色，次吉=同我者色，不宜=克我者色）
# --------------------------------------------------------------------------

GAN_WUXING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
              "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
WUXING_COLOR = {"木": "青、绿", "火": "红、紫", "土": "黄、棕", "金": "白、金、银", "水": "黑、蓝、灰"}
SHENG_SRC = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}   # 生我者
BE_KE = {"木": "金", "金": "火", "火": "水", "水": "土", "土": "木"}       # 克我者

# --------------------------------------------------------------------------
# 七、法定假日表（2026–2027 常规放假日程，供红色主题触发；其余年份按节日当日识别）
# --------------------------------------------------------------------------

STATUTORY_RANGES = {
    2026: [("元旦", "2026-01-01", "2026-01-03"),
           ("春节", "2026-02-16", "2026-02-22"),
           ("清明节", "2026-04-04", "2026-04-06"),
           ("劳动节", "2026-05-01", "2026-05-05"),
           ("端午节", "2026-06-19", "2026-06-21"),
           ("中秋节", "2026-09-25", "2026-09-27"),
           ("国庆节", "2026-10-01", "2026-10-07")],
    2027: [("元旦", "2027-01-01", "2027-01-03"),
           ("春节", "2027-02-05", "2027-02-11"),
           ("清明节", "2027-04-03", "2027-04-05"),
           ("劳动节", "2027-05-01", "2027-05-05"),
           ("端午节", "2027-06-09", "2027-06-11"),
           ("中秋节", "2027-09-14", "2027-09-16"),
           ("国庆节", "2027-10-01", "2027-10-07")],
}
_STATUTORY_FESTIVAL_NAMES = {"元旦", "国庆节", "劳动节", "春节", "端午节", "中秋节", "清明节"}


def _safe(fn, default="—"):
    try:
        v = fn()
        if v is None or v == "":
            return default
        return v
    except Exception:
        return default


def get_holiday(d: date):
    """若为法定假日返回假名（如「国庆节」），否则 None。"""
    for name, s, e in STATUTORY_RANGES.get(d.year, []):
        try:
            ys, ms, ds = map(int, s.split("-"))
            ye, me, de = map(int, e.split("-"))
            if date(ys, ms, ds) <= d <= date(ye, me, de):
                return name
        except Exception:
            continue
    # 兜底：节日当日识别
    try:
        solar = Solar.fromYmd(d.year, d.month, d.day)
        lunar = solar.getLunar()
        fests = set(solar.getFestivals()) | set(lunar.getFestivals())
        hit = fests & _STATUTORY_FESTIVAL_NAMES
        if hit:
            return sorted(hit)[0]
        if lunar.getJieQi() == "清明":
            return "清明节"
    except Exception:
        pass
    return None


def get_lucky_hours(lunar) -> list:
    """当日黄道吉时列表：[(时辰干支, 时辰名, 值神, 'HH:MM-HH:MM')]。"""
    out = []
    try:
        for t in lunar.getTimes():
            if t.getTianShenLuck() == "吉":
                gz = t.getGanZhi()
                zhi_name = gz[1] + "时"
                out.append((gz, zhi_name, t.getTianShen(),
                            "%s-%s" % (t.getMinHm(), t.getMaxHm())))
    except Exception:
        pass
    return out


def get_lucky_colors(lunar) -> dict:
    """当日穿衣五行吉凶颜色。"""
    try:
        gan = lunar.getDayInGanZhi()[0]
        x = GAN_WUXING.get(gan)
        if not x:
            return {}
        return {
            "大吉": WUXING_COLOR[SHENG_SRC[x]],
            "次吉": WUXING_COLOR[x],
            "不宜": WUXING_COLOR[BE_KE[x]],
        }
    except Exception:
        return {}


def build_advice(info: dict) -> dict:
    """按事业 / 感情 / 出行 / 财务生成当日简明建议（规则版）。"""
    zhixing = info.get("zhixing", "")
    ttype = info.get("tianshen_type", "")
    ts = info.get("tianshen", "")
    yi, ji = set(info.get("yi") or []), set(info.get("ji") or [])
    score = info.get("fortune_score", 50)

    # ---- 事业 ----
    if zhixing in ("成", "开", "定"):
        a = "建除%s日、利推进新事，宜主动汇报、签约立项" % zhixing
    elif zhixing in ("建", "执", "除", "满"):
        a = "建除%s日、按计划推进即可，宜理顺手头事务" % zhixing
    elif zhixing in ("破", "闭"):
        a = "建除%s日、不宜新开大项，宜守成、复盘理旧" % zhixing
    else:
        a = "平日守常，宜按部就班、勿冒进"
    if "签约" in ji or "开市" in ji:
        a += "；今日忌签约开市，重要合同缓一缓"
    if ttype == "黄道":
        a += "（%s%s助势）" % (ts, ttype)

    # ---- 感情 ----
    if "嫁娶" in yi or "订婚" in yi or "不将" in (info.get("jishen") or []):
        g = "情感氛围佳，宜约会、联络、谈婚论嫁"
    elif "嫁娶" in ji:
        g = "情缘平平，宜细水长流，不宜争执翻旧账"
    else:
        g = "情感平稳，宜多沟通陪伴，少猜疑"
    if "六冲" in str(info.get("zodiac_tags", "")) or score < 40:
        g += "；今日易情绪起伏，忍让为先"

    # ---- 出行 ----
    if "出行" in ji or "远行" in ji:
        c = "忌远行奔波，短途尚可，出行留意路况"
    elif "出行" in yi or "赴任" in yi:
        c = "宜出行赴任、外务交涉，路上遇贵几率高"
    else:
        c = "出行平常，出门看天色、返程趁早"
    if "白虎" in (info.get("xiongsha") or []) or "灾煞" in (info.get("xiongsha") or []):
        c += "；凶煞当值，防磕碰意外，勿登高涉水"

    # ---- 财务 ----
    if "纳财" in yi or "收账" in yi or "求财" in yi:
        b = "财路尚通，宜收款、对账、推进回款"
    elif "纳财" in ji or "求财" in ji:
        b = "忌大额支出与投资，捂好钱包"
    else:
        b = "财运平常，量入为出、稳健为上"
    xs = set(info.get("xiongsha") or [])
    if "大耗" in xs or "小耗" in xs:
        b += "；防破小财，勿冲动消费"
    if "五虚" in xs:
        b += "；忌开仓放贷、合伙投钱"

    return {"事业": a, "感情": g, "出行": c, "财务": b}


def _lunar_month_size(lunar) -> bool:
    """农历当月是否为大月（30 天）。lunar-python 无直接接口，用下月初一倒推。"""
    try:
        from lunar_python import Lunar
        # 找本月的天数：从当月初一逐日前进到下月初一
        first = Lunar.fromYmd(lunar.getYear(), abs(lunar.getMonth()), 1)
        day = first
        for i in range(1, 32):
            day = day.next(1)
            if abs(day.getMonth()) != abs(first.getMonth()) or day.getYear() != first.getYear():
                return i >= 30
        return False
    except Exception:
        return True


# --------------------------------------------------------------------------
# 四、当日排盘
# --------------------------------------------------------------------------

def get_day_info(d: date) -> dict:
    """取某公历日期的完整通胜信息。"""
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()

    zhixing = _safe(lunar.getZhiXing, "平")
    tianshen = _safe(lunar.getDayTianShen, "—")
    tianshen_type = _safe(lunar.getDayTianShenType, "—")   # 黄道 / 黑道
    tianshen_luck = _safe(lunar.getDayTianShenLuck, "—")
    jishen = _safe(lunar.getDayJiShen, [])
    xiongsha = _safe(lunar.getDayXiongSha, [])
    strict_yi = _safe(lunar.getDayYi, [])
    strict_ji = _safe(lunar.getDayJi, [])

    # ---- 宽松口径宜忌合成（两广·港澳通书） ----
    score = {}
    w_zx, w_ts, w_shen, w_sha = 3.0, 2.5, 1.2, 1.6

    def add(items, weight):
        for it in (items or []):
            if it:
                score[it] = score.get(it, 0.0) + weight

    zx_yj = ZHIXING_YIJI.get(zhixing, ([], []))
    add(zx_yj[0], w_zx)
    add(zx_yj[1], -w_zx)
    ts_yj = TIANSHEN_YIJI.get(tianshen, ([], []))
    add(ts_yj[0], w_ts)
    add(ts_yj[1], -w_ts)
    add([s for s in jishen if s in HUANG_DAO_SHEN or s in ("天德", "月德", "三合", "六合", "母仓", "不将")], w_shen)
    add(xiongsha, -w_sha)

    yi = [k for k, v in score.items() if v >= 2.4]
    ji = [k for k, v in score.items() if v <= -2.4]
    yi.sort(key=lambda x: -score[x])
    ji.sort(key=lambda x: score[x])
    if not yi:
        yi = strict_yi[:6]
    if not ji:
        ji = strict_ji[:6]

    # ---- 整体运势打分 ----
    fs = 55.0
    fs += ZHIXING_SCORE.get(zhixing, 0)
    fs += 12.0 if tianshen in HUANG_DAO_SHEN else -8.0
    fs += min(len(jishen), 6) * 1.5 - min(len(xiongsha), 6) * 1.5
    fs = max(5, min(98, round(fs)))
    if fs >= 78:
        grade, grade_tip = "上吉", "诸事易成，宜把握良机、积极进取"
    elif fs >= 64:
        grade, grade_tip = "吉", "大体顺遂，宜按计划推进要事"
    elif fs >= 50:
        grade, grade_tip = "平", "平顺无奇，宜守常、理旧务"
    elif fs >= 36:
        grade, grade_tip = "凶", "暗藏阻滞，宜守不宜攻、谨慎行事"
    else:
        grade, grade_tip = "大凶", "诸事宜守，宜静养、避争端、勿举大事"

    # ---- 节气 ----
    jieqi = _safe(lunar.getJieQi, "")
    if not jieqi:
        try:
            jieqi = lunar.getNextJieQi().getName() + "（将至）"
        except Exception:
            jieqi = "—"

    leap = lunar.getMonth() < 0
    month_cn = lunar.getMonthInChinese()
    info = {
        "date": d,
        "week_cn": WEEK_CN[d.weekday()],
        "week_en": WEEK_EN[d.weekday()],
        "month_en": MONTH_EN[d.month - 1],
        "lunar_year_cn": lunar.getYearInGanZhi(),
        "lunar_year_shengxiao": lunar.getYearShengXiao(),
        "lunar_month_cn": ("闰" if leap else "") + month_cn + "月",
        "lunar_month_plain": month_cn,          # 农历月名（无闰字，用于匹配行事历）
        "lunar_day_cn": lunar.getDayInChinese(),
        "lunar_month_size": ("大" if _lunar_month_size(lunar) else "小"),
        "year_ganzhi": lunar.getYearInGanZhi(),
        "month_ganzhi": lunar.getMonthInGanZhi(),
        "day_ganzhi": lunar.getDayInGanZhi(),
        "day_shengxiao": lunar.getDayShengXiao(),
        "day_zhi": lunar.getDayInGanZhi()[-1],
        "jieqi": jieqi,
        "zhixing": zhixing,
        "tianshen": tianshen,
        "tianshen_type": tianshen_type,
        "tianshen_luck": tianshen_luck,
        "jishen": jishen,
        "xiongsha": xiongsha,
        "yi": yi[:10],
        "ji": ji[:10],
        "lu": _safe(lunar.getDayLu, "—"),
        "chong": _safe(lunar.getDayChongDesc, "—"),
        "pos_cai": _safe(lunar.getDayPositionCaiDesc, "—"),
        "pos_xi": _safe(lunar.getDayPositionXiDesc, "—"),
        "pos_fu": _safe(lunar.getDayPositionFuDesc, "—"),
        "pos_tai": _safe(lunar.getDayPositionTai, "—"),
        "fortune_score": fs,
        "fortune_grade": grade,
        "fortune_tip": grade_tip,
    }
    # 扩展：法定假日 / 吉时 / 吉凶颜色 / 分项建议 / 箴言谶言
    info["holiday"] = get_holiday(d)
    info["lucky_hours"] = get_lucky_hours(lunar)
    info["lucky_colors"] = get_lucky_colors(lunar)
    info["advice"] = build_advice(info)
    info["wisdom"] = get_daily_wisdom(d)
    return info


# --------------------------------------------------------------------------
# 五、生肖当日运势（合冲派，参考钦天监 zodiac.py）
# --------------------------------------------------------------------------

def analyze_zodiac_day(info: dict, shengxiao: str) -> dict:
    """分析指定生肖在本日的运势。"""
    zhi = SHENGXIAO_ZHI.get(shengxiao)
    if not zhi:
        return {"tags": ["—"], "score": info["fortune_score"], "text": "请选择有效生肖。", "tips": []}

    day_zhi = info["day_zhi"]
    tags, tips = [], []

    if zhi == day_zhi:
        tags.append("值日")
        tips.append("与本日地支同气，气场相合，宜顺势而为、稳中求进")

    if LIU_HE.get(zhi) == day_zhi or LIU_HE.get(day_zhi) == zhi:
        tags.append("六合")
        tips.append("与日支六合，人和气顺，易得贵人助力")

    san_group = next((g for g in SAN_HE_GROUPS if zhi in g and day_zhi in g), None)
    if san_group:
        tags.append("三合" + SAN_HE_NAME[san_group])
        tips.append("与日支三合%s，气势相投、合力成事" % SAN_HE_NAME[san_group])

    if CHONG.get(zhi) == day_zhi:
        tags.append("六冲")
        tips.append("与日支六冲，动中生变，情绪与行程易起伏，大事缓议")

    if (zhi, day_zhi) in HAI or (day_zhi, zhi) in HAI:
        tags.append("六害")
        tips.append("与日支六害，暗中小人使绊、细事相扰，谨防口舌")

    xing_pairs = [("子", "卯"), ("寅", "巳"), ("巳", "申"), ("丑", "戌"), ("戌", "未")]
    self_xing = {"辰", "午", "酉", "亥"}
    if (zhi, day_zhi) in xing_pairs or (day_zhi, zhi) in xing_pairs:
        tags.append("相刑")
        tips.append("与日支相刑， friction 易起，忍让为先，不宜争执硬顶")
    if zhi == day_zhi and zhi in self_xing:
        tags.append("自刑")
        tips.append("值日且自刑，易自寻烦恼，放宽心、不钻牛角尖")

    if not tags:
        tags.append("中性")
        tips.append("与日支无刑合冲害，平常心度过，按部就班即可")

    # 生肖分 = 日整体分 + 关系修正
    adj = 0.0
    for t in tags:
        if t.startswith("三合") or t == "六合":
            adj += 12
        elif t == "值日":
            adj += 6
        elif t == "六冲":
            adj -= 15
        elif t == "六害":
            adj -= 10
        elif t in ("相刑", "自刑"):
            adj -= 8
    zscore = max(5, min(98, round(info["fortune_score"] + adj)))

    text = "%s日（%s）见%s：%s。今日冲煞：%s。" % (
        info["day_ganzhi"], info["day_shengxiao"], shengxiao,
        "、".join(tags), info["chong"])
    return {"tags": tags, "score": zscore, "text": text, "tips": tips}


# --------------------------------------------------------------------------
# 六、每日箴言 / 谶言（与钦天监 page_today 同源口径，按日期种子取当日）
# --------------------------------------------------------------------------

WISDOM_MAXIMS = [
    "君子务本，本立而道生。",
    "天行健，君子以自强不息；地势坤，君子以厚德载物。",
    "知者不惑，仁者不忧，勇者不惧。",
    "静坐常思己过，闲谈莫论人非。",
    "积善之家必有余庆，积不善之家必有余殃。",
    "凡事预则立，不预则废。",
    "大道至简，衍化至繁；返璞归真，抱元守一。",
    "上善若水，水利万物而不争。",
    "祸兮福所倚，福兮祸所伏。",
    "不以物喜，不以己悲。",
    "千里之行，始于足下。",
    "海纳百川，有容乃大；壁立千仞，无欲则刚。",
    "博学之，审问之，慎思之，明辨之，笃行之。",
    "工欲善其事，必先利其器。",
    "学而不思则罔，思而不学则殆。",
    "三人行，必有我师焉。",
    "天将降大任于斯人也，必先苦其心志，劳其筋骨。",
    "非淡泊无以明志，非宁静无以致远。",
    "行有不得，反求诸己。",
    "君子坦荡荡，小人长戚戚。",
    "见贤思齐焉，见不贤而内自省也。",
    "温故而知新，可以为师矣。",
    "敏而好学，不耻下问。",
    "人无远虑，必有近忧。",
    "德不孤，必有邻。",
    "满招损，谦受益。",
    "锲而舍之，朽木不折；锲而不舍，金石可镂。",
    "路漫漫其修远兮，吾将上下而求索。",
    "穷且益坚，不坠青云之志。",
    "莫愁前路无知己，天下谁人不识君。",
    "山重水复疑无路，柳暗花明又一村。",
]

OMENS = [
    "今日宜静心养气，不宜急进。",
    "财气在东南，利出行与洽谈。",
    "口舌须防，谨言慎行为上。",
    "贵人近在咫尺，稍加留意便可得助。",
    "今日利于文书契约，签约为宜。",
    "阴气渐长，宜早归休整，勿贪晚景。",
    "阳气正盛，宜主动出击，把握时机。",
    "今日利静不利动，守成为要。",
    "远方有信至，或遇故人重逢。",
    "小人是非暗生，宽怀以待自可化解。",
    "今日五行相合，百事皆顺遂。",
    "宜祭祀祖先、敬奉神明，可得庇佑。",
    "今日利迁移变动，不宜固守成规。",
    "桃花暗动，单身者宜主动，已婚者宜珍惜。",
    "财星高照但易散，收入宜及时储蓄。",
    "今日宜结交新友，拓展人脉为上策。",
    "病气潜伏，宜调饮食、适运动以为防。",
    "文昌当值，学子宜勤读，考运亨通。",
    "官非口舌之兆，忍让三分退一步海阔天空。",
    "家宅安宁，宜整理居室、调和六亲。",
    "失物有望寻回，多往西北方向留意。",
]


def get_daily_wisdom(d: date) -> dict:
    """按日期种子返回当日箴言（修身格言）与谶言（当日征兆）。"""
    ymd = "%04d%02d%02d" % (d.year, d.month, d.day)
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(ymd))
    return {"zhenyan": WISDOM_MAXIMS[seed % len(WISDOM_MAXIMS)],
            "chenyan": OMENS[(seed + 7) % len(OMENS)]}


# --------------------------------------------------------------------------
# 八字排盘与每日推演（v1.3.0）
# --------------------------------------------------------------------------
GAN_HE = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙",
          "丙": "辛", "辛": "丙", "丁": "壬", "壬": "丁",
          "戊": "癸", "癸": "戊"}                                   # 天干五合
GAN_CHONG_PAIRS = [("甲", "庚"), ("庚", "甲"), ("乙", "辛"), ("辛", "乙"),
                   ("丙", "壬"), ("壬", "丙"), ("丁", "癸"), ("癸", "丁")]
ZHI_XING_PAIRS = [("子", "卯"), ("卯", "子"), ("寅", "巳"), ("巳", "寅"),
                  ("巳", "申"), ("申", "巳"), ("丑", "戌"), ("戌", "丑"),
                  ("戌", "未"), ("未", "戌")]
_BAZI_ADJ = {"干合": 8, "支六合": 8, "今日生我": 6, "我克为财": 4,
             "生肖六合": 6, "生肖三合": 6, "比和": 3,
             "干冲": -8, "支六冲": -10, "今日克我": -6,
             "支六害": -5, "支相刑": -5, "生肖六冲": -8}


def compute_eightchar(year, month, day, hour=None, lunar_mode=False):
    """按出生年月日（公历/农历）+ 可选 24h 小时排四柱。

    :return: {"pillars": [年柱, 月柱, 日柱, 时柱], "shengxiao": 年支生肖}
    """
    from lunar_python import Solar, Lunar
    # 日柱统一按当日 12 点排，避免 23 点子时换日歧义
    if lunar_mode:
        lunar = Lunar.fromYmdHms(int(year), int(month), int(day), 12, 0, 0)
    else:
        lunar = Solar.fromYmdHms(int(year), int(month), int(day), 12, 0, 0).getLunar()
    ec = lunar.getEightChar()
    pillars = [ec.getYear(), ec.getMonth(), ec.getDay(), ""]
    if hour is not None:
        if lunar_mode:
            lh = Lunar.fromYmdHms(int(year), int(month), int(day), int(hour), 0, 0)
        else:
            lh = Solar.fromYmdHms(int(year), int(month), int(day), int(hour), 0, 0).getLunar()
        pillars[3] = lh.getTimeInGanZhi()
    sx = ZHI_SHENGXIAO.get(pillars[0][-1], "") if pillars[0] else ""
    return {"pillars": pillars, "shengxiao": sx}


def bazi_day_report(bazi: dict, info: dict):
    """用户八字 vs 当日干支的推演报告（运势带强化用）。

    :return: {"tags": [...], "score": int, "text": 一行摘要, "tips": [...],
              "shengxiao": 八字年支生肖} 或 None（八字无效）
    """
    pillars = (bazi or {}).get("pillars") or []
    if len(pillars) < 3 or not pillars[2] or len(pillars[2]) < 2:
        return None
    u_gan, u_zhi = pillars[2][0], pillars[2][-1]
    u_wx = GAN_WUXING.get(u_gan)
    d_gan = info["day_ganzhi"][0]
    d_zhi = info["day_zhi"]
    d_wx = GAN_WUXING.get(d_gan)
    tags, tips = [], []

    # —— 日干 vs 今日天干（五合 / 相冲 / 五行生克）——
    if GAN_HE.get(u_gan) == d_gan:
        tags.append("干合")
        tips.append("你的日干%s与今日%s五合，缘分成事，宜签约合作、拜见贵人" % (u_gan, d_gan))
    elif (u_gan, d_gan) in GAN_CHONG_PAIRS:
        tags.append("干冲")
        tips.append("你的日干%s与今日%s相冲，易有口舌与变动，缓签约定、少争执" % (u_gan, d_gan))
    if u_wx and d_wx and u_wx != d_wx:
        if SHENG_SRC.get(u_wx) == d_wx:
            tags.append("今日生我")
            tips.append("今日%s生你的%s，得扶助滋养，宜学习求助、补给身心" % (d_wx, u_wx))
        elif BE_KE.get(u_wx) == d_wx:
            tags.append("今日克我")
            tips.append("今日%s克你的%s，压力偏大，防硬碰硬，稳字当头" % (d_wx, u_wx))
        elif SHENG_SRC.get(d_wx) == u_wx:
            tags.append("我生泄秀")
            tips.append("你的%s生今日%s，付出偏多，量力而行、忌大额投入" % (u_wx, d_wx))
        elif BE_KE.get(d_wx) == u_wx:
            tags.append("我克为财")
            tips.append("你的%s克今日%s，可控可取，宜推进实务、理财追款" % (u_wx, d_wx))
    elif u_wx and d_wx:
        tags.append("比和")
        tips.append("你的日主%s与今日%s同气，气场相投，宜顺势而为" % (u_wx, d_wx))

    # —— 用户日支 vs 今日地支 ——
    if LIU_HE.get(u_zhi) == d_zhi or LIU_HE.get(d_zhi) == u_zhi:
        tags.append("支六合")
        tips.append("你的日支%s与今日%s六合，人和运通，宜约会谈判、结盟协作" % (u_zhi, d_zhi))
    if CHONG.get(u_zhi) == d_zhi:
        tags.append("支六冲")
        tips.append("你的日支%s与今日%s六冲，行程易变、情绪起伏，大事缓议" % (u_zhi, d_zhi))
    if (u_zhi, d_zhi) in HAI or (d_zhi, u_zhi) in HAI:
        tags.append("支六害")
        tips.append("你的日支%s与今日%s六害，防小人暗扰与口舌是非" % (u_zhi, d_zhi))
    if (u_zhi, d_zhi) in ZHI_XING_PAIRS or (d_zhi, u_zhi) in ZHI_XING_PAIRS:
        tags.append("支相刑")
        tips.append("你的日支%s与今日%s相刑，摩擦易起，忍让为先、不宜争执" % (u_zhi, d_zhi))

    # —— 年支生肖 vs 今日地支（沿用生肖合冲口径）——
    y_sx = ZHI_SHENGXIAO.get(pillars[0][-1])
    if y_sx:
        y_zhi = SHENGXIAO_ZHI[y_sx]
        if LIU_HE.get(y_zhi) == d_zhi or LIU_HE.get(d_zhi) == y_zhi:
            tags.append("生肖六合")
            tips.append("你的生肖%s与今日六合，贵人运旺" % y_sx)
        if CHONG.get(y_zhi) == d_zhi:
            tags.append("生肖六冲")
            tips.append("你的生肖%s与今日六冲，谨慎出行、注意安全" % y_sx)
        g = next((gr for gr in SAN_HE_GROUPS if y_zhi in gr and d_zhi in gr), None)
        if g:
            tags.append("生肖三合")
            tips.append("你的生肖%s与今日三合%s，合力成事" % (y_sx, SAN_HE_NAME[g]))

    if not tags:
        tags.append("平")
        tips.append("八字与今日干支无刑合冲害，平常心度过，按部就班即可")

    adj = sum(_BAZI_ADJ.get(t, 0) for t in tags)
    score = max(5, min(98, int(info["fortune_score"] * 0.5 + 50 + adj)))
    wx_txt = "（%s命）" % u_wx if u_wx else ""
    text = "日主%s%s ｜ %s" % (pillars[2], wx_txt, "、".join(tags[:4]))
    return {"tags": tags, "score": score, "text": text, "tips": tips,
            "shengxiao": y_sx or ""}
