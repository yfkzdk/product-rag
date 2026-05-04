-- Migration: 001_initial_schema
-- Description: Initial database schema for Product Knowledge Graph

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    specifications JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_code ON products(product_code);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- Faults table
CREATE TABLE IF NOT EXISTS faults (
    id SERIAL PRIMARY KEY,
    fault_code VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    solution TEXT,
    product_id INTEGER REFERENCES products(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faults_code ON faults(fault_code);
CREATE INDEX IF NOT EXISTS idx_faults_product ON faults(product_id);
CREATE INDEX IF NOT EXISTS idx_faults_severity ON faults(severity);

-- Compatibility matrix table
CREATE TABLE IF NOT EXISTS compatibility_matrix (
    id SERIAL PRIMARY KEY,
    product_a_id INTEGER REFERENCES products(id),
    product_b_id INTEGER REFERENCES products(id),
    compatibility_type VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compat_product_a ON compatibility_matrix(product_a_id);
CREATE INDEX IF NOT EXISTS idx_compat_product_b ON compatibility_matrix(product_b_id);
CREATE INDEX IF NOT EXISTS idx_compat_type ON compatibility_matrix(compatibility_type);

-- Manual chunks table
CREATE TABLE IF NOT EXISTS manual_chunks (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    chunk_type VARCHAR(50) NOT NULL,
    section_title VARCHAR(200),
    content TEXT NOT NULL,
    chunk_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_product ON manual_chunks(product_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON manual_chunks(chunk_type);

-- Seed data: realistic product catalog
INSERT INTO products (product_code, name, category, description, specifications) VALUES
    ('CTL-001', '智能控制器X1', '控制器', '高性能工业智能控制器，支持多协议通信', '{"power": "220V AC", "weight": "1.2kg", "dimensions": "200×100×50mm", "working_temp": "-10°C ~ 60°C", "protection_level": "IP65", "communication": ["Modbus RTU", "CAN", "Ethernet"]}') ,
    ('CTL-002', 'PLC控制器A3', '控制器', '可编程逻辑控制器，适用于自动化生产线', '{"power": "24V DC", "weight": "0.8kg", "dimensions": "150×80×40mm", "io_channels": 16, "communication": ["RS485", "Profibus"]}') ,
    ('SEN-001', '温度传感器T200', '传感器', '高精度工业温度传感器', '{"range": "-20°C ~ 200°C", "accuracy": "±0.5°C", "response_time": "100ms", "output_signal": "4-20mA", "protection_level": "IP67"}') ,
    ('SEN-002', '压力传感器P100', '传感器', '工业压力传感器，适用于液压系统', '{"range": "0 ~ 10MPa", "accuracy": "±0.25%", "output_signal": "0-10V", "connection": "M12"}') ,
    ('ACT-001', '电动执行器E50', '执行器', '高性能电动执行器，支持远程控制', '{"torque": "500Nm", "speed": "10rpm", "voltage": "380V AC", "control_mode": "模拟量/数字量"}') ,
    ('MOD-001', '通信模块C4', '模块', '多协议通信转换模块', '{"protocols": ["Modbus RTU", "Modbus TCP", "CANopen"], "power_consumption": "5W", "channels": 4}') ,
    ('MOD-002', '电源模块PS24', '模块', '工业级24V电源模块', '{"output_voltage": "24V DC", "output_current": "10A", "input_voltage": "220V AC", "efficiency": "95%"}')
ON CONFLICT (product_code) DO NOTHING;

-- Seed data: realistic fault catalog
INSERT INTO faults (fault_code, description, severity, solution, product_id) VALUES
    ('E001', '设备无法启动，电源指示灯不亮', 'critical', '1. 检查电源连接是否正常\n2. 检查保险丝是否熔断\n3. 如保险丝完好，更换电源模块', 1),
    ('E002', '通信中断，Modbus连接超时', 'high', '1. 检查通信线路连接\n2. 确认通信参数配置正确\n3. 重启通信模块', 1),
    ('E003', '温度显示异常，读数偏差超过±5°C', 'medium', '1. 检查传感器安装位置\n2. 校准传感器参数\n3. 如校准无效，更换传感器', 3),
    ('E004', '执行器响应迟缓，动作延迟超过2秒', 'medium', '1. 检查执行器供电电压\n2. 清洁执行器机械部件\n3. 调整控制参数', 5),
    ('E005', '电源模块输出电压不稳定，波动超过±2V', 'high', '1. 检查输入电源质量\n2. 检查负载是否超出额定范围\n3. 更换电源模块', 7)
ON CONFLICT DO NOTHING;

-- Seed data: compatibility relationships
INSERT INTO compatibility_matrix (product_a_id, product_b_id, compatibility_type, confidence, notes) VALUES
    (1, 6, 'compatible', 0.95, 'CTL-001与MOD-001完全兼容，支持所有通信协议'),
    (1, 7, 'compatible', 0.98, 'CTL-001推荐使用MOD-002供电'),
    (3, 1, 'compatible', 0.90, 'SEN-001可直接连接CTL-001的模拟量输入'),
    (4, 1, 'compatible', 0.85, 'SEN-002需通过MOD-001转换后连接CTL-001'),
    (2, 6, 'upgrade', 0.80, 'CTL-002可升级为CTL-001以获得更多通信协议支持')
ON CONFLICT DO NOTHING;

-- Seed data: manual chunks for vector search
INSERT INTO manual_chunks (product_id, chunk_type, section_title, content, chunk_metadata) VALUES
    (1, 'spec', '产品概述', '智能控制器X1是一款高性能工业控制器，支持Modbus RTU、CAN和Ethernet三种通信协议。额定电压220V AC，工作温度范围-10°C至60°C，防护等级IP65，适合恶劣工业环境使用。', '{"page": 1}'),
    (1, 'spec', '技术参数', 'CTL-001技术参数：输入电压220V AC（100-240V宽范围），额定功率500W，重量1.2kg，外形尺寸200×100×50mm。支持16路数字量输入、8路模拟量输入（4-20mA/0-10V），8路数字量输出。', '{"page": 3}'),
    (1, 'troubleshoot', '故障排查-无法启动', 'CTL-001无法启动排查步骤：1. 检查电源线连接是否牢固；2. 确认输入电压在100-240V范围内；3. 检查保险丝（规格5A/250V）；4. 观察电源指示灯状态（绿灯=正常，红灯=故障）；5. 如以上均正常，联系技术支持。', '{"page": 15}'),
    (3, 'spec', '温度传感器T200规格', '温度传感器T200：测量范围-20°C至200°C，精度±0.5°C，响应时间100ms，输出信号4-20mA，防护等级IP67。安装方式：M12螺纹安装，探头长度50mm。', '{"page": 1}'),
    (3, 'troubleshoot', '温度异常排查', '温度传感器T200显示异常排查：1. 检查传感器安装位置是否正确（避免阳光直射和热源干扰）；2. 校准零点和量程；3. 检查信号线连接（4-20mA回路电阻<500Ω）；4. 如读数持续偏差>±5°C，更换传感器。', '{"page": 12}')
ON CONFLICT DO NOTHING;