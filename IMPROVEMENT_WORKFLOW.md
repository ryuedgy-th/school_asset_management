# 🚀 Improvement Workflow - คำสั่งสำหรับแต่ละ Phase

> **คู่มือการดำเนินงานแก้ไขและปรับปรุงระบบ**
> ใช้คู่กับ `IMPROVEMENT_PLAN.md` เพื่อดำเนินการทีละขั้นตอน

---

## ⚠️ IMPORTANT: Odoo 19 Best Practices Compliance

**ทุก task ต้องปฏิบัติตามข้อกำหนดเหล่านี้อย่างเคร่งครัด:**

### 📚 คู่มืออ้างอิง (อ่านก่อนเขียนโค้ด)

> **📖 ODOO19_BEST_PRACTICES.md** - คู่มือมาตรฐานฉบับสมบูรณ์
> อ่านและปฏิบัติตามทุกครั้งที่เขียนโค้ด

### 🔗 Official Documentation
- **Odoo 19 Developer Documentation**: https://www.odoo.com/documentation/19.0/developer.html
- **Odoo Guidelines**: https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html
- **Best Practices**: https://www.odoo.com/documentation/19.0/developer/howtos.html

### 🎯 Mandatory Requirements

#### 1. **Python Code Standards**
```python
# ✅ DO: ใช้ ORM API ของ Odoo
records = self.env['model.name'].search([('field', '=', value)])
records.write({'field': new_value})

# ❌ DON'T: ใช้ SQL โดยตรง (ยกเว้นกรณีจำเป็นมาก)
self.env.cr.execute("UPDATE ...")  # หลีกเลี่ยง

# ✅ DO: ใช้ @api decorators ที่ถูกต้อง
@api.depends('field1', 'field2')
def _compute_field(self):
    for record in self:
        record.computed_field = record.field1 + record.field2

# ✅ DO: ใช้ proper logging
import logging
_logger = logging.getLogger(__name__)
_logger.info("Message")
_logger.warning("Warning")
_logger.error("Error")

# ❌ DON'T: ใช้ print()
print("Debug")  # ห้ามใช้

# ✅ DO: Transaction safety
@api.model
def create(self, vals):
    # Odoo handles transaction automatically
    record = super().create(vals)
    record._send_notification()
    return record
```

#### 2. **Field Definitions (Odoo 19)**
```python
# ✅ DO: ใช้ fields จาก odoo.fields
from odoo import models, fields, api

class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model Description'  # บังคับใน Odoo 19

    name = fields.Char('Name', required=True, index=True)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft', required=True, copy=False)

    # Computed fields ต้องมี store=True ถ้าต้องการค้นหา
    total = fields.Float('Total', compute='_compute_total', store=True)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for record in self:
            record.total = sum(record.line_ids.mapped('amount'))
```

#### 3. **XML View Standards (Odoo 19)**
```xml
<!-- ✅ DO: Proper view structure -->
<odoo>
    <record id="view_model_form" model="ir.ui.view">
        <field name="name">model.name.form</field>
        <field name="model">model.name</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <button name="action_confirm" type="object"
                            string="Confirm" class="oe_highlight"
                            invisible="state != 'draft'"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" placeholder="Name..."/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="field1"/>
                        </group>
                        <group>
                            <field name="field2"/>
                        </group>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
</odoo>

<!-- ✅ DO: List view (ไม่ใช่ tree) -->
<record id="view_model_list" model="ir.ui.view">
    <field name="name">model.name.list</field>
    <field name="model">model.name</field>
    <field name="arch" type="xml">
        <list>
            <field name="name"/>
            <field name="state" widget="badge"/>
        </list>
    </field>
</record>

<!-- ❌ DON'T: ใช้ <tree> tag (deprecated in Odoo 19) -->
<tree>...</tree>  <!-- เปลี่ยนเป็น <list> -->
```

#### 4. **Security (ir.model.access.csv)**
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_model_user,model.user,model_model_name,base.group_user,1,1,1,0
access_model_manager,model.manager,model_model_name,base.group_system,1,1,1,1
```

#### 5. **Controller Standards**
```python
from odoo import http
from odoo.http import request

class MyController(http.Controller):

    # ✅ DO: Proper route definition
    @http.route('/my/route', type='http', auth='public',
                methods=['GET', 'POST'], csrf=False, website=True)
    def my_route(self, **kwargs):
        # ✅ Use request.env for database access
        records = request.env['model.name'].sudo().search([])

        # ✅ Return proper response
        return request.render('module.template', {
            'records': records
        })

    # ✅ DO: JSON controller
    @http.route('/my/json', type='json', auth='user')
    def my_json_route(self, **kwargs):
        return {
            'success': True,
            'data': []
        }
```

#### 6. **JavaScript Standards (Odoo 19)**
```javascript
// ✅ DO: Use Odoo's JavaScript framework
/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class MyComponent extends Component {
    static template = "my_module.MyTemplate";

    setup() {
        super.setup();
        // Your setup code
    }
}

registry.category("actions").add("my_action", MyComponent);

// ✅ DO: Legacy frontend (if needed)
odoo.define('module_name.ClassName', function(require) {
    'use strict';

    var core = require('web.core');
    var _t = core._t;

    // Your code
});
```

#### 7. **Email Templates**
```xml
<!-- ✅ DO: Proper email template structure -->
<odoo>
    <record id="email_template_id" model="mail.template">
        <field name="name">Template Name</field>
        <field name="model_id" ref="model_model_name"/>
        <field name="subject">Subject: ${object.name}</field>
        <field name="email_from">${(object.company_id.email or '')|safe}</field>
        <field name="email_to">${object.partner_id.email}</field>
        <field name="body_html" type="html">
            <div style="font-family: Arial, sans-serif;">
                <p>Hello ${object.partner_id.name},</p>
                <p>Your content here...</p>
            </div>
        </field>
    </record>
</odoo>
```

#### 8. **Testing Requirements**
```python
# ✅ DO: Write tests for critical functions
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestMyModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Model = self.env['my.model']

    def test_create_record(self):
        record = self.Model.create({'name': 'Test'})
        self.assertTrue(record)
        self.assertEqual(record.name, 'Test')
```

#### 9. **Performance Best Practices**
```python
# ✅ DO: Batch operations
records.write({'field': value})  # แทน loop

# ✅ DO: Prefetch data
self.mapped('related_id.field')  # ดึงข้อมูลแบบ batch

# ✅ DO: Use search_read for list data
data = model.search_read([domain], ['field1', 'field2'])

# ❌ DON'T: Loop with search inside
for item in items:
    related = self.env['other.model'].search([('id', '=', item.id)])  # N+1 query

# ✅ DO: Use mapped/filtered
values = records.mapped('field_name')
filtered = records.filtered(lambda r: r.state == 'done')
```

#### 10. **Module Structure**
```
my_module/
├── __init__.py                 # Import submodules
├── __manifest__.py             # Module metadata
├── models/
│   ├── __init__.py
│   └── model_name.py
├── views/
│   └── model_views.xml
├── security/
│   ├── security.xml            # Groups, rules
│   └── ir.model.access.csv     # Access rights
├── data/
│   └── data.xml                # Demo/default data
├── controllers/
│   ├── __init__.py
│   └── main.py
├── static/
│   ├── src/
│   │   ├── js/
│   │   ├── css/
│   │   └── xml/
│   └── description/
│       ├── icon.png
│       └── index.html
└── tests/
    ├── __init__.py
    └── test_model.py
```

### 🔒 Security Checklist
- [ ] ใช้ `sudo()` เฉพาะที่จำเป็น และมี security check
- [ ] Validate user input ทุกครั้ง
- [ ] ใช้ `mapped()` แทนการ loop เพื่อป้องกัน SQL injection
- [ ] Set proper `groups_id` ใน field definitions
- [ ] ใช้ `@api.constrains` สำหรับ business rules
- [ ] Log security-related events

### 📝 Code Quality Standards
- [ ] Follow PEP 8 for Python code
- [ ] Use meaningful variable names (English)
- [ ] Add docstrings to all classes and methods
- [ ] Comment complex logic
- [ ] No unused imports or variables
- [ ] Handle exceptions properly
- [ ] Use translation functions `_()` for user-facing strings

### 🧪 Testing Requirements (Before Commit)
```bash
# Run Odoo with tests
odoo-bin -d database -u module_name --test-enable --stop-after-init

# Check for Python errors
flake8 module_name/

# Check for JavaScript errors (browser console)
```

---

## 📋 Phase 1: CRITICAL FIXES (ต้องทำก่อน Production)

### ⏱️ เวลาโดยประมาณ: 4-6 ชั่วโมง

---

### 🔴 Task 1.1: Implement Redis for Rate Limiting

**📍 ปัญหา:**
- `SignatureSecurityHelper` ใน `models/security_helpers.py` ใช้ in-memory dictionary
- ไม่ทำงานใน Production (multi-worker environment)
- Attacker สามารถ bypass rate limiting ได้

**🎯 เป้าหมาย:**
- แทนที่ in-memory storage ด้วย Redis
- รองรับ multi-process/multi-worker environment
- เก็บ rate limiting data แบบ persistent

**💬 คำสั่ง Prompt:**
```
แก้ไขระบบ Rate Limiting ใน models/security_helpers.py โดย:

⚠️ ODOO 19 BEST PRACTICES REQUIREMENTS:
- ใช้ ORM API เท่านั้น (ไม่ใช้ raw SQL)
- ใช้ logging.getLogger(__name__) แทน print()
- เพิ่ม docstrings ทุก method (Google style)
- Follow PEP 8 coding standards
- Handle exceptions ด้วย try-except และ log errors
- ใช้ @api.model decorator ถ้าเป็น class method
- เพิ่ม type hints สำหรับ parameters (Python 3.9+)

IMPLEMENTATION REQUIREMENTS:

1. เปลี่ยนจาก in-memory dictionary เป็น Redis backend
2. เพิ่ม Redis connection management ด้วย connection pooling
3. เพิ่ม fallback mechanism ถ้า Redis ไม่พร้อมใช้งาน (log warning + อนุญาตชั่วคราว)
4. ใช้ Redis key pattern: "rate_limit:{ip}:{endpoint}"
5. ตั้ง TTL ให้ key หมดอายุอัตโนมัติ (1 hour)
6. เพิ่ม configuration ใน ir.config_parameter สำหรับ Redis connection
7. เพิ่ม docstring และ comments อธิบายการทำงาน

ODOO-SPECIFIC REQUIREMENTS:
- ใช้ self.env['ir.config_parameter'].get_param() สำหรับ config
- Log ทุก rate limiting event ด้วย self.env['security_audit_log'].create()
- ใช้ Odoo's @api.model decorator สำหรับ utility methods
- Transaction safety: ใช้ self.env.cr.commit() เฉพาะที่จำเป็น

CODE STRUCTURE:
```python
import logging
from typing import Optional, Tuple
import redis
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SignatureSecurityHelper:
    """Redis-based rate limiting for signature endpoints.

    Implements distributed rate limiting using Redis as shared storage
    to work correctly in multi-worker production environments.
    """

    def __init__(self, env):
        """Initialize Redis connection with fallback mechanism."""
        pass

    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection pooling.

        Returns:
            redis.Redis: Redis client instance or None if unavailable
        """
        pass

    @api.model
    def check_rate_limit(self, ip_address: str, endpoint: str) -> Tuple[bool, str]:
        """Check if request is within rate limit.

        Args:
            ip_address: Client IP address
            endpoint: API endpoint being accessed

        Returns:
            Tuple[bool, str]: (is_allowed, error_message)
        """
        pass
```

TESTING REQUIREMENTS:
- ทดสอบใน single worker (development)
- ทดสอบใน multi-worker (production with gunicorn/uwsgi)
- ทดสอบ Redis unavailable (fallback mode)
- ทดสอบ rate limit exceeded scenario

CONFIGURATION:
- redis_host (default: localhost)
- redis_port (default: 6379)
- redis_db (default: 0)
- redis_password (optional)
- rate_limit_requests (default: 10)
- rate_limit_window (default: 3600 seconds)
```

**📁 ไฟล์ที่ต้องแก้:**
- `models/security_helpers.py` - เปลี่ยน storage backend
- `__manifest__.py` - เพิ่ม Redis config (ถ้าจำเป็น)

**✅ Definition of Done:**
- [ ] Redis connection working with connection pool
- [ ] Rate limiting ทำงานข้าม multiple workers
- [ ] Fallback mechanism ทำงานเมื่อ Redis down
- [ ] TTL auto-cleanup ทำงานถูกต้อง
- [ ] ทดสอบใน multi-worker environment
- [ ] Security audit log บันทึก rate limit events

---

### 🔴 Task 1.2: Add Missing External Dependencies

**📍 ปัญหา:**
- `__manifest__.py` ไม่ได้ระบุ `Pillow` และ `redis`
- โมดูลอาจติดตั้งไม่สำเร็จหรือ runtime error

**🎯 เป้าหมาย:**
- ระบุ external dependencies ที่จำเป็นทั้งหมด
- ให้ Odoo ตรวจสอบและแจ้งเตือนก่อนติดตั้ง

**💬 คำสั่ง Prompt:**
```
แก้ไขไฟล์ __manifest__.py โดยเพิ่ม external dependencies:

⚠️ ODOO 19 MANIFEST BEST PRACTICES:
- ใช้ Python dictionary format ที่ถูกต้อง
- เรียงลำดับ keys ตาม Odoo conventions
- เพิ่ม comments อธิบาย dependencies
- ระบุ version constraints ชัดเจน
- ตรวจสอบ syntax ด้วย Python parser

REQUIRED STRUCTURE:
{
    'name': 'Module Name',
    'version': '19.0.1.0.0',
    'category': 'Category',
    'summary': 'Short description',
    'description': """
        Long description
    """,
    'author': 'Author Name',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],  # Odoo modules
    'external_dependencies': {
        'python': ['Pillow', 'redis'],  # Python packages
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [...],
        'web.assets_frontend': [...],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

IMPLEMENTATION:

1. เพิ่ม section 'external_dependencies' ถ้ายังไม่มี
2. ระบุ Python libraries พร้อม version constraints:
   - Pillow>=9.0.0 (สำหรับ signature watermark)
   - redis>=4.5.0 (สำหรับ rate limiting)

3. เพิ่ม inline comments อธิบายการใช้งาน:
   'external_dependencies': {
       'python': [
           'Pillow',  # Image processing for signature watermarks
           'redis',   # Distributed rate limiting in multi-worker env
       ],
   },

4. ตรวจสอบว่ามี dependencies อื่นที่ยังไม่ได้ระบุหรือไม่:
   - ดู import statements ในโค้ด Python ทั้งหมด
   - ตรวจสอบว่า library ไหนเป็น external (ไม่ใช่ Python standard library)

5. Validation:
   - ทดสอบด้วย: python3 -c "import ast; ast.parse(open('__manifest__.py').read())"
   - ตรวจสอบว่าไม่มี syntax errors

หลังจากแก้ไขแล้ว:
- แสดงผล __manifest__.py ที่แก้ไขแล้วทั้งหมด
- อธิบายการเปลี่ยนแปลงที่ทำ
- Validate syntax
```

**📁 ไฟล์ที่ต้องแก้:**
- `__manifest__.py`

**✅ Definition of Done:**
- [ ] External dependencies ถูกเพิ่มใน `__manifest__.py`
- [ ] Pillow และ redis ระบุพร้อม version requirements
- [ ] มี comments อธิบายการใช้งาน
- [ ] Syntax ถูกต้อง (Python dict format)
- [ ] ทดสอบติดตั้งโมดูลใหม่ (uninstall → install)

---

## 📋 Phase 2: HIGH-PRIORITY IMPROVEMENTS

### ⏱️ เวลาโดยประมาณ: 6-8 ชั่วโมง

---

### 🟠 Task 2.1: Enhance Token Security (HMAC-based)

**📍 ปัญหา:**
- ใช้ random token ธรรมดา (UUID) ไม่มี signature verification
- ไม่มี expiration time → token ใช้ได้ตลอดไป
- ไม่มีการตรวจสอบ CSRF (csrf=False ใน controller)

**🎯 เป้าหมาย:**
- เปลี่ยนเป็น HMAC-SHA256 token ที่มี signature
- เพิ่ม token expiration (24 ชั่วโมง)
- เพิ่มการตรวจสอบ HTTP Referer

**💬 คำสั่ง Prompt:**
```
ปรับปรุงระบบ Token Security ในโมดูล school_asset_management:

⚠️ ODOO 19 BEST PRACTICES (ต้องปฏิบัติตาม):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Python Standards:
   - ใช้ logging.getLogger(__name__) แทน print()
   - เพิ่ม docstrings (Google style) ทุก method
   - ใช้ type hints: def method(self, token: str) -> Tuple[bool, str]
   - Follow PEP 8 (line length, naming conventions)
   - Handle exceptions properly with try-except

2. Odoo ORM:
   - ใช้ @api.depends สำหรับ computed fields
   - ใช้ @api.model สำหรับ utility methods
   - ไม่ใช้ raw SQL (ใช้ ORM เท่านั้น)
   - ใช้ self.env['model.name'] สำหรับเข้าถึง models

3. Field Definitions:
   - ทุก field ต้องมี string parameter
   - ใช้ help parameter สำหรับอธิบาย field
   - ใช้ copy=False สำหรับ fields ที่ไม่ควร duplicate
   - ใช้ index=True สำหรับ fields ที่ใช้ search บ่อย

4. Security:
   - Validate input ทุกครั้ง
   - Log security events ด้วย self.env['security_audit_log'].create()
   - ใช้ sudo() เฉพาะที่จำเป็น + มี validation
   - ไม่เก็บ sensitive data เป็น plain text

5. Configuration:
   - ใช้ self.env['ir.config_parameter'].get_param() สำหรับ config
   - ไม่ hardcode values
   - มี fallback values ที่เหมาะสม

6. Translation:
   - ใช้ _() สำหรับ user-facing strings
   - from odoo import _, _lt สำหรับ translations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PART 1: Models (Student Assignment)
ไฟล์: models/asset_student_assignment.py

1. เพิ่มฟิลด์ใหม่:
   - token_expires_at = fields.Datetime('Token Expiration')
   - token_created_at = fields.Datetime('Token Created')

2. แก้ไขเมธอด generate_signature_token():
   - แทนที่ uuid4() ด้วย HMAC-SHA256 token
   - Token format: HMAC(secret_key, assignment_id + timestamp + salt)
   - ตั้งค่า token_expires_at = now + 24 hours
   - บันทึก token_created_at
   - ใช้ Odoo's get_param() เพื่อดึง secret key จาก ir.config_parameter

3. เพิ่มเมธอดใหม่ validate_token(token):
   - ตรวจสอบ HMAC signature
   - ตรวจสอบ expiration time
   - ตรวจสอบว่า token ยังไม่ถูกใช้ (checkout_signature_date is False)
   - Return (is_valid, error_message)

PART 2: Models (Teacher Assignment)
ไฟล์: models/asset_teacher_assignment.py
- ทำเหมือนกับ Student Assignment

PART 3: Controllers
ไฟล์: controllers/main.py

1. เพิ่ม helper method _validate_referer(request):
   - ตรวจสอบ HTTP_REFERER header
   - อนุญาตเฉพาะ domain ของเรา
   - Return True/False

2. แก้ไขทุกเมธอดที่รับ token:
   - checkout_signature()
   - teacher_checkout_signature()
   - damage_report_signature()
   - teacher_damage_report_signature()

   ให้เพิ่มการตรวจสอบ:
   a) เรียก assignment.validate_token(token)
   b) เรียก _validate_referer(request)
   c) ถ้าไม่ผ่าน → return error page พร้อม message
   d) ถ้าผ่าน → ดำเนินการต่อ

3. เพิ่ม error template:
   - templates/token_error_page.xml
   - แสดงข้อความ error (expired, invalid, used)
   - แสดง contact information

Requirements:
- ใช้ hmac และ hashlib จาก Python standard library
- Secret key เก็บใน ir.config_parameter (key: 'school_asset.signature_secret')
- Auto-generate secret ถ้ายังไม่มี (ตอนติดตั้งโมดูล)
- Log ทุก token validation failure ไปยัง security_audit_log

ตรวจสอบ:
- Token หมดอายุหลัง 24 ชั่วโมง
- Token ที่ใช้แล้วจะใช้ซ้ำไม่ได้
- Referer checking ทำงานถูกต้อง
```

**📁 ไฟล์ที่ต้องแก้:**
- `models/asset_student_assignment.py`
- `models/asset_teacher_assignment.py`
- `controllers/main.py`
- `templates/token_error_page.xml` (สร้างใหม่)
- `data/default_config.xml` (สร้างใหม่ - สำหรับ secret key)

**✅ Definition of Done:**
- [ ] HMAC-SHA256 token generation working
- [ ] Token expiration checking (24 hours)
- [ ] Token validation ป้องกัน reuse
- [ ] HTTP Referer validation
- [ ] Error page แสดงผลถูกต้อง
- [ ] Secret key auto-generated on install
- [ ] Security audit logging
- [ ] ทดสอบ expired token → error
- [ ] ทดสอบ used token → error
- [ ] ทดสอบ wrong referer → error

---

### 🟠 Task 2.2: Create Token Validation Decorator

**📍 ปัญหา:**
- Logic การตรวจสอบ token ซ้ำซ้อนในหลายเมธอด
- Code duplication ทำให้ maintain ยาก
- ถ้าจะแก้ logic ต้องแก้หลายที่

**🎯 เป้าหมาย:**
- สร้าง Python decorator สำหรับ token validation
- ลดโค้ดซ้ำซ้อน (DRY principle)
- ทำให้แก้ไข logic ได้ที่เดียว

**💬 คำสั่ง Prompt:**
```
สร้าง Token Validation Decorator ใน controllers/main.py:

⚠️ อ่าน ODOO19_BEST_PRACTICES.md ก่อนเขียนโค้ด (Section: Controller Standards, Python Standards)

MANDATORY COMPLIANCE:
- ใช้ logging.getLogger(__name__)
- เพิ่ม docstrings (Google style)
- Type hints สำหรับ parameters
- Proper exception handling
- Input validation ทุก parameter
- Security audit logging

PART 1: สร้าง Decorator
ตำแหน่ง: ด้านบนของ class AssetSignatureController

def validate_signature_token(model_name, token_param='token',
                             assignment_param='assignment'):
    """
    Decorator สำหรับตรวจสอบ signature token

    Args:
        model_name: 'asset.student.assignment' หรือ 'asset.teacher.assignment'
        token_param: ชื่อ parameter ของ token (default: 'token')
        assignment_param: ชื่อ parameter ที่จะ inject assignment record

    Returns:
        Decorator function ที่ตรวจสอบ token และ inject assignment

    Raises:
        Redirect to error page ถ้า token invalid/expired/used
    """

    การทำงาน:
    1. ดึง token จาก kwargs[token_param]
    2. ค้นหา assignment record จาก model_name ที่มี token นี้
    3. เรียก assignment.validate_token(token)
    4. ตรวจสอบ HTTP Referer
    5. ถ้าผ่าน: inject assignment เข้า kwargs[assignment_param]
    6. ถ้าไม่ผ่าน: redirect ไป /signature/error พร้อม error message
    7. เรียก original function พร้อม assignment

PART 2: Refactor Controller Methods
แก้ไขเมธอดเหล่านี้ให้ใช้ decorator:

@validate_signature_token('asset.student.assignment')
def checkout_signature(self, token, assignment=None, **kwargs):
    # ไม่ต้องตรวจสอบ token อีก เพราะ decorator ทำให้แล้ว
    # ใช้ assignment ที่ decorator inject มาได้เลย
    ...

@validate_signature_token('asset.teacher.assignment')
def teacher_checkout_signature(self, token, assignment=None, **kwargs):
    ...

@validate_signature_token('asset.student.assignment')
def damage_report_signature(self, token, assignment=None, **kwargs):
    ...

@validate_signature_token('asset.teacher.assignment')
def teacher_damage_report_signature(self, token, assignment=None, **kwargs):
    ...

PART 3: Error Handler Route
เพิ่ม route สำหรับแสดง error:

@http.route('/signature/error', type='http', auth='public', csrf=False)
def signature_error(self, error_type='invalid', **kwargs):
    """แสดงหน้า error สำหรับ token issues"""
    return request.render('school_asset_management.token_error_page', {
        'error_type': error_type,
        'error_messages': {
            'expired': 'ลิงก์หมดอายุแล้ว (เกิน 24 ชั่วโมง)',
            'invalid': 'ลิงก์ไม่ถูกต้องหรือถูกแก้ไข',
            'used': 'ลิงก์นี้ถูกใช้งานไปแล้ว',
            'not_found': 'ไม่พบข้อมูลการมอบหมาย',
        }
    })

Requirements:
- ใช้ functools.wraps เพื่อรักษา function metadata
- Log ทุก validation failure
- รองรับทั้ง student และ teacher assignments
- Error handling ที่ชัดเจน

ผลลัพธ์:
- โค้ดสั้นลง ประมาณ 40-50 บรรทัด
- แก้ logic ได้ที่ decorator เพียงที่เดียว
- เพิ่ม validation logic ใหม่ได้ง่าย
```

**📁 ไฟล์ที่ต้องแก้:**
- `controllers/main.py`

**✅ Definition of Done:**
- [ ] Decorator ทำงานถูกต้อง
- [ ] ใช้งานได้กับทั้ง student และ teacher
- [ ] Assignment record ถูก inject เข้า method
- [ ] Error handling ครบถ้วน
- [ ] Code ลดลงอย่างน้อย 40 บรรทัด
- [ ] ทดสอบทุก endpoint ที่ใช้ decorator
- [ ] Logging ทำงานถูกต้อง

---

### 🟠 Task 2.3: Complete PDPA Email Templates

**📍 ปัญหา:**
- มี `TODO` ใน `models/asset_data_request.py` สำหรับ email templates
- ระบบ Data Subject Request ยังไม่มีการแจ้งเตือนทางอีเมล
- ไม่เป็นไปตาม PDPA best practices

**🎯 เป้าหมาย:**
- สร้างเทมเพลตอีเมลครบถ้วนสำหรับทุก stage ของ DSR
- ส่งอีเมลอัตโนมัติเมื่อมีการเปลี่ยนสถานะ

**💬 คำสั่ง Prompt:**
```
⚠️ อ่าน ODOO19_BEST_PRACTICES.md sections: Email Templates, Python Standards

เพิ่ม Email Templates สำหรับ Data Subject Request (DSR):

PART 1: สร้าง Email Templates
ไฟล์: data/dsr_email_templates.xml

สร้าง email template ดังนี้:

1. email_dsr_received (เมื่อได้รับคำขอ)
   Subject: "[MYIS] ได้รับคำขอใช้สิทธิ์ตาม PDPA - #{reference}"
   Content:
   - ยืนยันว่าได้รับคำขอแล้ว
   - แสดง request type ที่ขอ
   - แจ้งระยะเวลาดำเนินการ (30 วัน)
   - แจ้งว่าจะติดต่อกลับเพื่อ verify identity

2. email_dsr_identity_verified (เมื่อยืนยันตัวตนสำเร็จ)
   Subject: "[MYIS] ยืนยันตัวตนสำเร็จ - #{reference}"
   Content:
   - แจ้งว่าได้รับการยืนยันตัวตนแล้ว
   - กำลังดำเนินการตามคำขอ
   - แสดง deadline

3. email_dsr_in_progress (เมื่อเริ่มดำเนินการ)
   Subject: "[MYIS] กำลังดำเนินการตามคำขอ - #{reference}"
   Content:
   - แจ้งว่ากำลังดำเนินการ
   - ประมาณการระยะเวลา
   - ช่องทางติดต่อสอบถาม

4. email_dsr_completed (เมื่อเสร็จสิ้น)
   Subject: "[MYIS] ดำเนินการตามคำขอเสร็จสิ้น - #{reference}"
   Content:
   - แจ้งว่าดำเนินการเสร็จแล้ว
   - สรุปผลการดำเนินการ
   - ขั้นตอนถัดไป (ถ้าม�)
   - สิทธิ์ในการร้องเรียนถ้าไม่พอใจ

5. email_dsr_rejected (เมื่อปฏิเสธคำขอ)
   Subject: "[MYIS] แจ้งผลการพิจารณาคำขอ - #{reference}"
   Content:
   - แจ้งว่าไม่สามารถดำเนินการได้
   - เหตุผลที่ปฏิเสธ
   - สิทธิ์ในการอุทธรณ์
   - ช่องทางร้องเรียน

6. email_dsr_deadline_warning (แจ้งเตือนใกล้ครบกำหนด)
   Subject: "[MYIS INTERNAL] แจ้งเตือน: คำขอ DSR ใกล้ครบกำหนด - #{reference}"
   Content: (ส่งหา DPO/Staff)
   - แจ้งว่าคำขอใกล้ครบ 30 วันแล้ว
   - วันที่ครบกำหนด
   - link ไปยัง record

Design:
- ใช้ MYIS brand colors (Purple #574193, Green #6ab42d)
- Responsive HTML email template
- รองรับทั้งภาษาไทยและอังกฤษ
- มี footer พร้อม contact information

PART 2: Update Model
ไฟล์: models/asset_data_request.py

1. ลบ TODO comments
2. เพิ่มเมธอด _send_email(template_xmlid):
   - ดึง template จาก xmlid
   - ส่งอีเมลไปยัง requester_email
   - บันทึก log ลงใน mail.message

3. เพิ่มการเรียก _send_email ใน:
   - create() → ส่ง email_dsr_received
   - action_verify_identity() → ส่ง email_dsr_identity_verified
   - action_start_processing() → ส่ง email_dsr_in_progress
   - action_complete() → ส่ง email_dsr_completed
   - action_reject() → ส่ง email_dsr_rejected

4. เพิ่ม scheduled action:
   - ชื่อ: "DSR Deadline Warning"
   - ทำงานทุกวัน
   - หา records ที่เหลือเวลา 3 วัน
   - ส่ง email_dsr_deadline_warning หา staff

PART 3: Update __manifest__.py
เพิ่ม data/dsr_email_templates.xml เข้าไปใน 'data': []

Requirements:
- Email ต้องเป็น HTML responsive
- มี plain text fallback
- ทดสอบส่งอีเมลได้จริง
- Log ทุกครั้งที่ส่งอีเมล
```

**📁 ไฟล์ที่ต้องแก้:**
- `data/dsr_email_templates.xml` (สร้างใหม่)
- `models/asset_data_request.py`
- `__manifest__.py`

**✅ Definition of Done:**
- [ ] สร้าง email templates ครบ 6 แบบ
- [ ] Email ใช้ MYIS brand colors
- [ ] Responsive design ทำงานบนมือถือ
- [ ] เมธอด _send_email ทำงานถูกต้อง
- [ ] Email ถูกส่งอัตโนมัติตาม state changes
- [ ] Scheduled action สำหรับ deadline warning
- [ ] ทดสอบส่งอีเมลได้จริง
- [ ] TODO comments ถูกลบออกหมด
- [ ] Mail logging ทำงานถูกต้อง

---

## 📋 Phase 3: RELIABILITY & BEST PRACTICES

### ⏱️ เวลาโดยประมาณ: 4-6 ชั่วโมง

---

### 🟡 Task 3.1: Bundle Font File with Module

**📍 ปัญหา:**
- `signature_watermark.py` เรียกใช้ Font จาก system path (`/usr/share/fonts/`)
- ไม่เสถียร อาจไม่มี font ในบาง environment
- ทำให้ watermark ล้มเหลว

**🎯 เป้าหมาย:**
- แนบไฟล์ Font เข้ากับโมดูล
- ใช้ Font จากภายในโมดูล
- เพิ่ม error handling

**💬 คำสั่ง Prompt:**
```
⚠️ อ่าน ODOO19_BEST_PRACTICES.md sections: Python Standards, Module Structure

แก้ไขการจัดการ Font ใน Signature Watermark:

PART 1: เพิ่มไฟล์ Font
1. สร้างโฟลเดอร์ data/fonts/
2. คัดลอก DejaVuSans-Bold.ttf เข้าไปในโฟลเดอร์
3. เพิ่ม __init__.py ใน data/ (ถ้ายังไม่มี)

PART 2: แก้ไข Watermark Code
ไฟล์: models/signature_watermark.py

เปลี่ยนจาก:
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

เป็น:
def _get_font_path():
    """Get bundled font path from module"""
    module_path = os.path.dirname(os.path.dirname(__file__))
    font_path = os.path.join(module_path, 'data', 'fonts', 'DejaVuSans-Bold.ttf')

    if not os.path.exists(font_path):
        # Fallback to system font
        system_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if os.path.exists(system_font):
            return system_font
        # Last resort: default PIL font
        return None

    return font_path

เพิ่ม Error Handling:
try:
    font_path = _get_font_path()
    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        _logger.warning("Font not found, using default PIL font")
        font = ImageFont.load_default()
except Exception as e:
    _logger.error(f"Error loading font: {e}")
    font = ImageFont.load_default()

PART 3: Update __manifest__.py
เพิ่มไฟล์ font ใน 'data': []
'data': [
    'data/fonts/DejaVuSans-Bold.ttf',
    ...
]

PART 4: เพิ่ม License File
สร้าง data/fonts/LICENSE.txt
- ใส่ license ของ DejaVu Fonts (Free license)
- อ้างอิงที่มา

Requirements:
- Font ต้องทำงานใน Docker container
- Error handling ไม่ให้ระบบ crash
- Log warning ถ้าต้องใช้ default font
- ทดสอบใน environment ที่ไม่มี system fonts
```

**📁 ไฟล์ที่ต้องแก้:**
- `models/signature_watermark.py`
- `data/fonts/DejaVuSans-Bold.ttf` (สร้างใหม่)
- `data/fonts/LICENSE.txt` (สร้างใหม่)
- `__manifest__.py`

**✅ Definition of Done:**
- [ ] Font file ถูก bundle เข้ากับโมดูล
- [ ] Code ใช้ bundled font เป็น primary
- [ ] Fallback mechanism ทำงานถูกต้อง
- [ ] Error handling ไม่ให้ระบบ crash
- [ ] License file ถูกเพิ่ม
- [ ] ทดสอบใน environment ที่ไม่มี system fonts
- [ ] Watermark ยังคงสวยงามเหมือนเดิม

---

### 🟡 Task 3.2: Refactor JavaScript Signature Pad Code

**📍 ปัญหา:**
- โค้ด JavaScript ซ้ำซ้อนใน 5 ไฟล์
- แต่ละไฟล์มี logic เกือบเหมือนกัน 80%
- แก้ไข bug ต้องแก้หลายไฟล์

**🎯 เป้าหมาย:**
- สร้าง Base Class สำหรับ SignaturePad
- Extend จาก Base Class
- ลดโค้ดซ้ำซ้อน

**💬 คำสั่ง Prompt:**
```
⚠️ อ่าน ODOO19_BEST_PRACTICES.md sections: JavaScript Standards

Refactor JavaScript Signature Pad เป็น OOP Pattern:

PART 1: สร้าง Base Class
ไฟล์: static/src/js/base_signature_pad.js

สร้าง ES6 class BaseSignaturePad ที่มี:

class BaseSignaturePad {
    constructor(config) {
        // config: {
        //   canvasId: 'signature-pad',
        //   clearBtnId: 'clear-button',
        //   formId: 'signature-form',
        //   checkboxIds: [],  // checkbox ที่ต้อง validate
        //   onSubmitValidate: function,  // custom validation
        // }
        this.config = config;
        this.canvas = null;
        this.signaturePad = null;
        this.init();
    }

    init() {
        // Initialize canvas
        // Setup SignaturePad library
        // Bind events
        // Setup form submission
    }

    setupCanvas() { ... }

    bindEvents() {
        // Clear button
        // Window resize
        // Form submit
    }

    validateForm() {
        // Check signature drawn
        // Check required checkboxes
        // Call custom validation
        return { valid: true/false, errors: [] }
    }

    handleSubmit(event) {
        // Validate
        // Convert to base64
        // Submit form
    }

    clear() { ... }

    resizeCanvas() { ... }

    toDataURL() {
        return this.signaturePad.toDataURL('image/png');
    }
}

PART 2: Refactor แต่ละไฟล์ให้ใช้ Base Class

1. static/src/js/signature_pad.js (Student Checkout)
class StudentSignaturePad extends BaseSignaturePad {
    constructor() {
        super({
            canvasId: 'signature-pad',
            clearBtnId: 'clear-button',
            formId: 'signature-form',
            checkboxIds: [
                'consent_privacy_policy',
                'consent_data_collection',
                'consent_liability_waiver'
            ],
            onSubmitValidate: function() {
                // Custom validation สำหรับ student
                return { valid: true, errors: [] };
            }
        });
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    new StudentSignaturePad();
});

2. static/src/js/teacher_signature_pad.js (Teacher Checkout)
class TeacherSignaturePad extends BaseSignaturePad {
    constructor() {
        super({
            canvasId: 'signature-pad',
            clearBtnId: 'clear-button',
            formId: 'signature-form',
            checkboxIds: ['consent_privacy_policy'],
        });
    }
}

3. static/src/js/damage_signature_pad.js (Student Damage)
class StudentDamageSignaturePad extends BaseSignaturePad { ... }

4. static/src/js/teacher_damage_signature_pad.js (Teacher Damage)
class TeacherDamageSignaturePad extends BaseSignaturePad { ... }

5. static/src/js/inspection_damage_signature_pad.js (Inspection)
class InspectionSignaturePad extends BaseSignaturePad { ... }

PART 3: Update Templates
แก้ไข templates ให้โหลด base_signature_pad.js ก่อน:

<script src="/school_asset_management/static/src/js/base_signature_pad.js"></script>
<script src="/school_asset_management/static/src/js/signature_pad.js"></script>

PART 4: Update __manifest__.py
เพิ่ม base_signature_pad.js ใน assets

'assets': {
    'web.assets_frontend': [
        'school_asset_management/static/src/js/base_signature_pad.js',
        'school_asset_management/static/src/js/signature_pad.js',
        ...
    ]
}

Requirements:
- ใช้ ES6 class syntax
- รองรับ browser เก่า (transpile ถ้าจำเป็น)
- ไม่เปลี่ยนพฤติกรรมที่มีอยู่
- เพิ่ม JSDoc comments
- ทดสอบทุก signature page

Expected Results:
- โค้ดลดลงจาก ~500 บรรทัด เหลือ ~200 บรรทัด
- แก้ไข logic ได้ที่ base class เพียงที่เดียว
- เพิ่ม feature ใหม่ได้ง่าย
```

**📁 ไฟล์ที่ต้องแก้:**
- `static/src/js/base_signature_pad.js` (สร้างใหม่)
- `static/src/js/signature_pad.js`
- `static/src/js/teacher_signature_pad.js`
- `static/src/js/damage_signature_pad.js`
- `static/src/js/teacher_damage_signature_pad.js`
- `static/src/js/inspection_damage_signature_pad.js`
- `templates/*.xml` (update script tags)
- `__manifest__.py`

**✅ Definition of Done:**
- [ ] Base class สร้างเสร็จ
- [ ] ทุกไฟล์ refactor เป็น inheritance
- [ ] โค้ดลดลงอย่างน้อย 60%
- [ ] ทดสอบทุก signature page ทำงานถูกต้อง
- [ ] Form validation ยังคงเหมือนเดิม
- [ ] JSDoc comments ครบถ้วน
- [ ] ไม่มี console errors

---

## 📋 Phase 4: CODE CLEANUP

### ⏱️ เวลาโดยประมาณ: 2-3 ชั่วโมง

---

### 🔵 Task 4.1: Remove Obsolete Files and Clean Up Data

**📍 ปัญหา:**
- มีไฟล์เก่าที่ไม่ใช้งาน (_old.xml, .backup)
- ข้อมูลตัวอย่างไม่สมบูรณ์ (XXX-XXX-XXXX)
- Access rights ของ dashboard ให้สิทธิ์เกินจำเป็น

**🎯 เป้าหมาย:**
- ลบไฟล์ที่ไม่ใช้งาน
- แก้ไขข้อมูลตัวอย่าง
- ปรับ access rights

**💬 คำสั่ง Prompt:**
```
⚠️ อ่าน ODOO19_BEST_PRACTICES.md sections: Code Quality Standards, Module Structure

ทำความสะอาดโค้ดและข้อมูลในโมดูล:

PART 1: ลบไฟล์เก่า
ค้นหาและลบไฟล์ที่มีส่วนขยายเหล่านี้:
- *_old.xml
- *.backup
- *.backup-*

คำสั่ง:
find . -name "*_old.xml" -o -name "*.backup*"
# ตรวจสอบก่อนลบ
find . -name "*_old.xml" -o -name "*.backup*" -delete

ไฟล์ที่น่าจะลบ:
- reports/inspection_damage_report_old.xml
- static/src/js/teacher_damage_signature_pad.js.backup-*

PART 2: แก้ไขข้อมูลตัวอย่าง
ไฟล์: templates/privacy_consent.xml

ค้นหา: "XXX-XXX-XXXX"
แทนที่ด้วย: "โทร 02-123-4567" หรือเบอร์จริงของโรงเรียน

ค้นหาและแก้ไขข้อมูล placeholder อื่นๆ:
- อีเมล example@example.com → อีเมลจริง
- ที่อยู่ "Address TBD" → ที่อยู่จริง

PART 3: แก้ไข Access Rights
ไฟล์: security/ir.model.access.csv

หา record: access_asset_dashboard_user
เปลี่ยนจาก:
access_asset_dashboard_user,asset.dashboard.user,model_asset_dashboard,base.group_user,1,1,1,1

เป็น:
access_asset_dashboard_user,asset.dashboard.user,model_asset_dashboard,base.group_user,1,0,0,0
                                                                                          ^ ^ ^ ^
                                                                                          | | | unlink (ลบออก)
                                                                                          | | write (ลบออก)
                                                                                          | create (ลบออก)
                                                                                          read (เก็บไว้)

เหตุผล: Dashboard เป็น computed view ไม่ควรมีสิทธิ์ create/write/delete

PART 4: ตรวจสอบ TODO และ FIXME Comments
ค้นหา TODO/FIXME ทั้งหมด:
grep -r "TODO\|FIXME" --include="*.py" --include="*.xml" --include="*.js"

ทำรายการและตรวจสอบว่า:
- ทำเสร็จแล้ว → ลบ comment
- ยังไม่เสร็จ → เพิ่มใน IMPROVEMENT_PLAN.md

PART 5: Update __manifest__.py
ลบ reference ไปยังไฟล์ที่ถูกลบออก:
- reports/inspection_damage_report_old.xml
- (ไฟล์อื่นๆ ที่ลบ)

Requirements:
- Backup ก่อนลบไฟล์
- Commit แต่ละ part แยกกัน
- ทดสอบว่าโมดูลยังทำงานได้หลังลบไฟล์
```

**📁 ไฟล์ที่ต้องแก้:**
- `reports/inspection_damage_report_old.xml` (ลบ)
- `static/src/js/*.backup*` (ลบ)
- `templates/privacy_consent.xml`
- `security/ir.model.access.csv`
- `__manifest__.py`

**✅ Definition of Done:**
- [ ] ไฟล์เก่าถูกลบออกหมด
- [ ] ไม่มี XXX-XXX-XXXX ในโค้ด
- [ ] Access rights ของ dashboard ถูกต้อง
- [ ] TODO/FIXME ถูกจัดการหมด
- [ ] __manifest__.py อัพเดทแล้ว
- [ ] โมดูลยังทำงานได้ปกติ
- [ ] Commit history สะอาด

---

## 📊 Workflow Checklist - Overview

### Phase 1: CRITICAL (ต้องทำก่อน Production) 🔴
- [ ] Task 1.1: Redis Rate Limiting (2-3 ชม.)
- [ ] Task 1.2: External Dependencies (30 นาที)

### Phase 2: HIGH PRIORITY (ทำก่อนเพิ่ม Wizards) 🟠
- [ ] Task 2.1: HMAC Token Security (3-4 ชม.)
- [ ] Task 2.2: Token Decorator (1-2 ชม.)
- [ ] Task 2.3: PDPA Email Templates (2-3 ชม.)

### Phase 3: RELIABILITY (ควรทำ) 🟡
- [ ] Task 3.1: Bundle Font File (1-2 ชม.)
- [ ] Task 3.2: JavaScript Refactoring (3-4 ชม.)

### Phase 4: CLEANUP (ทำเมื่อมีเวลา) 🔵
- [ ] Task 4.1: Remove Obsolete Files (2-3 ชม.)

---

## 🎯 Recommended Execution Order

```
Week 1: Phase 1 (CRITICAL)
├── Day 1-2: Redis Rate Limiting + Testing
└── Day 2:   Add Dependencies + Deploy Test

Week 2: Phase 2 (HIGH)
├── Day 1:   HMAC Token Implementation
├── Day 2:   Token Decorator Refactor
└── Day 3:   PDPA Email Templates

Week 3: Phase 3 (RELIABILITY)
├── Day 1:   Bundle Font File
└── Day 2-3: JavaScript Refactoring

Week 4: Phase 4 + Testing
├── Day 1:   Code Cleanup
└── Day 2-3: Full System Testing + QA
```

---

## 🧪 Testing Checklist

หลังจากแต่ละ Phase:

### After Phase 1:
- [ ] Rate limiting works in multi-worker environment
- [ ] Module installs without missing dependencies
- [ ] Security audit logs show rate limiting events

### After Phase 2:
- [ ] HMAC tokens expire after 24 hours
- [ ] Used tokens cannot be reused
- [ ] Referer validation works
- [ ] All 6 PDPA emails sent correctly

### After Phase 3:
- [ ] Watermarks work without system fonts
- [ ] All signature pages still functional
- [ ] JavaScript has no console errors

### After Phase 4:
- [ ] No obsolete files remain
- [ ] Module passes Odoo linter
- [ ] All tests pass

---

## 📝 Notes

- **อย่ารีบพัฒนา Wizards** จนกว่า Phase 1-2 จะเสร็จสมบูรณ์
- **ทดสอบหลังทุก task** ก่อนไป task ถัดไป
- **Commit บ่อยๆ** ทุก task ที่เสร็จ
- **Backup database** ก่อนเริ่มแต่ละ Phase

---

---

## 📖 Documentation Files

ใช้เอกสารเหล่านี้ร่วมกัน:

1. **IMPROVEMENT_PLAN.md** - รายการปัญหาและลำดับความสำคัญ
2. **IMPROVEMENT_WORKFLOW.md** (ไฟล์นี้) - คำสั่ง prompt พร้อมใช้สำหรับแต่ละ task
3. **ODOO19_BEST_PRACTICES.md** - มาตรฐาน Odoo 19 ฉบับสมบูรณ์ (อ่านก่อนเขียนโค้ดทุกครั้ง)
4. **DEVELOPMENT_PLAN.md** - แผนพัฒนา Wizards (ทำหลัง Phase 1-2)

---

## ⚡ Quick Start Guide

### สำหรับ Claude Code:

```
Phase 1 Task 1.1: แก้ไข Rate Limiting
─────────────────────────────────────────
1. อ่าน ODOO19_BEST_PRACTICES.md sections: Python Standards, Performance
2. Copy prompt จาก IMPROVEMENT_WORKFLOW.md → Phase 1 → Task 1.1
3. Paste และรัน
4. ตรวจสอบ Definition of Done
5. Commit พร้อม message: "feat: Implement Redis-based rate limiting"
```

### สำหรับ Developer:

```bash
# 1. อ่านเอกสาร
cat ODOO19_BEST_PRACTICES.md

# 2. เลือก Phase และ Task
cat IMPROVEMENT_WORKFLOW.md

# 3. เริ่มทำงาน
# ... implement code ...

# 4. Test
odoo-bin -d db -u school_asset_management --test-enable

# 5. Commit
git add .
git commit -m "feat: [Task description]"
```

---

## 🚨 Critical Reminders

1. **อ่าน ODOO19_BEST_PRACTICES.md ก่อนเขียนโค้ดทุกครั้ง**
2. **ไม่มี print() statements - ใช้ _logger**
3. **ไม่มี raw SQL - ใช้ ORM เท่านั้น**
4. **ทุก model ต้องมี _description**
5. **ใช้ `<list>` ไม่ใช่ `<tree>` ใน Odoo 19**
6. **Test ทุก task ก่อนไป task ถัดไป**
7. **Commit บ่อยๆ ทุก task ที่เสร็จ**

---

**Last Updated:** 2025-10-16
**Created for:** school_asset_management module
**Based on:** IMPROVEMENT_PLAN.md analysis by Gemini + Claude Code
**Odoo Version:** 19.0
**Compliance:** ✅ Odoo 19 Best Practices
