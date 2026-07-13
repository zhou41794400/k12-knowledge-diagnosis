from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树" / "数学"

CONTENT: dict[str, tuple[list[str], str]] = {
    "MATH-JHS-G7-GG-001": (["几何图形", "线段射线直线", "角的比较"], "从校园道路、建筑轮廓和指示牌中抽象点、线、角及基本几何图形。"),
    "MATH-JHS-G7-GG-002": (["三角形", "三角形内角和", "三角形三边关系"], "利用桥梁或屋架示意图判断三角形构成条件，并计算未知角。"),
    "MATH-JHS-G7-NS-001": (["有理数", "数轴", "有理数运算"], "用河北冬季气温、海拔相对高度等数据表示正负数并完成有理数运算。"),
    "MATH-JHS-G7-NS-002": (["整式", "合并同类项", "整式加减"], "用字母表示研学活动人数与费用，化简整式并解释各项含义。"),
    "MATH-JHS-G7-NS-003": (["一元一次方程", "解方程", "方程应用题"], "根据石家庄公交或场馆票价与总费用列一元一次方程求人数。"),
    "MATH-JHS-G7-NS-004": (["二元一次方程组", "代入消元", "加减消元"], "根据两类门票数量和总价列二元一次方程组，求不同票种数量。"),
    "MATH-JHS-G7-NS-005": (["一元一次不等式", "不等式组", "不等式解集"], "根据车辆载客量或活动预算上限建立不等式，确定可行人数范围。"),
    "MATH-JHS-G7-STP-001": (["数据收集", "频数分布", "抽样调查"], "调查班级学生通勤方式，设计抽样、整理频数并选择合适统计图。"),
    "MATH-JHS-G8-GG-001": (["全等三角形", "全等判定", "全等三角形性质"], "在桥梁支架或对称屋架图中寻找全等三角形，并说明判定依据。"),
    "MATH-JHS-G8-GG-002": (["等腰三角形", "直角三角形", "勾股定理"], "根据建筑斜撑或道路里程示意图，运用等腰三角形性质或勾股定理求长度。"),
    "MATH-JHS-G8-GG-003": (["平行四边形", "矩形菱形正方形", "特殊平行四边形判定"], "从伸缩门、窗框和地砖图案中辨认特殊平行四边形并完成判定。"),
    "MATH-JHS-G8-GG-004": (["一次函数", "一次函数图象", "函数增减性"], "建立出租车费用或蓄水量随时间变化的一次函数，解释图象斜率和截距。"),
    "MATH-JHS-G8-NS-001": (["整式乘除", "乘法公式", "因式分解"], "用矩形场地面积变化解释乘法公式，并用因式分解处理面积关系。"),
    "MATH-JHS-G8-NS-002": (["分式", "分式方程", "分式化简"], "用路程、速度和时间关系建立分式或分式方程，求研学车辆速度。"),
    "MATH-JHS-G8-NS-003": (["二次根式", "根式化简", "二次根式运算"], "根据正方形广场或矩形展板的面积求边长，并化简二次根式。"),
    "MATH-JHS-G8-NS-004": (["一元二次方程", "配方法", "求根公式"], "根据矩形菜地面积和边长关系列一元二次方程，筛选符合实际的解。"),
    "MATH-JHS-G8-STP-001": (["平均数中位数众数", "方差", "数据分析"], "比较河北两地一段时间的气温或降水数据，用集中趋势和波动程度作判断。"),
    "MATH-JHS-G9-GG-001": (["图形旋转", "圆的性质", "圆周角"], "分析风车叶片旋转或圆形广场设计图，解决旋转中心、圆心角和圆周角问题。"),
    "MATH-JHS-G9-GG-002": (["相似三角形", "相似判定", "相似比"], "利用同一时刻物体影长测量校园旗杆或古塔模型高度，建立相似比例。"),
    "MATH-JHS-G9-GG-003": (["解直角三角形", "锐角三角函数", "仰角俯角"], "根据观测点到建筑物的距离和仰角，计算建筑物高度并说明测量误差。"),
    "MATH-JHS-G9-GG-004": (["三视图", "投影", "由视图判断几何体"], "根据正投影绘制石雕或建筑模型的主视图、俯视图和左视图。"),
    "MATH-JHS-G9-NS-001": (["二次函数", "抛物线", "二次函数最值"], "把拱桥轮廓或喷泉水柱近似为抛物线，分析顶点、对称轴和高度。"),
    "MATH-JHS-G9-NS-002": (["反比例函数", "反比例函数图象", "反比例关系"], "研究固定路程下速度与时间的关系，建立反比例函数并解释图象。"),
    "MATH-JHS-G9-STP-001": (["概率", "列表法树状图", "频率估计概率"], "通过抽取不同颜色活动卡片或转盘试验，用列表法或树状图计算概率。"),
    "MATH-JHS-G9-PRA-001": (["中考数学综合", "函数几何综合", "分类讨论"], "综合河北生活数据设计代数、函数、几何和统计相结合的问题，明确分步证据。"),
    "MATH-SHS-G10-PRE-001": (["集合", "充分必要条件", "全称量词存在量词"], "用选课、社团参与条件表示集合关系，并判断命题的充分性和必要性。"),
    "MATH-SHS-G10-PRE-002": (["一元二次不等式", "二次函数与方程", "不等式解集"], "根据场地面积或收益限制建立一元二次不等式，求满足条件的参数范围。"),
    "MATH-SHS-G10-FNC-001": (["函数概念", "函数单调性", "函数奇偶性"], "用气温、客流或蓄水量随时间变化的数据定义函数并分析基本性质。"),
    "MATH-SHS-G10-FNC-002": (["指数函数", "对数函数", "幂函数"], "用人口增长、衰减或声音强度等情境比较幂、指数和对数模型。"),
    "MATH-SHS-G10-FNC-003": (["三角函数", "诱导公式", "正弦型函数"], "用季节性日照时长或周期运动建立三角函数模型，分析周期和最值。"),
    "MATH-SHS-G10-GEO-001": (["平面向量", "向量数量积", "向量坐标运算"], "用城市道路位移或风向与行进方向表示向量，计算合位移和夹角。"),
    "MATH-SHS-G11-FNC-001": (["导数", "导数几何意义", "导数求最值"], "建立成本或包装材料用量函数，用导数分析单调区间并优化方案。"),
    "MATH-SHS-G11-FNC-002": (["等差数列", "等比数列", "数列求和"], "分析分期储蓄、阶梯座位或逐年增长数据，建立数列并计算总量。"),
    "MATH-SHS-G11-GEO-001": (["空间向量", "立体几何", "空间角与距离"], "在建筑或场馆模型中建立空间坐标系，用空间向量求线面角和距离。"),
    "MATH-SHS-G11-GEO-002": (["直线方程", "圆的方程", "直线与圆位置关系"], "把城市道路和圆形场地抽象为直线与圆，判断相交、相切或相离。"),
    "MATH-SHS-G11-GEO-003": (["椭圆", "双曲线", "抛物线"], "从轨迹、反射或工程轮廓情境识别圆锥曲线，求标准方程和几何性质。"),
    "MATH-SHS-G11-PRS-001": (["条件概率", "随机变量", "统计推断"], "根据产品抽检或调查数据计算条件概率，并用样本估计总体特征。"),
    "MATH-SHS-G12-FNC-001": (["函数综合", "导数应用", "参数讨论"], "综合成本、流量或变化率模型，用导数和分类讨论解决最值及参数问题。"),
    "MATH-SHS-G12-GEO-001": (["解析几何综合", "轨迹方程", "定点定值"], "把道路、场馆边界等抽象为曲线，综合研究交点、轨迹和定值问题。"),
    "MATH-SHS-G12-PRS-001": (["概率统计综合", "概率分布", "回归分析"], "分析农业试验或质量抽检数据，综合使用概率分布、期望和统计推断。"),
    "MATH-SHS-G12-MOD-001": (["高考数学综合", "数学建模", "多知识点综合"], "围绕河北交通、农业或文旅公开数据建立模型，综合函数、几何和概率方法。"),
}


def value(text: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def main() -> None:
    paths: dict[str, Path] = {}
    for path in KNOWLEDGE_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if value(text, "mastery_granularity") != "knowledge_point" or value(text, "stage") == "小学":
            continue
        code = value(text, "point_code")
        if code in CONTENT:
            paths[code] = path

    missing = sorted(set(CONTENT) - set(paths))
    if missing:
        raise SystemExit(f"未找到知识卡：{', '.join(missing)}")
    if len(CONTENT) != 41:
        raise SystemExit(f"预期 41 张知识卡，实际映射 {len(CONTENT)} 张")

    changed = 0
    for code, (keywords, example) in CONTENT.items():
        path = paths[code]
        text = path.read_text(encoding="utf-8")
        if value(text, "status") != "draft":
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
    print(f"本次补充 {changed} 张；初高中数学目标草稿卡共 {len(CONTENT)} 张")


if __name__ == "__main__":
    main()
