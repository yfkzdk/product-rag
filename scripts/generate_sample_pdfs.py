#!/usr/bin/env python
"""生成模拟工业产品手册 PDF 文件，用于测试真实 PDF 摄取管道。

用法:
    .\.venv\Scripts\python.exe scripts\generate_sample_pdfs.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF


class ProductManualPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, self.title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def add_section(self, heading, body):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 5, body)
        self.ln(3)


manuals = [
    {
        "filename": "PROD-001_smart_thermostat_manual.pdf",
        "title": "PROD-001 Smart Thermostat Product Manual v2.3",
        "sections": [
            ("1. Product Overview",
             "PROD-001 is an industrial-grade smart thermostat designed for precision temperature "
             "control in manufacturing environments. It supports Modbus RTU/TCP communication and "
             "features a 3.5-inch IPS display with IP65-rated front panel protection. Operating "
             "temperature range: -20C to 85C. Rated power: 220V/50Hz, 5W standby, 15W peak."),
            ("2. Technical Specifications",
             "Input Voltage: AC 220V +/- 10%, 50/60Hz\n"
             "Measurement Range: -40C to 125C\n"
             "Accuracy: +/- 0.1C (0-100C), +/- 0.3C (full range)\n"
             "Sensor Type: PT100/PT1000 RTD, NTC 10K (configurable)\n"
             "Output: 2x Relay (NO/NC, 250VAC/5A), 1x 4-20mA analog\n"
             "Communication: RS-485 (Modbus RTU), Ethernet (Modbus TCP)\n"
             "Display: 3.5-inch IPS, 480x320 resolution\n"
             "Protection: IP65 front panel, IP20 rear\n"
             "Dimensions: 96mm x 96mm x 85mm (WxHxD)\n"
             "Weight: 420g\n"
             "Mounting: Panel cutout 92mm x 92mm"),
            ("3. Installation Guide",
             "Step 1: Cut a 92mm x 92mm square hole in the control panel.\n"
             "Step 2: Insert the thermostat from the front and secure with the mounting bracket.\n"
             "Step 3: Connect power wiring to terminals L (Live) and N (Neutral).\n"
             "Step 4: Connect PT100 sensor to terminals 3-4 (polarity independent for 2-wire).\n"
             "Step 5: For 3-wire PT100, connect the two same-color wires to terminal 3, the third to terminal 4.\n"
             "Step 6: Connect relay output to terminals 7-8 (NO) or 7-9 (NC) as needed.\n"
             "Step 7: Power on and verify the display illuminates with firmware version.\n"
             "WARNING: Ensure main power is OFF before wiring. Use 0.5-1.5mm2 wire gauge."),
            ("4. Fault Codes and Troubleshooting",
             "E001 - Sensor Open: PT100 sensor disconnected or broken. Check wiring at terminals 3-4.\n"
             "  Solution: Measure resistance across sensor leads (should be 100-138 ohms at room temp).\n"
             "E002 - Sensor Short: Sensor wires shorted together. Inspect cable for damage.\n"
             "  Solution: Replace sensor cable if insulation is compromised.\n"
             "E003 - Over Temperature: Measured temperature exceeds 125C.\n"
             "  Solution: Check process temperature; verify sensor is rated for the application.\n"
             "E004 - Under Temperature: Measured temperature below -40C.\n"
             "  Solution: Verify sensor type setting matches installed sensor.\n"
             "E005 - Relay Fault: Relay contacts welded or driver failure detected.\n"
             "  Solution: Check load current does not exceed 5A rating; replace unit if fault persists.\n"
             "E006 - Memory Error: Internal EEPROM checksum failure.\n"
             "  Solution: Perform factory reset via menu > System > Reset > Factory Defaults."),
            ("5. Maintenance Schedule",
             "Monthly: Clean front panel with soft dry cloth. Verify display readability.\n"
             "Quarterly: Check wiring connections for tightness. Verify sensor accuracy with reference thermometer.\n"
             "Annually: Perform full calibration (menu > Calibration > 2-Point Cal).\n"
             "  Check relay contacts for signs of arcing or pitting. Replace if contact resistance > 50mOhm.\n"
             "Battery: CR2032 coin cell for RTC backup, replace every 2 years."),
            ("6. Compatibility Matrix",
             "Compatible Sensors: PT100 (2-wire, 3-wire), PT1000, NTC 10K B=3950\n"
             "Compatible Systems: Siemens S7-1200 PLC (Modbus TCP), Allen-Bradley MicroLogix (Modbus RTU)\n"
             "Partial Compat: Mitsubishi FX5U (requires RS-485 adapter FX5-485-BD)\n"
             "Incompatible: Direct 0-10V input (requires external signal conditioner)\n"
             "Software: Compatible with SCADA systems supporting Modbus TCP (WinCC, Ignition, LabVIEW)"),
        ]
    },
    {
        "filename": "PROD-003_pressure_transmitter_manual.pdf",
        "title": "PROD-003 Industrial Pressure Transmitter Manual v1.8",
        "sections": [
            ("1. Product Description",
             "PROD-003 is a piezoresistive pressure transmitter for hydraulic and pneumatic systems. "
             "Ranges available: 0-10 bar, 0-50 bar, 0-200 bar (gauge). Output: 4-20mA + HART protocol. "
             "Process connection: G1/4 male thread. Electrical connection: M12 4-pin connector."),
            ("2. Specifications",
             "Pressure Range: 0-200 bar (gauge)\n"
             "Overpressure Limit: 300 bar (1.5x FS)\n"
             "Burst Pressure: 600 bar (3x FS)\n"
             "Accuracy: +/- 0.25% FS (including linearity, hysteresis, repeatability)\n"
             "Output Signal: 4-20mA (2-wire), HART 7 protocol superimposed\n"
             "Supply Voltage: 10-30 VDC\n"
             "Load Resistance: (Vsupply - 10V) / 0.02A (max 500 ohm at 24V)\n"
             "Process Connection: G1/4 (DIN 3852), 1/4 NPT optional\n"
             "Wetted Materials: 316L stainless steel, FKM O-ring\n"
             "Protection: IP67\n"
             "Operating Temp: -25C to 85C\n"
             "Weight: 180g"),
            ("3. Installation",
             "1. Ensure process is depressurized before installation.\n"
             "2. Apply PTFE tape to G1/4 threads (3-4 wraps clockwise).\n"
             "3. Hand-tighten, then use wrench for final 1/4 turn. Do not overtighten.\n"
             "4. Connect M12 cable: Pin 1 = +24V, Pin 2 = Not Used, Pin 3 = 0V/GND, Pin 4 = Not Used.\n"
             "5. For HART communication, connect a 250 ohm resistor in series with the loop.\n"
             "6. Zero adjustment: press and hold the zero button for 3 seconds at zero pressure."),
            ("4. Fault Diagnosis",
             "E101 - Signal Low (< 3.6mA): Sensor element damage or cable break.\n"
             "  Check supply voltage at transmitter terminals. Measure loop resistance.\n"
             "E102 - Signal High (> 22mA): Overpressure condition or short circuit.\n"
             "  Verify process pressure is within range. Check for water ingress in connector.\n"
             "E103 - Drift > 0.5%: Diaphragm fouling or temperature effect.\n"
             "  Clean diaphragm with soft brush and solvent. Re-zero after cleaning.\n"
             "E104 - No HART Signal: Loop resistance too low or supply not HART-compatible.\n"
             "  Add 250 ohm resistor. Verify supply ripple < 100mV.\n"
             "E105 - Zero Shift: Mounting position effect or mechanical stress.\n"
             "  Re-zero in final mounting orientation. Check for pipe strain on process connection."),
            ("5. Maintenance",
             "Every 6 months: Visual inspection for corrosion, cable integrity, connector seal.\n"
             "Every 12 months: Full calibration with deadweight tester. Clean diaphragm.\n"
             "Every 3 years: Replace FKM O-ring (kit P/N: ORING-FKM-G14)."),
            ("6. Compatibility",
             "Compatible: Standard 4-20mA PLC analog input modules (Siemens SM331, AB 1756-IF8)\n"
             "  HART-compatible: Emerson AMS, Siemens PDM, PACTware\n"
             "Partial Compat: 0-10V PLC inputs require 500 ohm shunt resistor for 2-10V conversion\n"
             "Incompatible: Direct 3.3V/5V microcontroller ADC input without signal conditioning"),
        ]
    },
    {
        "filename": "PROD-005_servo_drive_manual.pdf",
        "title": "PROD-005 AC Servo Drive System Manual v4.2",
        "sections": [
            ("1. System Overview",
             "PROD-005 is a high-performance AC servo drive system consisting of the SD-2000 drive unit "
             "and SM-80 servo motor. Rated power: 750W. Suitable for CNC machining, robotic arms, "
             "and precision positioning applications. Supports EtherCAT, CANopen, and pulse-train control modes."),
            ("2. Drive Specifications",
             "Input Power: 220VAC 1-phase, 50/60Hz\n"
             "Rated Output: 750W (1.0 HP)\n"
             "Rated Current: 4.2A (continuous), 12.6A (peak, 3s)\n"
             "Control Modes: Position (pulse), Speed (analog +/-10V), Torque, EtherCAT CiA402\n"
             "Encoder Support: Incremental (2500 PPR), Absolute (17-bit, 131072 cpr), BISS-C\n"
             "Positioning Accuracy: +/- 1 pulse (incremental), +/- 1 arc-min (absolute)\n"
             "I/O: 8x Digital Input (24V PNP), 4x Digital Output, 2x Analog Input (12-bit)\n"
             "Protection: IP20, forced air cooling\n"
             "Dimensions: 170mm x 120mm x 160mm (WxHxD)\n"
             "Weight: 2.1 kg"),
            ("3. Motor Specifications (SM-80)",
             "Rated Torque: 2.39 Nm\n"
             "Peak Torque: 7.16 Nm (3x rated)\n"
             "Rated Speed: 3000 RPM\n"
             "Max Speed: 5000 RPM\n"
             "Rotor Inertia: 1.2 kg-cm2\n"
             "Shaft: 14mm keyed, IP54 sealing\n"
             "Weight: 3.5 kg"),
            ("4. Fault Codes",
             "AL.001 - Overcurrent: Motor cable short circuit or drive IGBT failure.\n"
             "  Check motor phase-to-phase resistance (should be 2-5 ohms). Inspect cable insulation.\n"
             "AL.002 - Overvoltage: Regenerative energy exceeds braking resistor capacity.\n"
             "  Add external braking resistor. Reduce deceleration rate (Pr.008).\n"
             "AL.003 - Undervoltage: Input voltage below 170VAC.\n"
             "  Check mains supply. Verify power wiring gauge is adequate.\n"
             "AL.004 - Encoder Fault: No encoder signal or checksum error.\n"
             "  Check encoder cable shielding. Verify 5V supply to encoder.\n"
             "AL.005 - Following Error: Position deviation exceeds Pr.015 threshold.\n"
             "  Increase following error limit or tune velocity feedforward (Pr.020).\n"
             "AL.006 - Overload: Motor operating above rated torque for extended period.\n"
             "  Reduce load or acceleration. Check mechanical binding in driven system."),
            ("5. Tuning Guide",
             "Auto-Tuning: Set Pr.001 = 1 to enable auto-tuning. Drive will measure load inertia and set gains.\n"
             "Manual Tuning: Adjust Pr.010 (Proportional Gain), Pr.011 (Integral Time), Pr.012 (Derivative Time).\n"
             "  Start with low gains and increase until audible ringing, then reduce by 20%.\n"
             "Notch Filter: Set Pr.030-033 to suppress mechanical resonance frequencies.\n"
             "  Use FFT function (menu > Diagnostic > FFT) to identify resonance peaks."),
            ("6. Compatibility",
             "Compatible Motors: SM-40 (400W), SM-80 (750W), SM-130 (1.5kW) series\n"
             "Compatible Controllers: Siemens SIMATIC S7-1500 (EtherCAT), Beckhoff TwinCAT 3\n"
             "Partial Compat: Omron NJ/NX series (requires ESI file import from vendor website)\n"
             "Incompatible: Direct 380V 3-phase input (requires step-down transformer)\n"
             "Cables: Use only shielded twisted-pair cables with drive-rated insulation (600V min)"),
        ]
    },
]

os.makedirs("data/pdfs", exist_ok=True)

for manual in manuals:
    pdf = ProductManualPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.title = manual["title"]
    pdf.add_page()

    for heading, body in manual["sections"]:
        pdf.add_section(heading, body)

    filepath = os.path.join("data/pdfs", manual["filename"])
    pdf.output(filepath)
    print(f"Generated: {filepath} ({pdf.pages_count} pages)")

print(f"\nDone. {len(manuals)} PDF manuals created in data/pdfs/")
