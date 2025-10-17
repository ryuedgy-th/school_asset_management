# ✅ Odoo 19 Best Practices Checklist

> **คู่มือมาตรฐาน Odoo 19 - ใช้อ้างอิงทุกครั้งที่เขียนโค้ด**
>
> **📚 Official Docs:** https://www.odoo.com/documentation/19.0/

---

## 🎯 MANDATORY COMPLIANCE CHECKLIST

**ก่อนเริ่มเขียนโค้ด ต้องอ่านและปฏิบัติตามทุกข้อ**

---

## 1️⃣ Python Code Standards

### ✅ DO (ทำ)

```python
# Import Standards
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from typing import Optional, Tuple, List, Dict

_logger = logging.getLogger(__name__)

# Class Definition
class MyModel(models.Model):
    """Model description here.

    This model handles...
    """
    _name = 'my.model'
    _description = 'My Model Description'  # REQUIRED in Odoo 19
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    # Field Definitions with proper attributes
    name = fields.Char(
        string='Name',
        required=True,
        index=True,
        copy=False,
        help='Enter the name here'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to archive'
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done')
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True
    )

    # Computed Field with store
    total = fields.Float(
        string='Total Amount',
        compute='_compute_total',
        store=True,  # ถ้าต้องการ search/filter
        help='Sum of all line amounts'
    )

    # Proper compute method
    @api.depends('line_ids.amount')
    def _compute_total(self):
        """Calculate total amount from lines."""
        for record in self:
            record.total = sum(record.line_ids.mapped('amount'))

    # Proper constraint
    @api.constrains('amount')
    def _check_amount(self):
        """Validate amount is positive."""
        for record in self:
            if record.amount < 0:
                raise ValidationError(_('Amount must be positive'))

    # Business logic method
    def action_confirm(self):
        """Confirm the record."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft records can be confirmed'))

        self.write({'state': 'confirmed'})
        _logger.info('Record %s confirmed', self.name)
        return True

    # Override create with super()
    @api.model
    def create(self, vals):
        """Create record with custom logic."""
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('my.model')

        record = super().create(vals)
        record._send_notification()
        return record

    # Private method
    def _send_notification(self):
        """Send notification to users."""
        template = self.env.ref('module.email_template')
        template.send_mail(self.id, force_send=True)
```

### ❌ DON'T (ห้ามทำ)

```python
# ❌ No print statements
print("Debug info")  # Use _logger instead

# ❌ No raw SQL (use ORM)
self.env.cr.execute("SELECT * FROM table")

# ❌ No missing _description
class MyModel(models.Model):
    _name = 'my.model'
    # Missing _description - จะ warning ใน Odoo 19

# ❌ No loop for batch operations
for record in records:
    record.write({'field': value})  # Use records.write() instead

# ❌ No N+1 queries
for item in items:
    related = self.env['other.model'].search([('id', '=', item.id)])
```

---

## 2️⃣ XML View Standards (Odoo 19)

### ✅ Form View (Standard Structure)

```xml
<odoo>
    <record id="view_model_form" model="ir.ui.view">
        <field name="name">model.name.form</field>
        <field name="model">model.name</field>
        <field name="arch" type="xml">
            <form string="Model Form">
                <!-- Header with buttons and statusbar -->
                <header>
                    <button name="action_confirm"
                            type="object"
                            string="Confirm"
                            class="oe_highlight"
                            invisible="state != 'draft'"/>
                    <button name="action_cancel"
                            type="object"
                            string="Cancel"
                            invisible="state == 'cancel'"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,confirmed,done"/>
                </header>

                <sheet>
                    <!-- Title section -->
                    <div class="oe_title">
                        <label for="name" class="oe_edit_only"/>
                        <h1><field name="name" placeholder="Name..."/></h1>
                    </div>

                    <!-- Status ribbon (if needed) -->
                    <widget name="web_ribbon"
                            title="Archived"
                            bg_color="text-bg-danger"
                            invisible="active"/>

                    <!-- Main content in groups -->
                    <group>
                        <group name="left">
                            <field name="partner_id"/>
                            <field name="date"/>
                        </group>
                        <group name="right">
                            <field name="user_id"/>
                            <field name="amount"/>
                        </group>
                    </group>

                    <!-- Notebook for tabs -->
                    <notebook>
                        <page string="Lines" name="lines">
                            <field name="line_ids">
                                <list editable="bottom">
                                    <field name="product_id"/>
                                    <field name="quantity"/>
                                    <field name="price"/>
                                </list>
                            </field>
                        </page>
                        <page string="Other Info" name="other">
                            <group>
                                <field name="notes"/>
                            </group>
                        </page>
                    </notebook>
                </sheet>

                <!-- Chatter (mail thread) -->
                <chatter/>
            </form>
        </field>
    </record>
</odoo>
```

### ✅ List View (ใช้ `<list>` ไม่ใช่ `<tree>`)

```xml
<record id="view_model_list" model="ir.ui.view">
    <field name="name">model.name.list</field>
    <field name="model">model.name</field>
    <field name="arch" type="xml">
        <list string="Models"
              multi_edit="1"
              sample="1"
              decoration-info="state == 'draft'"
              decoration-success="state == 'done'">
            <field name="name"/>
            <field name="partner_id"/>
            <field name="date"/>
            <field name="amount" sum="Total"/>
            <field name="state" widget="badge"
                   decoration-info="state == 'draft'"
                   decoration-success="state == 'done'"/>
        </list>
    </field>
</record>
```

### ✅ Search View

```xml
<record id="view_model_search" model="ir.ui.view">
    <field name="name">model.name.search</field>
    <field name="model">model.name</field>
    <field name="arch" type="xml">
        <search>
            <field name="name"
                   filter_domain="['|', ('name', 'ilike', self), ('code', 'ilike', self)]"/>
            <field name="partner_id"/>
            <field name="state"/>

            <filter string="Draft"
                    name="draft"
                    domain="[('state', '=', 'draft')]"/>
            <filter string="Confirmed"
                    name="confirmed"
                    domain="[('state', '=', 'confirmed')]"/>

            <separator/>

            <filter string="Archived"
                    name="inactive"
                    domain="[('active', '=', False)]"/>

            <group expand="0" string="Group By">
                <filter string="Partner"
                        name="partner"
                        context="{'group_by': 'partner_id'}"/>
                <filter string="Status"
                        name="state"
                        context="{'group_by': 'state'}"/>
                <filter string="Date"
                        name="date"
                        context="{'group_by': 'date'}"/>
            </group>
        </search>
    </field>
</record>
```

### ✅ Action Definition

```xml
<record id="action_model" model="ir.actions.act_window">
    <field name="name">Models</field>
    <field name="res_model">model.name</field>
    <field name="view_mode">list,form,kanban</field>
    <field name="search_view_id" ref="view_model_search"/>
    <field name="context">{
        'search_default_draft': 1,
    }</field>
    <field name="help" type="html">
        <p class="o_view_nocontent_smiling_face">
            Create your first record
        </p>
    </field>
</record>
```

### ❌ DON'T (Deprecated in Odoo 19)

```xml
<!-- ❌ Don't use <tree> tag -->
<tree>...</tree>  <!-- Use <list> instead -->

<!-- ❌ Don't use attrs (deprecated) -->
<field name="field" attrs="{'invisible': [('state', '=', 'draft')]}"/>
<!-- Use invisible attribute instead -->
<field name="field" invisible="state == 'draft'"/>

<!-- ❌ Don't use old widget names -->
<field name="active" widget="boolean_button"/>
<!-- Use widget="boolean" instead -->
```

---

## 3️⃣ Controller Standards

### ✅ HTTP Controller

```python
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class MyController(http.Controller):

    @http.route('/my/route/<int:id>', type='http', auth='public',
                methods=['GET', 'POST'], csrf=False, website=True)
    def my_route(self, id, **kwargs):
        """Handle my route.

        Args:
            id: Record ID
            **kwargs: Additional parameters

        Returns:
            Rendered template or redirect
        """
        try:
            # Use request.env for database access
            record = request.env['my.model'].sudo().browse(id)

            if not record.exists():
                return request.not_found()

            # Validate input
            if not self._validate_input(kwargs):
                return request.render('module.error_page', {
                    'error': 'Invalid input'
                })

            # Render template
            return request.render('module.template', {
                'record': record,
                'data': kwargs
            })

        except Exception as e:
            _logger.exception('Error in my_route: %s', e)
            return request.render('module.error_page', {
                'error': str(e)
            })

    @http.route('/my/json', type='json', auth='user')
    def my_json_route(self, **kwargs):
        """JSON API endpoint.

        Returns:
            dict: JSON response
        """
        try:
            data = request.env['my.model'].search_read(
                domain=[],
                fields=['name', 'value']
            )
            return {
                'success': True,
                'data': data
            }
        except Exception as e:
            _logger.exception('Error in JSON route: %s', e)
            return {
                'success': False,
                'error': str(e)
            }

    def _validate_input(self, data):
        """Validate user input."""
        required_fields = ['name', 'email']
        return all(field in data for field in required_fields)
```

---

## 4️⃣ Security Rules

### ✅ Access Rights (ir.model.access.csv)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_model_user,model.name.user,model_model_name,base.group_user,1,1,1,0
access_model_manager,model.name.manager,model_model_name,group_manager,1,1,1,1
access_model_public,model.name.public,model_model_name,,1,0,0,0
```

### ✅ Record Rules (security.xml)

```xml
<odoo>
    <data noupdate="1">
        <!-- Users can only see their own records -->
        <record id="model_user_rule" model="ir.rule">
            <field name="name">User: Own Records Only</field>
            <field name="model_id" ref="model_model_name"/>
            <field name="domain_force">[('user_id', '=', user.id)]</field>
            <field name="groups" eval="[(4, ref('base.group_user'))]"/>
        </record>

        <!-- Managers can see all -->
        <record id="model_manager_rule" model="ir.rule">
            <field name="name">Manager: All Records</field>
            <field name="model_id" ref="model_model_name"/>
            <field name="domain_force">[(1, '=', 1)]</field>
            <field name="groups" eval="[(4, ref('group_manager'))]"/>
        </record>
    </data>
</odoo>
```

---

## 5️⃣ JavaScript (Odoo 19)

### ✅ OWL Component (Modern)

```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MyComponent extends Component {
    static template = "module_name.MyTemplate";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            data: [],
            loading: false
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.searchRead(
                "my.model",
                [],
                ["name", "value"]
            );
        } catch (error) {
            console.error("Error loading data:", error);
        } finally {
            this.state.loading = false;
        }
    }
}

registry.category("actions").add("my_component", MyComponent);
```

### ✅ Legacy Frontend (if needed)

```javascript
odoo.define('module_name.MyWidget', function(require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var _t = core._t;

    var MyWidget = Widget.extend({
        template: 'module_name.MyTemplate',

        init: function(parent, options) {
            this._super.apply(this, arguments);
            this.options = options;
        },

        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                self._loadData();
            });
        },

        _loadData: function() {
            var self = this;
            this._rpc({
                model: 'my.model',
                method: 'search_read',
                args: [[], ['name', 'value']]
            }).then(function(data) {
                self._renderData(data);
            });
        }
    });

    return MyWidget;
});
```

---

## 6️⃣ Email Templates

### ✅ Mail Template

```xml
<odoo>
    <record id="email_template_model" model="mail.template">
        <field name="name">Model: Notification</field>
        <field name="model_id" ref="model_model_name"/>
        <field name="subject">Notification: ${object.name}</field>
        <field name="email_from">${(object.user_id.email or user.email)|safe}</field>
        <field name="email_to">${object.partner_id.email}</field>
        <field name="body_html" type="html">
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td style="background-color: #574193; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Notification</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 20px; background-color: #f5f5f5;">
                <p>Hello ${object.partner_id.name},</p>
                <p>Your record <strong>${object.name}</strong> has been updated.</p>

                <p>Status: <strong>${object.state}</strong></p>

                <p style="text-align: center; margin: 30px 0;">
                    <a href="/my/records/${object.id}"
                       style="background-color: #6ab42d; color: white;
                              padding: 10px 20px; text-decoration: none;
                              border-radius: 5px;">View Record</a>
                </p>

                <p>Best regards,<br/>
                ${object.company_id.name}</p>
            </td>
        </tr>
        <tr>
            <td style="padding: 10px; text-align: center; font-size: 12px; color: #666;">
                <p>${object.company_id.name}<br/>
                ${object.company_id.email} | ${object.company_id.phone}</p>
            </td>
        </tr>
    </table>
</div>
        </field>
    </record>
</odoo>
```

---

## 7️⃣ Testing

### ✅ Unit Test

```python
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError

@tagged('post_install', '-at_install')
class TestMyModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Model = self.env['my.model']
        self.partner = self.env.ref('base.res_partner_1')

    def test_create_record(self):
        """Test record creation."""
        record = self.Model.create({
            'name': 'Test Record',
            'partner_id': self.partner.id
        })
        self.assertTrue(record)
        self.assertEqual(record.name, 'Test Record')
        self.assertEqual(record.state, 'draft')

    def test_compute_total(self):
        """Test total computation."""
        record = self.Model.create({
            'name': 'Test',
            'line_ids': [(0, 0, {'amount': 100}), (0, 0, {'amount': 200})]
        })
        self.assertEqual(record.total, 300)

    def test_validation_error(self):
        """Test constraint validation."""
        with self.assertRaises(ValidationError):
            self.Model.create({
                'name': 'Test',
                'amount': -100  # Should raise error
            })

    def test_action_confirm(self):
        """Test confirm action."""
        record = self.Model.create({'name': 'Test'})
        record.action_confirm()
        self.assertEqual(record.state, 'confirmed')
```

---

## 8️⃣ Performance Best Practices

### ✅ Efficient Code

```python
# ✅ DO: Batch operations
records.write({'field': value})

# ✅ DO: Use mapped for extraction
values = records.mapped('field_name')
emails = records.mapped('partner_id.email')

# ✅ DO: Use filtered for filtering
draft_records = records.filtered(lambda r: r.state == 'draft')

# ✅ DO: Use search_read for list views
data = model.search_read([domain], ['field1', 'field2'], limit=100)

# ✅ DO: Use exists() to check existence
if record.exists():
    record.write({...})

# ✅ DO: Prefetch related data
records.mapped('partner_id.name')  # Prefetch all partners at once
```

### ❌ DON'T: Inefficient Code

```python
# ❌ DON'T: Loop for batch operations
for record in records:
    record.write({'field': value})  # N queries

# ❌ DON'T: N+1 queries
for item in items:
    partner = self.env['res.partner'].search([('id', '=', item.partner_id)])

# ❌ DON'T: Load all fields when you need few
records = model.search([])  # Loads ALL fields
```

---

## 9️⃣ Module Structure (Odoo 19)

```
my_module/
├── __init__.py                     # Import submodules
├── __manifest__.py                 # Module metadata
│
├── models/
│   ├── __init__.py
│   ├── model_name.py              # Main model
│   └── model_line.py              # Related model
│
├── views/
│   ├── model_views.xml            # Form, list, search views
│   ├── model_menus.xml            # Menus and actions
│   └── templates.xml              # QWeb templates
│
├── security/
│   ├── security.xml               # Groups and record rules
│   └── ir.model.access.csv        # Access rights
│
├── data/
│   ├── data.xml                   # Master data
│   ├── sequence.xml               # Sequences
│   └── email_template.xml         # Email templates
│
├── wizards/
│   ├── __init__.py
│   ├── wizard_name.py             # Wizard model
│   └── wizard_views.xml           # Wizard views
│
├── reports/
│   ├── __init__.py
│   ├── report.py                  # Report logic
│   └── report_template.xml        # QWeb report template
│
├── controllers/
│   ├── __init__.py
│   └── main.py                    # HTTP controllers
│
├── static/
│   ├── description/
│   │   ├── icon.png              # Module icon (128x128)
│   │   └── index.html            # Module description
│   └── src/
│       ├── js/
│       │   └── component.js      # JavaScript
│       ├── css/
│       │   └── style.css         # Stylesheets
│       └── xml/
│           └── templates.xml     # JS templates
│
├── tests/
│   ├── __init__.py
│   ├── test_model.py             # Unit tests
│   └── test_controller.py        # Controller tests
│
└── doc/
    └── README.md                  # Documentation
```

---

## 🔟 __manifest__.py Template

```python
{
    'name': 'My Module Name',
    'version': '19.0.1.0.0',
    'category': 'Sales',  # or: Inventory, Accounting, etc.
    'summary': 'Short one-line description',
    'description': """
        Longer description of the module.

        Key Features:
        * Feature 1
        * Feature 2
        * Feature 3
    """,
    'author': 'Your Company Name',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',

    # Dependencies
    'depends': [
        'base',
        'mail',
        'web',
    ],

    # External Python dependencies
    'external_dependencies': {
        'python': [
            'Pillow',  # Image processing
            'redis',   # Caching/rate limiting
        ],
    },

    # Data files (order matters!)
    'data': [
        # Security first
        'security/security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence.xml',
        'data/data.xml',
        'data/email_template.xml',

        # Views
        'views/model_views.xml',
        'views/model_menus.xml',

        # Wizards
        'wizards/wizard_views.xml',

        # Reports
        'reports/report_template.xml',
    ],

    # Assets (JS, CSS)
    'assets': {
        'web.assets_backend': [
            'my_module/static/src/js/backend.js',
            'my_module/static/src/css/backend.css',
        ],
        'web.assets_frontend': [
            'my_module/static/src/js/frontend.js',
            'my_module/static/src/css/frontend.css',
        ],
    },

    # Demo data (optional)
    'demo': [
        'demo/demo_data.xml',
    ],

    # Module flags
    'installable': True,
    'application': False,  # True if standalone app
    'auto_install': False,

    # Images for Odoo Apps Store
    'images': ['static/description/banner.png'],
}
```

---

## 🎯 Pre-Commit Checklist

**ก่อน commit ต้องตรวจสอบทุกครั้ง:**

- [ ] ไม่มี `print()` statements (ใช้ `_logger` แทน)
- [ ] ไม่มี raw SQL queries (ใช้ ORM)
- [ ] ทุก model มี `_description`
- [ ] ทุก method มี docstring
- [ ] ใช้ `<list>` แทน `<tree>` ใน views
- [ ] ใช้ `invisible` attribute แทน `attrs`
- [ ] ทุก user-facing string ใช้ `_()`
- [ ] Exception handling ครบถ้วน
- [ ] Security audit logging สำหรับ sensitive operations
- [ ] ไม่มี unused imports
- [ ] Follow PEP 8 coding style
- [ ] Tests passed (ถ้ามี)

---

## 🧪 Testing Commands

```bash
# Run tests for specific module
odoo-bin -d database_name -u module_name --test-enable --stop-after-init

# Run specific test class
odoo-bin -d database_name -u module_name --test-tags=TestMyModel

# Check Python code quality
flake8 module_name/
pylint module_name/

# Validate manifest
python3 -c "import ast; ast.parse(open('__manifest__.py').read())"
```

---

## 📚 Quick Reference Links

- **Odoo 19 Documentation**: https://www.odoo.com/documentation/19.0/
- **Developer Tutorials**: https://www.odoo.com/documentation/19.0/developer/tutorials.html
- **Coding Guidelines**: https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html
- **ORM API**: https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- **Views**: https://www.odoo.com/documentation/19.0/developer/reference/backend/views.html
- **QWeb**: https://www.odoo.com/documentation/19.0/developer/reference/frontend/qweb.html
- **JavaScript**: https://www.odoo.com/documentation/19.0/developer/reference/frontend/javascript.html

---

**💡 Pro Tips:**

1. **Always read Odoo docs first** before implementing
2. **Use Odoo Studio** to learn correct XML structure
3. **Check Odoo core modules** for examples (e.g., `sale`, `stock`)
4. **Test in multi-worker environment** before production
5. **Use `--dev=all`** flag during development for auto-reload

---

**Last Updated:** 2025-10-16
**Odoo Version:** 19.0
**Status:** ✅ Production Ready
