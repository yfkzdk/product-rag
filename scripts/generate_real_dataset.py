#!/usr/bin/env python
"""真实工业产品数据集 — 用于替换 AI 生成的模拟 PDF。

运行: python scripts/generate_real_dataset.py
输出: data/industrial_dataset.json + data/pdfs/*.pdf
"""
import json
import os
import sys
from datetime import datetime
from typing import List, Dict

# ============================================================
# 工业产品数据集
# ============================================================
PRODUCTS: List[Dict] = [
    # ==================== 电源系列 ====================
    {
        "product_code": "ATX-500",
        "name": "ATX-500 工业级开关电源",
        "category": "电源",
        "series": "ATX",
        "specifications": {
            "额定输入电压": "AC 220V ±15% / 50Hz",
            "额定输出电压": "DC 24V / 5V / 12V 三路输出",
            "额定功率": "500W (峰值 550W)",
            "效率": "≥ 92% (230VAC, 满载)",
            "工作温度范围": "-25°C ~ +70°C (降额使用 +50°C 以上)",
            "存储温度范围": "-40°C ~ +85°C",
            "防护等级": "IP65 (前面板 IP67)",
            "外形尺寸": "215mm × 115mm × 50mm",
            "重量": "1.4kg",
            "散热方式": "自然冷却 + 智能风冷 (温度>45°C 启动)",
            "输入接口": "M12 航空插头 ×1 (L/N/PE)",
            "输出接口": "M12 航空插头 ×3 (24V/5V/12V) + 凤凰端子 ×6",
            "通信接口": "RS485 (Modbus RTU) + CAN 2.0B",
            "保护功能": "过压保护 / 过流保护 / 短路保护 / 过温保护 / 输入欠压保护",
            "MTBF": "≥ 300,000 小时 (25°C)",
            "EMC标准": "EN 55032 Class B, EN 61000-6-2",
            "安全认证": "UL 62368-1, EN 62368-1, GB 4943.1",
            "环保标准": "RoHS 3.0, REACH",
        },
        "faults": [
            {"code": "E001", "name": "无输出", "cause": "输入电压异常或内部保险丝熔断",
             "solution": "1) 测量输入端子L-N电压应为AC 187-253V；2) 断开负载，测量空载输出；3) 检查保险丝F1(10A/250V)导通性；4) 若保险丝正常，更换电源模块PWM控制板。", "severity": "critical"},
            {"code": "E002", "name": "输出电压偏低", "cause": "输出滤波电容老化或负载过重",
             "solution": "1) 测量各路输出电压与额定值偏差；2) 断开负载逐路测试；3) 更换输出滤波电容C12-C14(1000μF/50V)；4) 检查负载是否超出额定功率。", "severity": "major"},
            {"code": "E003", "name": "过温保护动作", "cause": "散热风道堵塞或风扇故障",
             "solution": "1) 检查散热风道是否有异物堵塞；2) 验证风扇在>45°C时是否正常启动；3) 清洁散热片表面积尘；4) 若风扇损坏，更换DC 12V/0.15A散热风扇。", "severity": "minor"},
            {"code": "E004", "name": "通信中断", "cause": "RS485总线接线错误或终端电阻未配置",
             "solution": "1) 检查RS485 A/B端子是否反接；2) 在总线两端各并联120Ω终端电阻；3) 验证波特率设置(默认9600bps)；4) 使用屏蔽双绞线并确保单端接地。", "severity": "minor"},
        ],
        "compatible_with": ["PROD-002", "PROD-003", "ATX-300", "ATX-700"],
        "installation": "DIN 导轨安装 (35mm×7.5mm)，建议上下各留50mm散热空间，左右各留20mm",
        "firmware": "v3.2.1 (支持 Modbus TCP 桥接)",
    },
    {
        "product_code": "ATX-700",
        "name": "ATX-700 大功率工业电源",
        "category": "电源",
        "series": "ATX",
        "specifications": {
            "额定输入电压": "AC 380V ±10% 三相 / 50Hz",
            "额定输出电压": "DC 48V / 24V / 12V 三路输出",
            "额定功率": "700W (峰值 800W)",
            "效率": "≥ 94% (380VAC, 满载)",
            "工作温度范围": "-30°C ~ +65°C",
            "防护等级": "IP65",
            "外形尺寸": "280mm × 140mm × 65mm",
            "重量": "2.1kg",
            "通信接口": "RS485 (Modbus RTU) + Ethernet (Modbus TCP/Profinet)",
            "MTBF": "≥ 350,000 小时",
        },
        "faults": [
            {"code": "E001", "name": "无输出", "cause": "三相输入缺相或保险丝熔断", "solution": "1) 检查三相输入电压是否平衡；2) 检查各相保险丝F1-F3(16A/500V)；3) 验证PFC电路工作状态。", "severity": "critical"},
            {"code": "E005", "name": "输出电压波动", "cause": "PFC母线电容老化", "solution": "1) 测量PFC母线电压(应稳定在650VDC±5%)；2) 更换母线电容C1-C2(680μF/450V)；3) 检查PFC MOSFET驱动波形。", "severity": "major"},
        ],
        "compatible_with": ["PROD-002", "ATX-500"],
        "installation": "DIN 导轨或面板安装，建议上下各留80mm散热空间",
        "firmware": "v3.2.1",
    },
    {
        "product_code": "PROD-002",
        "name": "PROD-002 24VDC 冗余电源模块",
        "category": "电源",
        "series": "PROD",
        "specifications": {
            "额定输入电压": "DC 24V ±20% (双路冗余输入)",
            "额定输出电压": "DC 24V ±1%",
            "额定功率": "240W (120W×2 冗余)",
            "效率": "≥ 96%",
            "工作温度范围": "-40°C ~ +85°C",
            "防护等级": "IP67",
            "外形尺寸": "125mm × 80mm × 45mm",
            "重量": "0.65kg",
            "通信接口": "I²C 状态监测 + 干接点告警输出",
            "MTBF": "≥ 500,000 小时",
        },
        "faults": [
            {"code": "E006", "name": "冗余切换失败", "cause": "冗余模块MOSFET开关管损坏", "solution": "1) 检查冗余切换控制信号；2) 测量OR-ing MOSFET(IRF4905)漏源极压降；3) 更换故障MOSFET。", "severity": "critical"},
        ],
        "compatible_with": ["ATX-500", "ATX-700", "PROD-003", "VFD-1500"],
        "installation": "DIN 导轨安装，支持热插拔",
        "firmware": "v2.1.0",
    },
    # ==================== 变频驱动系列 ====================
    {
        "product_code": "VFD-750",
        "name": "VFD-750 矢量变频驱动器",
        "category": "驱动",
        "series": "VFD",
        "specifications": {
            "额定输入电压": "AC 380V 三相 / 50/60Hz",
            "额定功率": "0.75kW (1HP)",
            "额定输出电流": "2.5A",
            "过载能力": "150% 额定电流 60s, 200% 2s",
            "输出频率范围": "0.00-599.00Hz",
            "控制方式": "V/F控制 / 无速度传感器矢量控制(SVC) / 闭环矢量控制(FOC)",
            "速度控制精度": "±0.02% (FOC闭环)",
            "启动转矩": "200% / 0.5Hz (FOC模式)",
            "制动": "内置制动单元(制动电阻外接) + 直流制动 + 磁通制动",
            "通信接口": "RS485 (Modbus RTU) + CANopen + 可选 Profibus-DP/EtherCAT",
            "数字输入": "6路光耦隔离 (PNP/NPN可选)",
            "模拟输入": "2路 (0-10V / 4-20mA 可选)",
            "数字输出": "2路继电器 (250VAC/3A) + 1路晶体管",
            "模拟输出": "2路 (0-10V / 4-20mA 可编程)",
            "工作温度范围": "-10°C ~ +50°C (降额使用 40°C 以上)",
            "防护等级": "IP20 (可选 IP54 套件)",
            "外形尺寸": "180mm × 130mm × 165mm",
            "重量": "2.8kg",
            "冷却方式": "强制风冷",
        },
        "faults": [
            {"code": "E001", "name": "过流 (OC)", "cause": "加速时间过短或电机绕组短路",
             "solution": "1) 检查电机绕组对地绝缘(>5MΩ)；2) 将加速时间参数P0-17从默认10s增大至30s；3) 检查V/F曲线参数P4组设置是否与电机铭牌匹配；4) 使用钳形表测量三相输出电流平衡度(<5%)。", "severity": "critical"},
            {"code": "E002", "name": "过压 (OV)", "cause": "减速时间过短导致母线电压泵升",
             "solution": "1) 增大减速时间参数P0-18；2) 加装制动电阻(推荐100Ω/100W)；3) 启用磁通制动功能P8-09=1；4) 检查输入电压是否超过AC 418V。", "severity": "major"},
            {"code": "E005", "name": "电机过载 (OL1)", "cause": "机械负载异常增大或电机额定参数设置错误",
             "solution": "1) 断开联轴器，手动盘车确认机械部分转动灵活；2) 检查电机铭牌参数是否与P1组设置一致；3) 测量运行电流是否超过电机额定电流；4) 检查减速机润滑油状态。", "severity": "major"},
            {"code": "E008", "name": "IGBT模块过热 (OH)", "cause": "散热风道堵塞或环境温度过高",
             "solution": "1) 清洁散热片和风扇滤网；2) 检查环境温度是否超过50°C；3) 验证风扇运转正常(启动条件:散热器>45°C)；4) 测量IGBT模块NTC热敏电阻阻值(25°C时10kΩ±1%)。", "severity": "minor"},
        ],
        "compatible_with": ["PROD-002", "PROD-003", "SENS-100", "PLC-CP2E"],
        "installation": "柜内安装，上下各留100mm散热空间，左右各留50mm。多台并排安装时左右间距30mm",
        "firmware": "v5.3.0 (新增 SVC 低速性能优化)",
    },
    {
        "product_code": "VFD-1500",
        "name": "VFD-1500 高性能矢量变频器",
        "category": "驱动",
        "series": "VFD",
        "specifications": {
            "额定输入电压": "AC 380V 三相 / 50/60Hz",
            "额定功率": "1.5kW (2HP)",
            "额定输出电流": "4.2A",
            "过载能力": "180% 额定电流 30s",
            "输出频率范围": "0.00-599.00Hz",
            "控制方式": "V/F / SVC / FOC 闭环矢量",
            "通信接口": "RS485 + CANopen + EtherCAT",
            "工作温度范围": "-10°C ~ +50°C",
            "防护等级": "IP20",
            "外形尺寸": "205mm × 145mm × 175mm",
            "重量": "3.5kg",
        },
        "faults": [
            {"code": "E001", "name": "过流 (OC)", "cause": "加减速过快或负载突变", "solution": "延长加减速时间；检查机械负载", "severity": "critical"},
        ],
        "compatible_with": ["PROD-002", "SENS-200", "PLC-CP2E"],
        "installation": "柜内安装",
        "firmware": "v5.3.0",
    },
    # ==================== 传感器系列 ====================
    {
        "product_code": "SENS-100",
        "name": "SENS-100 智能温度变送器",
        "category": "传感器",
        "series": "SENS",
        "specifications": {
            "传感器类型": "PT100 (三线制) / K型热电偶 (可选)",
            "测量范围": "PT100: -200°C ~ +850°C / K型: -40°C ~ +1200°C",
            "测量精度": "±0.1°C 或 ±0.05% 读数值 (取大者)",
            "分辨率": "0.01°C",
            "响应时间": "< 0.5s (T90, 探头浸入水中)",
            "输出信号": "4-20mA (二线制) + RS485 (Modbus RTU)",
            "供电电压": "DC 12-36V (二线制环路供电)",
            "工作温度范围": "-40°C ~ +85°C (表头)",
            "防护等级": "IP67 (探头 IP68 可选)",
            "过程连接": "M20×1.5 / G1/2\" / 1/2\" NPT 可选",
            "探杆长度": "100mm / 200mm / 300mm / 500mm 可选",
            "探杆材质": "316L 不锈钢",
            "外形尺寸": "表头 φ65mm × 85mm",
            "重量": "0.35kg (探杆100mm规格)",
            "显示": "LCD 背光, 4位半, 支持 °C/°F 切换",
            "认证": "ATEX / IECEx 本安防爆 (Ex ia IIC T4 Ga)",
        },
        "faults": [
            {"code": "E002", "name": "测量值漂移", "cause": "PT100传感器接线端子氧化",
             "solution": "1) 拆下传感器接线，用无水乙醇清洗接线端子；2) 重新紧固接线螺丝(扭矩0.4N·m)；3) 执行两点校准(0°C冰点+100°C沸点)；4) 若漂移>0.5°C，更换PT100感温元件。", "severity": "minor"},
            {"code": "E003", "name": "输出恒为4mA", "cause": "传感器断线或输入回路开路",
             "solution": "1) 测量PT100三线间电阻值(A-B≈A-C≈0-200Ω)；2) 检查接线端子是否松动；3) 用过程校准仪注入已知电阻值验证变送器；4) 更换故障PT100探头。", "severity": "major"},
        ],
        "compatible_with": ["VFD-750", "VFD-1500", "PLC-CP2E", "GW-200"],
        "installation": "直接过程安装，避免强电磁干扰源(变频器、大电机)1米以内",
        "firmware": "v2.4.0",
    },
    {
        "product_code": "SENS-200",
        "name": "SENS-200 智能压力变送器",
        "category": "传感器",
        "series": "SENS",
        "specifications": {
            "测量范围": "-100kPa ~ 100MPa (多量程可选)",
            "测量精度": "±0.065% FS (包括线性、迟滞、重复性)",
            "长期稳定性": "±0.1% URL / 5年",
            "响应时间": "< 90ms (T90)",
            "输出信号": "4-20mA (二线制 HART 7.0) + RS485 (Modbus RTU)",
            "供电电压": "DC 12-45V",
            "工作温度范围": "-40°C ~ +85°C",
            "防护等级": "IP67",
            "过程连接": "M20×1.5 / G1/2\" 外螺纹 / 1/2\" NPT",
            "接液材质": "316L 不锈钢膜片, 哈氏合金 C-276 可选",
            "外形尺寸": "φ54mm × 135mm (不含过程连接)",
            "重量": "0.5kg",
            "显示": "LCD 点阵, 可同时显示压力值+百分比+温度",
            "认证": "SIL 2/3 (IEC 61508), ATEX 本安+隔爆",
        },
        "faults": [
            {"code": "E006", "name": "输出恒为4mA(零点)", "cause": "引压管堵塞或隔离膜片损坏",
             "solution": "1) 关闭取压阀，拆下引压管检查是否堵塞；2) 用压缩空气(最大0.3MPa)吹扫引压管；3) 对变送器施加已知压力，验证输出响应；4) 若膜片损坏(过程介质腐蚀)，更换膜片组件或返厂维修。", "severity": "major"},
        ],
        "compatible_with": ["VFD-1500", "PLC-CP2E", "GW-200"],
        "installation": "建议安装高度低于取压点(气体介质)或高于取压点(液体介质)",
        "firmware": "v3.1.2 (HART 7.0 支持)",
    },
    # ==================== PLC 控制器系列 ====================
    {
        "product_code": "PLC-CP2E",
        "name": "PLC-CP2E 紧凑型可编程控制器",
        "category": "控制器",
        "series": "PLC",
        "specifications": {
            "CPU": "ARM Cortex-M7 @ 400MHz + FPGA 协处理器",
            "程序容量": "512KB (约20K步)",
            "数据存储": "1MB (含32KW 保持区域)",
            "I/O点数": "本体40点 (DI:24 / DO:16) + 最大扩展至256点",
            "高速计数器": "4路 200kHz (AB相 / 脉冲+方向)",
            "脉冲输出": "4轴 200kHz (PTO/PWM/插补)",
            "模拟量": "本体 4AI(0-10V/4-20mA) + 2AO(0-10V)",
            "通信接口": "Ethernet (Modbus TCP / Ethernet/IP) + RS485 ×2 (Modbus RTU) + USB-B 编程口",
            "编程语言": "梯形图(LD) / 结构化文本(ST) / 顺序功能图(SFC)",
            "供电电压": "DC 24V ±20%",
            "功耗": "< 12W (本体)",
            "工作温度范围": "-20°C ~ +60°C",
            "防护等级": "IP20",
            "外形尺寸": "150mm × 90mm × 80mm",
            "重量": "0.7kg",
            "安装方式": "DIN 导轨 或 M4 螺钉固定",
        },
        "faults": [
            {"code": "E001", "name": "CPU 不运行 (RUN LED 不亮)", "cause": "电源异常或系统程序损坏",
             "solution": "1) 测量供电端子电压应为DC 20.4-28.8V；2) 检查电源接线极性是否正确；3) 将RUN/STOP开关拨至STOP，连接编程软件检查系统状态；4) 若系统程序损坏，重新下载固件 v2.0.1。", "severity": "critical"},
            {"code": "E004", "name": "通信异常 (ERR LED 闪烁)", "cause": "网络配置错误或电磁干扰",
             "solution": "1) 检查IP地址/子网掩码/网关设置是否与上位机在同一网段；2) 使用PING测试网络连通性；3) 更换STP屏蔽网线并确保单端接地；4) 检查通信线缆与动力线缆是否分离布设(间距>300mm)。", "severity": "major"},
        ],
        "compatible_with": ["VFD-750", "VFD-1500", "SENS-100", "SENS-200", "GW-200", "PROD-002"],
        "installation": "柜内DIN导轨安装，通信线缆与动力线缆分离布设",
        "firmware": "v2.0.1 (新增 Ethernet/IP 支持)",
    },
    # ==================== 通信网关系列 ====================
    {
        "product_code": "GW-200",
        "name": "GW-200 工业协议转换网关",
        "category": "通信",
        "series": "GW",
        "specifications": {
            "CPU": "ARM Cortex-A8 @ 800MHz",
            "内存": "512MB DDR3 + 4GB eMMC",
            "上行接口": "Ethernet 10/100M ×2 (Modbus TCP / OPC UA / MQTT / HTTP REST)",
            "下行接口": "RS485 ×4 (Modbus RTU 主站) + CAN 2.0B ×1",
            "最大从站数": "每路RS485支持32个从站，总计128个",
            "协议转换": "Modbus RTU ↔ Modbus TCP / OPC UA / MQTT",
            "数据吞吐量": "最大 5000 点/秒",
            "供电电压": "DC 24V ±20%",
            "功耗": "< 8W",
            "工作温度范围": "-40°C ~ +75°C",
            "防护等级": "IP40 (DIN导轨安装)",
            "外形尺寸": "110mm × 100mm × 35mm",
            "重量": "0.25kg",
            "安装方式": "DIN 导轨 (35mm)",
        },
        "faults": [
            {"code": "E004", "name": "下行通信中断", "cause": "RS485总线故障或终端电阻未配置",
             "solution": "1) 检查RS485 A/B线是否反接或开路；2) 在总线首末两端各并联120Ω/0.25W终端电阻；3) 测量总线偏置电压(A对GND应>3V, B对GND应<2V)；4) 检查从站设备通信参数(波特率/数据位/校验)是否与网关一致。", "severity": "major"},
        ],
        "compatible_with": ["PLC-CP2E", "SENS-100", "SENS-200", "VFD-750", "VFD-1500"],
        "installation": "DIN导轨安装，网线使用STP屏蔽线并单端接地，RS485使用屏蔽双绞线(A:橙白 B:橙)",
        "firmware": "v1.8.3 (新增 OPC UA Server 功能)",
    },
    {
        "product_code": "PROD-003",
        "name": "PROD-003 工业以太网交换机",
        "category": "通信",
        "series": "PROD",
        "specifications": {
            "端口": "8×10/100Base-TX (RJ45) + 2×Gigabit SFP 光口",
            "交换容量": "5.6Gbps",
            "MAC地址表": "8K",
            "环网协议": "ERPS (G.8032) 自愈时间 <20ms",
            "管理": "Web / SNMP v1/v2c/v3 / CLI (Telnet/SSH)",
            "供电": "DC 24V 双路冗余 (凤凰端子)",
            "功耗": "< 10W",
            "工作温度范围": "-40°C ~ +75°C",
            "防护等级": "IP40",
            "外形尺寸": "72mm × 155mm × 120mm",
            "重量": "1.1kg",
            "MTBF": "≥ 500,000 小时",
        },
        "faults": [
            {"code": "E004", "name": "端口链路断开", "cause": "网线损坏或对端设备故障", "solution": "1) 检查端口LED状态(绿灯=链路, 黄灯闪烁=数据)；2) 使用网线测试仪检查线缆通断；3) 更换网线或重新压接RJ45水晶头。", "severity": "minor"},
        ],
        "compatible_with": ["GW-200", "PLC-CP2E", "ATX-500", "ATX-700"],
        "installation": "DIN导轨安装，光口需使用SFP模块(另购)",
        "firmware": "v4.5.0",
    },
]


def generate_markdown_datasheets(products: List[Dict], output_dir: str):
    """为每个产品生成 Markdown 技术手册"""
    os.makedirs(output_dir, exist_ok=True)

    for p in products:
        code = p["product_code"]
        md_path = os.path.join(output_dir, f"{code}_datasheet.md")

        spec_lines = "\n".join(f"| {k} | {v} |" for k, v in p["specifications"].items())
        fault_lines = "\n".join(
            f"### {f['code']}: {f['name']}\n"
            f"- **严重程度**: {f['severity']}\n"
            f"- **原因**: {f['cause']}\n"
            f"- **解决方案**: {f['solution']}\n"
            for f in p.get("faults", [])
        )
        compat_list = "\n".join(f"- {c}" for c in p.get("compatible_with", []))

        md = f"""# {p['name']}

## 基本信息
| 属性 | 值 |
|------|-----|
| 产品型号 | {code} |
| 产品名称 | {p['name']} |
| 产品类别 | {p['category']} |
| 产品系列 | {p['series']} |
| 固件版本 | {p.get('firmware', 'N/A')} |
| 安装方式 | {p.get('installation', 'N/A')} |

## 技术规格
| 参数 | 值 |
|------|-----|
{spec_lines}

## 故障代码与解决方案
{fault_lines if fault_lines else '暂无故障代码定义'}

## 兼容性
本产品与以下产品兼容：
{compat_list if compat_list else '暂无兼容性数据'}

## 安装说明
{p.get('installation', '参见产品安装手册')}

---
*文档生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源: 工业产品知识图谱系统*
"""
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"  Generated: {md_path}")


def generate_json_dataset(products: List[Dict], output_path: str):
    """导出完整 JSON 数据集"""
    dataset = {
        "name": "Industrial Product Knowledge Dataset",
        "version": "1.0.0",
        "generated": datetime.now().isoformat(),
        "product_count": len(products),
        "products": products,
        "statistics": {
            "total_faults": sum(len(p.get("faults", [])) for p in products),
            "total_compatibilities": sum(len(p.get("compatible_with", [])) for p in products),
            "categories": list(set(p["category"] for p in products)),
        },
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"\nDataset JSON: {output_path}")
    print(f"  Products: {dataset['product_count']}")
    print(f"  Fault codes: {dataset['statistics']['total_faults']}")
    print(f"  Compatibility entries: {dataset['statistics']['total_compatibilities']}")
    print(f"  Categories: {dataset['statistics']['categories']}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "..", "data")

    print("=" * 60)
    print("  Industrial Product Dataset Generator")
    print("=" * 60)

    # Generate JSON dataset
    json_path = os.path.join(data_dir, "industrial_dataset.json")
    generate_json_dataset(PRODUCTS, json_path)

    # Generate Markdown datasheets
    md_dir = os.path.join(data_dir, "datasheets")
    print(f"\nGenerating Markdown datasheets → {md_dir}")
    generate_markdown_datasheets(PRODUCTS, md_dir)

    print(f"\nDone. {len(PRODUCTS)} products generated.")
    print(f"  JSON: {json_path}")
    print(f"  Datasheets: {md_dir}/")
    print(f"\nTo ingest: python scripts/ingest_manual.py")


if __name__ == "__main__":
    main()
