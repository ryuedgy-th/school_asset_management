# 🎨 Dashboard Minimalist Redesign - Task List

## 📋 Overview
ปรับปรุง Asset Management Dashboard ให้เป็นสไตล์ **Minimalist** แบบ modern school admin panel พร้อมสี soft pastel และ clean design

---

## ✅ สิ่งที่ทำไปแล้ว

### 1. สร้าง CSS File
**ไฟล์:** `/home/ryu/school_asset_management/static/src/css/dashboard_minimal.css`

**Features:**
- ✅ Soft pastel gradient colors (8 colors)
- ✅ Clean card design with rounded corners (16px radius)
- ✅ Smooth hover animations (lift + shadow)
- ✅ Responsive layout
- ✅ Fade-in animations on load
- ✅ Minimalist typography

---

## 📝 สิ่งที่ต้องทำต่อ

### Task 1: สร้าง Assets Bundle XML
**ไฟล์:** `views/assets.xml` (สร้างใหม่)

**จุดประสงค์:** โหลด CSS เข้า Odoo backend

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="assets_backend_dashboard" name="Dashboard Assets" inherit_id="web.assets_backend">
        <xpath expr="." position="inside">
            <link rel="stylesheet" type="text/scss" href="/school_asset_management/static/src/css/dashboard_minimal.css"/>
        </xpath>
    </template>
</odoo>
```

**ต้องเพิ่มใน `__manifest__.py`:**
```python
'assets': {
    'web.assets_backend': [
        'school_asset_management/static/src/css/dashboard_minimal.css',
    ],
},
```

---

### Task 2: อัพเดท Dashboard View XML
**ไฟล์:** `views/asset_dashboard.xml`

#### 2.1 เพิ่ม Container Class
เปลี่ยน:
```xml
<div class="container o_kanban_card_content">
```

เป็น:
```xml
<div class="container o_kanban_card_content o_asset_dashboard">
```

#### 2.2 แก้ไข Card Structure - Row 1

**Card 1: Total Assets (Blue/Purple Gradient)**
เปลี่ยนจาก:
```xml
<div class="card bg-primary text-white">
    <div class="card-body">
        <h4 class="card-title">📦 Total Assets</h4>
        <h2><field name="total_assets" readonly="1" nolabel="1"/></h2>
        <p class="mb-0">All assets in system</p>
    </div>
</div>
```

เป็น:
```xml
<div class="stat-card card-blue">
    <div class="icon-wrapper">📦</div>
    <div class="card-label">Total Assets</div>
    <div class="card-value"><field name="total_assets" readonly="1" nolabel="1"/></div>
    <p class="card-desc">All assets in system</p>
</div>
```

**Card 2: Available (Green/Cyan Gradient)**
```xml
<div class="stat-card card-green">
    <div class="icon-wrapper">✅</div>
    <div class="card-label">Available</div>
    <div class="card-value"><field name="available_assets" readonly="1" nolabel="1"/></div>
    <p class="card-desc">Ready for assignment</p>
</div>
```

**Card 3: Teachers (Purple/Pink Gradient)**
```xml
<div class="stat-card card-purple">
    <div class="icon-wrapper">👨‍🏫</div>
    <div class="card-label">Teachers</div>
    <div class="card-value"><field name="assigned_teacher" readonly="1" nolabel="1"/></div>
    <p class="card-desc">Assigned to teachers</p>
</div>
```

**Card 4: Students (Orange/Yellow Gradient)**
```xml
<div class="stat-card card-orange">
    <div class="icon-wrapper">👨‍🎓</div>
    <div class="card-label">Students</div>
    <div class="card-value"><field name="assigned_student" readonly="1" nolabel="1"/></div>
    <p class="card-desc">Assigned to students</p>
</div>
```

#### 2.3 แก้ไข Card Structure - Row 2

**Card 5: Maintenance (Teal/Purple Gradient)**
```xml
<div class="stat-card card-teal">
    <div class="icon-wrapper">🔧</div>
    <div class="card-label">Maintenance</div>
    <div class="card-value"><field name="maintenance_assets" readonly="1" nolabel="1"/></div>
    <p class="card-desc">Under maintenance/repair</p>
</div>
```

**Card 6: Warranty Expiring (Red/Pink Gradient)**
```xml
<div class="stat-card card-red">
    <div class="icon-wrapper">⚠️</div>
    <div class="card-label">Warranty Expiring</div>
    <div class="card-value"><field name="warranty_expiring" readonly="1" nolabel="1"/></div>
    <p class="card-desc">Expires within 30 days</p>
</div>
```

**Card 7: Total Value (Pink/Rose Gradient)**
```xml
<div class="stat-card card-pink">
    <div class="icon-wrapper">💰</div>
    <div class="card-label">Total Value</div>
    <div class="card-value"><field name="total_asset_value" widget="monetary" readonly="1" nolabel="1"/> ฿</div>
    <p class="card-desc">Total asset value</p>
</div>
```

**Card 8: Damage Cost (Yellow/Peach Gradient)**
```xml
<div class="stat-card card-yellow">
    <div class="icon-wrapper">💸</div>
    <div class="card-label">Damage Cost</div>
    <div class="card-value"><field name="total_damage_cost" widget="monetary" readonly="1" nolabel="1"/> ฿</div>
    <p class="card-desc">Total damages (<field name="total_damages" readonly="1" nolabel="1"/> items)</p>
</div>
```

#### 2.4 แก้ไข Quick Action Buttons

เปลี่ยนจาก:
```xml
<button type="action" name="%(action_asset_asset)d" class="btn btn-primary">
    <i class="fa fa-cubes"/> View All Assets
</button>
```

เป็น:
```xml
<button type="action" name="%(action_asset_asset)d" class="action-btn">
    <i class="fa fa-cubes"/> View All Assets
</button>
```

(ทำซ้ำกับ buttons ทั้ง 4 ตัว)

#### 2.5 แก้ไข Info Alert

เปลี่ยนจาก:
```xml
<div class="alert alert-info">
```

เป็น:
```xml
<div class="alert-minimal">
```

---

### Task 3: อัพเดท `__manifest__.py`
**ไฟล์:** `__manifest__.py`

เพิ่ม section ใหม่หรืออัพเดทที่มีอยู่:

```python
'data': [
    # ... existing files ...
    'views/assets.xml',  # เพิ่มบรรทัดนี้
    'views/asset_dashboard.xml',
],
'assets': {
    'web.assets_backend': [
        'school_asset_management/static/src/css/dashboard_minimal.css',
    ],
},
```

---

### Task 4: Upload Files to Server

```bash
# Upload CSS
scp /home/ryu/school_asset_management/static/src/css/dashboard_minimal.css \
    odoo19:/opt/odoo19/custom_addons/school_asset_management/static/src/css/

# Upload views (หลังจากแก้ไขแล้ว)
scp /home/ryu/school_asset_management/views/assets.xml \
    odoo19:/opt/odoo19/custom_addons/school_asset_management/views/

scp /home/ryu/school_asset_management/views/asset_dashboard.xml \
    odoo19:/opt/odoo19/custom_addons/school_asset_management/views/

scp /home/ryu/school_asset_management/__manifest__.py \
    odoo19:/opt/odoo19/custom_addons/school_asset_management/
```

---

### Task 5: Upgrade Module

```bash
# SSH to server
ssh odoo19

# Stop Odoo
sudo systemctl stop odoo19

# Upgrade module
sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo-bin \
    -c /etc/odoo19.conf -d odoo19 \
    -u school_asset_management --stop-after-init

# Start Odoo
sudo systemctl start odoo19

# Check status
sudo systemctl status odoo19
```

---

### Task 6: Test Dashboard

1. **Clear Browser Cache:** Ctrl + Shift + R
2. **Login to Odoo:** http://www.myisbackoffice.space
3. **Navigate:** Asset Management → Dashboard
4. **Verify:**
   - ✅ Cards มีสี pastel gradients
   - ✅ Hover effects ทำงาน (lift + shadow)
   - ✅ Icons แสดงในกล่องสี่เหลี่ยมมุมมน
   - ✅ Typography เรียบร้าย อ่านง่าย
   - ✅ Buttons มีสไตล์ minimalist
   - ✅ Responsive บน mobile

---

## 🎨 Color Palette - Soft Pastel Gradients

| Card | Gradient Colors | Usage |
|------|----------------|-------|
| **Blue/Purple** | `#667eea → #764ba2` | Total Assets |
| **Green/Cyan** | `#84fab0 → #8fd3f4` | Available |
| **Purple/Pink** | `#a18cd1 → #fbc2eb` | Teachers |
| **Orange/Yellow** | `#fa709a → #fee140` | Students |
| **Teal/Purple** | `#30cfd0 → #330867` | Maintenance |
| **Red/Pink** | `#ff6b6b → #ee5a6f` | Warranty Expiring |
| **Pink/Rose** | `#ff9a9e → #fecfef` | Total Value |
| **Yellow/Peach** | `#ffecd2 → #fcb69f` | Damage Cost |

---

## 📂 File Structure

```
school_asset_management/
├── __manifest__.py                          # อัพเดท: เพิ่ม assets
├── static/
│   └── src/
│       └── css/
│           └── dashboard_minimal.css        # ✅ สร้างแล้ว
└── views/
    ├── assets.xml                           # ❌ ต้องสร้าง
    └── asset_dashboard.xml                  # ❌ ต้องแก้ไข
```

---

## 🐛 Troubleshooting

### ถ้า CSS ไม่โหลด:
```bash
# Clear Odoo assets
sudo -u odoo19 rm -rf /opt/odoo19/.local/share/Odoo/filestore/odoo19/assets/*

# Restart Odoo
sudo systemctl restart odoo19

# Clear browser cache
Ctrl + Shift + R
```

### ถ้า Dashboard ไม่แสดงถูกต้อง:
1. เช็ค browser console (F12) หา CSS errors
2. Verify CSS file path: `/school_asset_management/static/src/css/dashboard_minimal.css`
3. เช็ค `__manifest__.py` มี 'assets' section หรือไม่
4. Upgrade module อีกครั้ง

---

## 📸 Expected Result

Dashboard จะมีลักษณะ:
- 🎨 **สี soft pastel** แทน Bootstrap colors
- 🔲 **Cards มุมมน** พร้อม gradient backgrounds
- ✨ **Hover effects** smooth animations
- 📱 **Responsive** ทำงานบน mobile
- 👁️ **Clean typography** อ่านง่าย สบายตา

---

## 📝 Notes

- CSS file ใช้ gradient แทน solid colors เพื่อความนุ่มนวล
- Icon wrapper ใช้ gradient เช่นกัน เพิ่มความสวยงาม
- Animation จะ fade in ทีละ card (stagger effect)
- รองรับ dark mode ถ้าต้องการเพิ่มในอนาคต

---

**Created:** 2025-10-20
**Status:** 🟡 In Progress (1/7 tasks completed)
**Author:** Claude Code Assistant
