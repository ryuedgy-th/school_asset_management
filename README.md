# School Asset Management Module

Version: 19.0.1.0.0
License: LGPL-3
Author: Your Company

## Overview

Complete asset management solution for international schools, specifically designed for IT departments to track and manage technology assets such as computers, tablets, projectors, and other equipment.

## Features

### Core Functionality
- **Asset Master Data Management**
  - Complete asset information tracking (name, code, barcode, serial number)
  - Category and location hierarchy
  - Purchase and warranty management
  - Status and condition tracking
  - QR code generation for easy scanning
  - Photo attachments

- **Teacher Assignments**
  - Checkout/check-in process for teachers
  - Term-based assignments (Semester 1, 2, Summer)
  - Digital signature capture
  - Condition documentation with photos
  - Damage assessment and tracking
  - Email notifications

- **Student Assignments**
  - Student device distribution
  - Parent/Guardian waiver management
  - Grade and section tracking
  - Bulk distribution support
  - Damage cost tracking and invoicing
  - Email notifications to parents

- **Asset Inspection**
  - Random and scheduled inspections
  - Customizable checklists
  - Photo documentation
  - Condition tracking over time
  - Action required tracking (monitor, repair, replace)

- **Movement History**
  - Automatic tracking of location changes
  - Custodian change history
  - Complete audit trail

## Installation

### Prerequisites
- Odoo 19 Community Edition
- Python 3.10 or higher
- Required Odoo modules: base, web, mail, hr

### Optional Python Libraries
For QR code generation functionality:
```bash
pip install qrcode[pil]
```

### Installation Steps

1. **Copy Module to Addons Directory**
   ```bash
   cp -r school_asset_management /path/to/odoo/addons/
   ```

2. **Update Apps List**
   - Log in to Odoo as Administrator
   - Go to Apps menu
   - Click "Update Apps List"
   - Search for "School Asset Management"

3. **Install Module**
   - Click "Install" button
   - Wait for installation to complete

4. **Configure Access Rights**
   - Go to Settings > Users & Companies > Groups
   - Assign users to appropriate groups:
     - IT Manager: Full access
     - IT Staff: Create and edit access
     - Teacher: Read-only access to own assignments

## Configuration

### Initial Setup

1. **Create Asset Categories**
   - Go to Assets > Configuration > Asset Categories
   - Create categories like:
     - Computers > Laptops
     - Computers > Desktops
     - Mobile Devices > Tablets
     - Peripherals > Projectors
     - Peripherals > Printers

2. **Create Asset Locations**
   - Go to Assets > Configuration > Asset Locations
   - Create location hierarchy:
     - Campus
       - Building A
         - Floor 1
           - Room 101
           - Room 102

3. **Import Assets** (Optional)
   - Prepare CSV file with columns:
     - name, asset_code, category, brand, model, serial_number, purchase_date, purchase_cost, location, status
   - Use Import feature in Assets list view

## Usage Guide

### Creating an Asset

1. Go to Assets > Assets > All Assets
2. Click "Create"
3. Fill in required information:
   - Asset Name (required)
   - Category (required)
   - Brand, Model, Serial Number
   - Purchase information
   - Warranty information
   - Location and Department
4. Upload photo (optional)
5. Click "Save"
6. Asset code will be auto-generated (format: ASSET-YYYY-NNNN)

### Teacher Checkout Process

1. Go to Assets > Assignments > Teacher Assignments
2. Click "Create"
3. Select teacher, academic year, and term
4. Set checkout and expected return dates
5. Add assets to the assignment:
   - Click "Add a line"
   - Select available assets
   - Document checkout condition
   - Add photos (optional)
   - Add notes
6. Capture teacher's digital signature
7. Click "Checkout" button
8. Email confirmation sent automatically

### Teacher Check-in Process

1. Open the teacher assignment
2. For each asset, document:
   - Check-in condition
   - Photos of returned asset
   - Any damage found
   - Estimated repair cost
3. System will auto-flag if condition worsened
4. Capture teacher's signature
5. Click "Check-in" button
6. Asset status automatically updated to "Available"
7. Email confirmation sent

### Student Distribution

1. Go to Assets > Assignments > Student Assignments
2. Click "Create"
3. Fill in student information:
   - Student name
   - Grade level and section
   - Academic year and term
   - Parent/Guardian information
4. Ensure parent waiver is signed
5. Add assets to distribute
6. Document initial condition
7. Click "Checkout"
8. Email sent to parent with asset details

### Conducting Inspections

1. Go to Assets > Inspections
2. Click "Create"
3. Select:
   - Asset to inspect
   - Inspection type (random, scheduled, maintenance, incident)
   - Inspection date
4. Document:
   - Current condition
   - Photos
   - Issues found
5. Fill in checklist items
6. Select action required (none, monitor, repair, replace)
7. If related to assignment, link the assignment
8. Click "Update Asset Condition" to sync with asset record

### Generating QR Codes

1. Open an asset
2. Click "Generate QR Code" button
3. QR code image will be downloaded
4. Print and attach to physical asset
5. Use mobile scanner to quickly locate asset in system

### Reports and Analytics

- **Asset Register**: Complete list of all assets with details
- **Assets by Category**: Distribution across categories
- **Assets by Location**: Current location of assets
- **Assignment History**: Complete assignment history
- **Warranty Expiry**: Assets with expiring warranties
- **Overdue Returns**: Assignments past expected return date

## User Roles and Permissions

### IT Manager
- Full access to all features
- Create, edit, delete assets
- Manage assignments
- Configure categories and locations
- View all reports
- User management

### IT Staff
- Create and edit assets
- Process checkout/check-in
- Conduct inspections
- View assignments
- Generate reports
- Cannot delete assets

### Teacher
- View own assignments
- View asset information
- Cannot modify assets
- Cannot create assignments

### Portal User (Parents)
- View student's assignments
- View asset information
- Cannot modify anything

## Data Security

- Record rules enforce data access based on user roles
- Teachers can only see their own assignments
- Parents can only see their children's assignments
- Complete audit trail with chatter integration
- All changes tracked in movement history

## Maintenance

### Regular Tasks
- Review warranty expiry alerts monthly
- Conduct random inspections quarterly
- Update asset conditions after each return
- Archive retired assets
- Generate asset register report annually

### Database Backups
- Regular backups recommended
- Keep asset photos and documents backed up separately

## Troubleshooting

### QR Code Generation Fails
**Issue**: Error when clicking "Generate QR Code"
**Solution**: Install qrcode library
```bash
pip install qrcode[pil]
```

### Email Notifications Not Sending
**Issue**: Emails not received by teachers/parents
**Solution**:
- Check Odoo email server configuration
- Verify teacher work_email and parent email addresses are set
- Check email template configuration in data/email_template.xml

### Assets Not Showing in Checkout
**Issue**: Assets don't appear in asset selection
**Solution**:
- Ensure asset status is "Available"
- Check if asset is already assigned
- Verify user has permission to view assets

## Support and Development

### Phase 1 (Current - Basic CRUD)
✅ Asset management with categories and locations
✅ Teacher and student assignments
✅ Inspection tracking
✅ Movement history
✅ Email notifications
✅ Basic security and access rights

### Phase 2 (Future Enhancements)
- Import/Export wizards
- Bulk operations (bulk status change, location change)
- Advanced checkout/checkin wizards
- Bulk student distribution wizard
- Enhanced dashboard with charts
- PDF report generation
- QR code label printing (bulk)
- Automated reminders and alerts
- Asset depreciation calculation
- Integration with accounting module
- Mobile app support

### Bug Reports
Please report issues with:
- Odoo version
- Module version
- Steps to reproduce
- Error messages (if any)
- Screenshots (if applicable)

## License

This module is licensed under LGPL-3.

## Credits

Developed for International School IT Departments
Compatible with Odoo 19 Community Edition

## Changelog

### Version 19.0.1.0.0 (2025-01-XX)
- Initial release
- Basic asset management functionality
- Teacher and student assignment tracking
- Inspection and movement history
- Email notification system
- Security groups and access rights
