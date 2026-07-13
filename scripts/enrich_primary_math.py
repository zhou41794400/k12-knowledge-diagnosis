from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树" / "数学" / "小学"

# 每项均需人工定义，禁止从标题自动生成后直接视为已完成内容。
CONTENT: dict[str, tuple[list[str], str]] = {
    "MATH-PRI-G2-GG-001": (["直角", "直角符号", "判断直角"], "观察课桌角、书本角和校园门窗角，用三角尺判断哪些角是直角。"),
    "MATH-PRI-G2-GG-002": (["观察物体", "不同方向观察", "看到的形状"], "从前面、侧面和上面观察牛奶盒或积木组合，选择对应看到的图形。"),
    "MATH-PRI-G2-GG-003": (["图形拼组", "七巧板", "平面图形组合"], "用七巧板拼出长城烽火台或小房子图案，并说明使用了哪些基本图形。"),
    "MATH-PRI-G3-GG-004": (["三角形", "三角形的边和角", "三角形分类"], "观察自行车车架、屋顶支架等三角形结构，辨认三条边和三个角。"),
    "MATH-PRI-G3-GG-005": (["平移", "旋转", "图形运动"], "观察电梯门开合、推拉窗和风车转动，判断属于平移还是旋转。"),
    "MATH-PRI-G3-GG-006": (["图形分类", "图形特征比较", "按边角分类"], "把校园标识中的三角形、长方形、正方形和圆按边、角等特征分类。"),
    "MATH-PRI-G3-NS-004": (["时分秒", "时间单位换算", "经过时间"], "根据石家庄公交到站和发车时刻，计算候车或行程经过的分钟数。"),
    "MATH-PRI-G3-NS-005": (["万以内加减法", "三位数加减", "加减法应用"], "根据社区图书角两周借阅册数，计算总数、相差数并验算。"),
    "MATH-PRI-G3-NS-006": (["有余数除法", "余数", "余数小于除数"], "把采摘的鸭梨按每盒固定个数装箱，计算能装满几盒、还剩几个。"),
    "MATH-PRI-G3-STP-001": (["数据收集", "数据整理", "统计记录"], "调查班级同学选择步行、公交或家长接送的上学方式，整理并比较人数。"),
    "MATH-PRI-G3-STP-002": (["平均数", "平均水平", "移多补少"], "比较小组连续几天收集废纸的平均数量，用移多补少解释平均数。"),
    "MATH-PRI-G4-GG-001": (["角的度量", "量角器", "角的度数"], "使用量角器测量校园道路转弯示意图中的角，并比较角的大小。"),
    "MATH-PRI-G4-GG-002": (["平行四边形", "梯形", "平行线"], "在伸缩门、梯子和桥梁护栏图片中辨认平行四边形与梯形，并说明特征。"),
    "MATH-PRI-G4-GG-003": (["位置与方向", "方向和距离", "路线描述"], "以学校为观测点，根据方向和距离描述图书馆、体育馆或公交站的位置。"),
    "MATH-PRI-G4-NS-001": (["大数的认识", "多位数读写", "大数改写"], "读取河北省城市人口或公共图书馆藏书等大数，完成读写、比较和近似表示。"),
    "MATH-PRI-G4-NS-002": (["三位数乘两位数", "乘法竖式", "积的估算"], "按旅游大巴每车人数和车辆数量，估算并计算研学活动可容纳的总人数。"),
    "MATH-PRI-G4-NS-003": (["除数是两位数", "除法竖式", "商的试算"], "把一批图书平均分到若干班级，使用两位数除法求每班册数和余数。"),
    "MATH-PRI-G4-NS-004": (["四则运算", "运算律", "简便计算"], "计算社区采购多种物资的总价，选择交换律、结合律或分配律进行简便计算。"),
    "MATH-PRI-G4-NS-005": (["小数的意义", "小数大小比较", "小数加减"], "读取超市商品以元为单位的价格或体温数据，比较小数并完成简单加减。"),
    "MATH-PRI-G4-STP-001": (["条形统计图", "统计图读数", "数据比较"], "根据一周空气质量等级或校园运动项目人数绘制条形统计图并回答问题。"),
    "MATH-PRI-G4-PRA-001": (["沏茶问题", "合理安排时间", "流程优化"], "安排烧水、洗杯、取茶叶等可同时或依次进行的任务，求完成全部任务的最短时间。"),
    "MATH-PRI-G4-PRA-002": (["田忌赛马", "对策问题", "最优策略"], "设计班级三局两胜的跳绳出场顺序，比较不同安排并说明获胜策略。"),
    "MATH-PRI-G5-GG-001": (["多边形面积", "平行四边形面积", "三角形梯形面积"], "计算校园花坛、菜地或宣传栏中平行四边形、三角形和梯形区域的面积。"),
    "MATH-PRI-G5-GG-002": (["长方体正方体", "表面积", "体积"], "用快递纸箱或牛奶包装盒测量长宽高，计算表面积或容积并比较包装方案。"),
    "MATH-PRI-G5-NS-001": (["小数乘法", "小数乘整数", "积的小数位数"], "根据苹果或鸭梨的每千克单价和质量，计算购买总价并检查小数点位置。"),
    "MATH-PRI-G5-NS-002": (["小数除法", "商的小数点", "循环小数"], "把购买文具的总价按数量平均分配，计算单价并按实际需要取近似值。"),
    "MATH-PRI-G5-NS-003": (["简易方程", "用字母表示数", "解方程"], "根据公交票价、人数和总费用之间的关系列简易方程并求未知数。"),
    "MATH-PRI-G5-NS-004": (["分数的意义", "分数单位", "约分通分"], "把一块试验田或一箱水果平均分配，用分数表示其中一部分并比较大小。"),
    "MATH-PRI-G5-NS-005": (["分数加减法", "异分母分数", "通分计算"], "把一周中阅读、运动等活动占用时间用分数表示，计算合计或相差部分。"),
    "MATH-PRI-G5-STP-001": (["可能性", "随机现象", "可能性大小"], "用抽取不同颜色的冬奥主题卡片进行试验，比较各种结果发生的可能性。"),
    "MATH-PRI-G5-STP-002": (["折线统计图", "变化趋势", "复式折线统计图"], "根据石家庄某周气温数据绘制折线统计图，描述升降变化和趋势。"),
    "MATH-PRI-G5-PRA-001": (["植树问题", "间隔数", "两端是否植树"], "为校园道路或社区绿化带安排树木，区分两端都栽、只栽一端和封闭路线。"),
    "MATH-PRI-G5-PRA-002": (["数学建模", "数量关系", "方案比较"], "为班级研学活动建立人数、车辆和费用模型，比较不同包车方案。"),
    "MATH-PRI-G6-GG-001": (["圆的认识", "半径直径", "圆的周长面积"], "测量自行车轮、井盖或圆形花坛，研究半径、直径、周长和面积的关系。"),
    "MATH-PRI-G6-GG-002": (["圆柱", "圆锥", "圆柱圆锥体积"], "把饮料罐、粮仓模型和漏斗抽象为圆柱或圆锥，计算表面积或体积。"),
    "MATH-PRI-G6-NS-001": (["分数乘法", "分数乘整数", "求一个数的几分之几"], "根据一块菜地各区域所占分数，计算某类蔬菜种植面积。"),
    "MATH-PRI-G6-NS-002": (["分数除法", "分数除以整数", "已知几分之几求总量"], "已知图书角某类书占总数的分数和实际册数，求图书总数。"),
    "MATH-PRI-G6-NS-003": (["比", "比例", "正比例反比例"], "按比例调配劳动实践用营养土，或根据地图比例尺计算两地实际距离。"),
    "MATH-PRI-G6-NS-004": (["百分数", "百分率", "折扣与增长率"], "读取超市折扣、出勤率或绿化率，计算百分数并解释结果含义。"),
    "MATH-PRI-G6-NS-005": (["负数", "正数负数", "数轴表示"], "读取河北冬季气温或地面以上、以下高度，用正负数表示并比较大小。"),
    "MATH-PRI-G6-STP-001": (["扇形统计图", "部分占总体", "百分比读图"], "用扇形统计图表示家庭一周支出或班级运动项目选择比例，并计算对应数量。"),
    "MATH-PRI-G6-PRA-001": (["鸽巢原理", "抽屉原理", "至少有几个"], "分析班级同学生日月份或书本存放格，判断至少有若干对象落入同一类。"),
    "MATH-PRI-G6-PRA-002": (["综合问题解决", "多步骤应用题", "方案设计"], "综合人数、路程、时间和费用，为河北省内研学活动设计并比较可行方案。"),
}


def metadata_value(text: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def main() -> None:
    paths: dict[str, Path] = {}
    for path in KNOWLEDGE_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if metadata_value(text, "mastery_granularity") != "knowledge_point":
            continue
        code = metadata_value(text, "point_code")
        if code in CONTENT:
            paths[code] = path

    missing = sorted(set(CONTENT) - set(paths))
    if missing:
        raise SystemExit(f"未找到知识卡：{', '.join(missing)}")
    if len(CONTENT) != 43:
        raise SystemExit(f"预期 43 张知识卡，实际映射 {len(CONTENT)} 张")

    changed = 0
    for code, (keywords, example) in CONTENT.items():
        path = paths[code]
        text = path.read_text(encoding="utf-8")
        if metadata_value(text, "status") != "draft":
            raise SystemExit(f"拒绝修改非草稿知识卡：{code}")
        has_keywords = "matching_keywords:" in text
        has_example = "## 河北生活化例题方向" in text
        if has_keywords and has_example:
            continue
        if has_keywords or has_example:
            raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{code}")
        keyword_block = "matching_keywords:\n" + "".join(f"  - {keyword}\n" for keyword in keywords)
        text = text.replace("mastery_granularity: knowledge_point\n", f"mastery_granularity: knowledge_point\n{keyword_block}", 1)
        example_block = f"## 河北生活化例题方向\n\n> [!example] 例题方向\n> {example}\n\n"
        if "## 课标依据\n" not in text:
            raise SystemExit(f"缺少课标依据段落：{code}")
        text = text.replace("## 课标依据\n", f"{example_block}## 课标依据\n", 1)
        text = re.sub(r"^updated:\s*.+$", "updated: 2026-07-13", text, count=1, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
        changed += 1
    print(f"本次补充 {changed} 张；小学二至六年级目标草稿卡共 {len(CONTENT)} 张")


if __name__ == "__main__":
    main()
