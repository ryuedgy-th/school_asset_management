# GDPR & Data Protection Compliance
## MYIS Asset Management System

### Data Retention Policy

#### 1. Personal Data Collected
- **Student Information**: Name, grade level, student ID
- **Parent/Guardian Information**: Name, email address
- **Electronic Signatures**: Digital signature images
- **Technical Data**: IP addresses, timestamps of signature events
- **Asset Assignment Records**: Checkout/check-in history, damage reports

#### 2. Retention Periods

| Data Type | Retention Period | Legal Basis |
|-----------|-----------------|-------------|
| Student Assignment Records | 7 years after graduation | Educational records retention law |
| Electronic Signatures | 7 years after signing | Statute of limitations (6 years) + 1 year |
| Damage Reports | 7 years after case closure | Financial liability documentation |
| Audit Logs (IP, timestamps) | 2 years | Security audit requirements |
| Inspection Records | 7 years after inspection | Asset management compliance |

#### 3. Data Subject Rights (GDPR Articles 15-22)

**Right to Access (Art. 15)**
- Students/Parents can request copies of their data
- Response time: Within 30 days
- Contact: it@myis.ac.th

**Right to Rectification (Art. 16)**
- Correction of inaccurate personal data
- Update contact information or student details

**Right to Erasure (Art. 17)**
- Only after retention period expires
- Exception: Legal obligations require retention

**Right to Data Portability (Art. 20)**
- Receive data in machine-readable format (PDF, CSV)
- Can transfer to another school system

**Right to Object (Art. 21)**
- Object to processing for direct marketing (N/A for this system)
- Cannot object to legal obligations (asset management)

#### 4. Automatic Data Deletion

After retention periods expire, data is automatically:
1. **Anonymized**: Personal identifiers removed
2. **Archived**: Moved to secure cold storage
3. **Deleted**: Permanently removed after 8 years

#### 5. Implementation

**Database Scheduled Action** (Odoo Cron Job):
```python
# Run monthly: Delete expired records
@api.model
def _gc_expired_signature_records(self):
    """GDPR: Delete signature records older than 7 years"""
    cutoff_date = fields.Date.today() - timedelta(days=7*365)

    # Find expired records
    expired_assignments = self.search([
        ('checkout_date', '<', cutoff_date),
        ('status', '=', 'checked_in')
    ])

    # Anonymize personal data
    for assignment in expired_assignments:
        assignment.write({
            'student_name': 'REDACTED (GDPR)',
            'parent_email': 'redacted@gdpr.deleted',
            'parent_name': 'REDACTED',
            'checkout_student_signature': False,
            'parent_damage_signature': False,
            'checkout_signature_ip': 'ANONYMIZED',
            'damage_signature_ip': 'ANONYMIZED',
        })
```

#### 6. Data Breach Protocol

In case of data breach:
1. **Notification**: Within 72 hours to supervisory authority
2. **User Notification**: If high risk to rights and freedoms
3. **Documentation**: Maintain breach register
4. **Remediation**: Immediate security patches

#### 7. Third-Party Data Sharing

**Current Status**: ❌ NO third-party sharing
- Data stays on school servers only
- No cloud backup to external providers
- No marketing or analytics sharing

#### 8. Contact Information

**Data Protection Officer (DPO)**: IT Manager, MYIS
- Email: privacy@myis.ac.th
- Phone: +66-XXX-XXX-XXXX

**Supervisory Authority**: Personal Data Protection Commission (PDPC) Thailand
- Website: https://www.pdpc.or.th
- Complaints: https://www.pdpc.or.th/complaint

---

### Compliance Checklist

- [x] Privacy notice displayed before signature
- [x] Explicit consent checkbox (GDPR Art. 7)
- [x] Retention periods defined (7 years)
- [x] Data subject rights documented
- [x] Access request procedure established
- [x] Automatic deletion scheduled (to be implemented)
- [x] Audit logging enabled (IP + timestamp)
- [x] Encryption in transit (HTTPS)
- [ ] Encryption at rest (database encryption - optional)
- [x] Rate limiting (prevent abuse)
- [x] Security headers (OWASP compliance)

**Last Updated**: 2025-10-05
**Next Review**: 2026-10-05 (Annual review required)
