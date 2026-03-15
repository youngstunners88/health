"""Compliance Auditor for Healthcare Platform - HIPAA, SOC 2, FDA SAMD."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


HIPAA_CHECKS = [
    {
        "id": "HIPAA-ADM-001",
        "category": "Administrative Safeguards",
        "title": "Security Management Process",
        "description": "Implement policies and procedures to prevent, detect, contain, and correct security violations.",
        "remediation": "Establish a formal security management process with documented policies, risk assessment procedures, and sanction policies.",
    },
    {
        "id": "HIPAA-ADM-002",
        "category": "Administrative Safeguards",
        "title": "Risk Analysis",
        "description": "Conduct an accurate and thorough assessment of the potential risks and vulnerabilities to ePHI.",
        "remediation": "Perform comprehensive risk analysis annually or upon significant environmental changes. Document findings and mitigation plans.",
    },
    {
        "id": "HIPAA-ADM-003",
        "category": "Administrative Safeguards",
        "title": "Risk Management",
        "description": "Implement security measures sufficient to reduce risks and vulnerabilities to a reasonable level.",
        "remediation": "Develop and implement a risk management plan addressing identified vulnerabilities with timelines and responsible parties.",
    },
    {
        "id": "HIPAA-ADM-004",
        "category": "Administrative Safeguards",
        "title": "Sanction Policy",
        "description": "Apply appropriate sanctions against workforce members who fail to comply with security policies.",
        "remediation": "Create and distribute a documented sanction policy with graduated consequences for policy violations.",
    },
    {
        "id": "HIPAA-ADM-005",
        "category": "Administrative Safeguards",
        "title": "Information System Activity Review",
        "description": "Regularly review records of information system activity, such as audit logs, access reports, and security incident tracking.",
        "remediation": "Implement automated log review and establish a schedule for manual audit log reviews by security personnel.",
    },
    {
        "id": "HIPAA-ADM-006",
        "category": "Administrative Safeguards",
        "title": "Security Officer",
        "description": "Identify a security official responsible for developing and implementing security policies and procedures.",
        "remediation": "Designate a qualified Security Officer with documented responsibilities and authority over the security program.",
    },
    {
        "id": "HIPAA-ADM-007",
        "category": "Administrative Safeguards",
        "title": "Workforce Security",
        "description": "Ensure that all workforce members have appropriate access to ePHI and prevent unauthorized access.",
        "remediation": "Implement role-based access controls, background checks, and regular access reviews for all workforce members.",
    },
    {
        "id": "HIPAA-ADM-008",
        "category": "Administrative Safeguards",
        "title": "Authorization and Supervision",
        "description": "Implement procedures for authorizing and supervising workforce members who access ePHI.",
        "remediation": "Document authorization procedures and implement supervisory controls for workforce access to ePHI.",
    },
    {
        "id": "HIPAA-ADM-009",
        "category": "Administrative Safeguards",
        "title": "Workforce Clearance",
        "description": "Implement procedures to determine that access to ePHI is appropriate based on job function.",
        "remediation": "Establish clearance procedures including background verification and role-based access assignment.",
    },
    {
        "id": "HIPAA-ADM-010",
        "category": "Administrative Safeguards",
        "title": "Termination Procedures",
        "description": "Implement procedures for terminating access to ePHI when employment ends.",
        "remediation": "Automate access revocation upon termination and maintain a checklist for offboarding procedures.",
    },
    {
        "id": "HIPAA-ADM-011",
        "category": "Administrative Safeguards",
        "title": "Security Awareness Training",
        "description": "Implement a security awareness and training program for all workforce members.",
        "remediation": "Deploy annual security awareness training with phishing simulations and track completion rates.",
    },
    {
        "id": "HIPAA-ADM-012",
        "category": "Administrative Safeguards",
        "title": "Protection from Malicious Software",
        "description": "Implement procedures for guarding against, detecting, and reporting malicious software.",
        "remediation": "Deploy endpoint protection, email filtering, and web security gateways with automated threat detection.",
    },
    {
        "id": "HIPAA-ADM-013",
        "category": "Administrative Safeguards",
        "title": "Log-in Monitoring",
        "description": "Implement procedures for monitoring log-in attempts and reporting discrepancies.",
        "remediation": "Configure account lockout policies, failed login alerts, and automated anomaly detection.",
    },
    {
        "id": "HIPAA-ADM-014",
        "category": "Administrative Safeguards",
        "title": "Password Management",
        "description": "Implement procedures for creating, changing, and safeguarding passwords.",
        "remediation": "Enforce password complexity, rotation policies, and multi-factor authentication across all systems.",
    },
    {
        "id": "HIPAA-ADM-015",
        "category": "Administrative Safeguards",
        "title": "Security Incident Procedures",
        "description": "Identify, respond to, and mitigate security incidents. Document and report incidents.",
        "remediation": "Establish an incident response plan with defined roles, communication procedures, and post-incident review.",
    },
    {
        "id": "HIPAA-ADM-016",
        "category": "Administrative Safeguards",
        "title": "Contingency Plan",
        "description": "Establish policies and procedures for responding to emergencies that damage systems containing ePHI.",
        "remediation": "Develop and test a comprehensive contingency plan including data backup, disaster recovery, and emergency mode operations.",
    },
    {
        "id": "HIPAA-ADM-017",
        "category": "Administrative Safeguards",
        "title": "Data Backup Plan",
        "description": "Establish and implement procedures to create and maintain retrievable exact copies of ePHI.",
        "remediation": "Implement automated encrypted backups with regular restoration testing and off-site storage.",
    },
    {
        "id": "HIPAA-ADM-018",
        "category": "Administrative Safeguards",
        "title": "Disaster Recovery Plan",
        "description": "Establish procedures to restore any loss of data and recover operations after a disaster.",
        "remediation": "Document and test disaster recovery procedures with defined RTO and RPO objectives.",
    },
    {
        "id": "HIPAA-ADM-019",
        "category": "Administrative Safeguards",
        "title": "Emergency Mode Operation Plan",
        "description": "Establish procedures to enable continuation of critical business processes during emergencies.",
        "remediation": "Identify critical systems and implement failover capabilities with documented emergency procedures.",
    },
    {
        "id": "HIPAA-ADM-020",
        "category": "Administrative Safeguards",
        "title": "Testing and Revision Procedures",
        "description": "Implement procedures for periodic testing and revision of contingency plans.",
        "remediation": "Schedule quarterly tabletop exercises and annual full-scale disaster recovery tests.",
    },
    {
        "id": "HIPAA-ADM-021",
        "category": "Administrative Safeguards",
        "title": "Business Associate Agreements",
        "description": "Execute BAAs with all vendors that have access to ePHI.",
        "remediation": "Maintain a BAA registry and ensure all business associates have signed agreements before data sharing.",
    },
    {
        "id": "HIPAA-ADM-022",
        "category": "Administrative Safeguards",
        "title": "Evaluation",
        "description": "Perform periodic technical and non-technical evaluations of security policies.",
        "remediation": "Conduct annual third-party security assessments and internal compliance reviews.",
    },
    {
        "id": "HIPAA-PHY-001",
        "category": "Physical Safeguards",
        "title": "Facility Access Controls",
        "description": "Implement policies and procedures to limit physical access to facilities housing ePHI systems.",
        "remediation": "Deploy badge access systems, visitor logs, and escorted access for non-employees.",
    },
    {
        "id": "HIPAA-PHY-002",
        "category": "Physical Safeguards",
        "title": "Contingency Operations",
        "description": "Implement procedures for facility access in support of contingency operations.",
        "remediation": "Document emergency access procedures and maintain alternate facility access capabilities.",
    },
    {
        "id": "HIPAA-PHY-003",
        "category": "Physical Safeguards",
        "title": "Facility Security Plan",
        "description": "Implement policies and procedures to safeguard the facility and equipment from unauthorized access.",
        "remediation": "Develop a comprehensive facility security plan with physical security controls and monitoring.",
    },
    {
        "id": "HIPAA-PHY-004",
        "category": "Physical Safeguards",
        "title": "Access Control and Validation",
        "description": "Implement procedures to control and validate a person's access to facilities.",
        "remediation": "Implement multi-factor physical access controls with regular access right reviews.",
    },
    {
        "id": "HIPAA-PHY-005",
        "category": "Physical Safeguards",
        "title": "Maintenance Records",
        "description": "Implement policies and procedures to document repairs and modifications to physical security components.",
        "remediation": "Maintain a maintenance log for all physical security systems with change tracking.",
    },
    {
        "id": "HIPAA-PHY-006",
        "category": "Physical Safeguards",
        "title": "Workstation Use",
        "description": "Implement policies and procedures specifying proper functions of workstations accessing ePHI.",
        "remediation": "Document acceptable use policies and deploy workstation security configurations.",
    },
    {
        "id": "HIPAA-PHY-007",
        "category": "Physical Safeguards",
        "title": "Workstation Security",
        "description": "Implement physical safeguards for all workstations that access ePHI.",
        "remediation": "Deploy privacy screens, automatic screen locks, and secure workstation placement.",
    },
    {
        "id": "HIPAA-PHY-008",
        "category": "Physical Safeguards",
        "title": "Device and Media Controls",
        "description": "Implement policies and procedures governing receipt and removal of hardware and electronic media.",
        "remediation": "Establish device inventory tracking, media sanitization procedures, and secure disposal processes.",
    },
    {
        "id": "HIPAA-PHY-009",
        "category": "Physical Safeguards",
        "title": "Disposal of PHI",
        "description": "Implement policies and procedures for the final disposition of ePHI and hardware.",
        "remediation": "Use NIST 800-88 compliant media sanitization with certificates of destruction.",
    },
    {
        "id": "HIPAA-PHY-010",
        "category": "Physical Safeguards",
        "title": "Media Re-use",
        "description": "Implement procedures for removal of ePHI from electronic media before re-use.",
        "remediation": "Implement automated media sanitization workflows with verification before re-assignment.",
    },
    {
        "id": "HIPAA-TEC-001",
        "category": "Technical Safeguards",
        "title": "Access Control - Unique User Identification",
        "description": "Assign a unique name and/or number for identifying and tracking user identity.",
        "remediation": "Implement unique user IDs across all systems with no shared accounts.",
    },
    {
        "id": "HIPAA-TEC-002",
        "category": "Technical Safeguards",
        "title": "Emergency Access Procedure",
        "description": "Establish procedures for obtaining necessary ePHI during an emergency.",
        "remediation": "Implement break-glass access procedures with enhanced logging and post-access review.",
    },
    {
        "id": "HIPAA-TEC-003",
        "category": "Technical Safeguards",
        "title": "Automatic Logoff",
        "description": "Implement electronic procedures that terminate an electronic session after a period of inactivity.",
        "remediation": "Configure automatic session timeout at 15 minutes of inactivity across all systems.",
    },
    {
        "id": "HIPAA-TEC-004",
        "category": "Technical Safeguards",
        "title": "Encryption and Decryption",
        "description": "Implement mechanism to encrypt and decrypt ePHI at rest and in transit.",
        "remediation": "Deploy AES-256 encryption for data at rest and TLS 1.2+ for data in transit.",
    },
    {
        "id": "HIPAA-TEC-005",
        "category": "Technical Safeguards",
        "title": "Audit Controls",
        "description": "Implement hardware, software, and procedural mechanisms to record and examine activity in systems containing ePHI.",
        "remediation": "Deploy centralized logging with immutable audit trails and real-time alerting for suspicious activities.",
    },
    {
        "id": "HIPAA-TEC-006",
        "category": "Technical Safeguards",
        "title": "Integrity Controls",
        "description": "Implement policies and procedures to protect ePHI from improper alteration or destruction.",
        "remediation": "Implement checksums, digital signatures, and version control for all ePHI records.",
    },
    {
        "id": "HIPAA-TEC-007",
        "category": "Technical Safeguards",
        "title": "Person or Entity Authentication",
        "description": "Implement procedures to verify that a person or entity seeking access to ePHI is who they claim to be.",
        "remediation": "Deploy multi-factor authentication with strong identity verification for all ePHI access.",
    },
    {
        "id": "HIPAA-TEC-008",
        "category": "Technical Safeguards",
        "title": "Transmission Security",
        "description": "Implement technical security measures to guard against unauthorized access to ePHI transmitted over networks.",
        "remediation": "Enforce TLS 1.2+ for all network communications and implement network segmentation.",
    },
    {
        "id": "HIPAA-TEC-009",
        "category": "Technical Safeguards",
        "title": "Network Security",
        "description": "Implement firewalls, intrusion detection, and network monitoring to protect ePHI.",
        "remediation": "Deploy next-generation firewalls, IDS/IPS, and continuous network monitoring with alerting.",
    },
    {
        "id": "HIPAA-TEC-010",
        "category": "Technical Safeguards",
        "title": "Vulnerability Management",
        "description": "Implement regular vulnerability scanning and patch management processes.",
        "remediation": "Schedule monthly vulnerability scans and critical patch deployment within 72 hours.",
    },
    {
        "id": "HIPAA-BRN-001",
        "category": "Breach Notification",
        "title": "Breach Notification to Individuals",
        "description": "Notify affected individuals without unreasonable delay, no later than 60 days after breach discovery.",
        "remediation": "Establish breach notification procedures with template letters and contact management.",
    },
    {
        "id": "HIPAA-BRN-002",
        "category": "Breach Notification",
        "title": "Breach Notification to HHS",
        "description": "Notify the Secretary of HHS following discovery of a breach of unsecured PHI.",
        "remediation": "Implement breach reporting workflows with HHS notification within required timelines.",
    },
    {
        "id": "HIPAA-BRN-003",
        "category": "Breach Notification",
        "title": "Breach Notification to Media",
        "description": "Notify prominent media outlets serving the state/jurisdiction for breaches affecting 500+ residents.",
        "remediation": "Develop media notification templates and maintain media contact lists for each jurisdiction.",
    },
    {
        "id": "HIPAA-BRN-004",
        "category": "Breach Notification",
        "title": "Breach Risk Assessment",
        "description": "Conduct a risk assessment to determine if a breach has occurred using the four-factor test.",
        "remediation": "Document the four-factor risk assessment process and maintain assessment records.",
    },
    {
        "id": "HIPAA-BRN-005",
        "category": "Breach Notification",
        "title": "Breach Documentation",
        "description": "Document all breaches regardless of size and maintain records for at least 6 years.",
        "remediation": "Implement breach tracking system with automated retention policies.",
    },
    {
        "id": "HIPAA-BRN-006",
        "category": "Breach Notification",
        "title": "Small Breach Log",
        "description": "Maintain a log of breaches affecting fewer than 500 individuals and report annually to HHS.",
        "remediation": "Track all breaches in a centralized log and submit annual report by March 1.",
    },
    {
        "id": "HIPAA-PRV-001",
        "category": "Privacy Rule",
        "title": "Notice of Privacy Practices",
        "description": "Provide patients with a notice of privacy practices describing how their PHI may be used and disclosed.",
        "remediation": "Create and distribute NPP to all patients, obtain acknowledgment, and post prominently.",
    },
    {
        "id": "HIPAA-PRV-002",
        "category": "Privacy Rule",
        "title": "Minimum Necessary Standard",
        "description": "Make reasonable efforts to limit PHI use, disclosure, and request to the minimum necessary.",
        "remediation": "Implement role-based access controls and data minimization policies across all systems.",
    },
    {
        "id": "HIPAA-PRV-003",
        "category": "Privacy Rule",
        "title": "Patient Right to Access",
        "description": "Provide patients access to their PHI within 30 days of request.",
        "remediation": "Establish patient portal access and formal request processing workflows with SLA tracking.",
    },
    {
        "id": "HIPAA-PRV-004",
        "category": "Privacy Rule",
        "title": "Patient Right to Amendment",
        "description": "Allow patients to request amendments to their PHI and respond within 60 days.",
        "remediation": "Implement amendment request workflows with tracking and response templates.",
    },
    {
        "id": "HIPAA-PRV-005",
        "category": "Privacy Rule",
        "title": "Accounting of Disclosures",
        "description": "Provide patients with an accounting of disclosures of their PHI upon request.",
        "remediation": "Maintain disclosure logs and implement automated accounting report generation.",
    },
    {
        "id": "HIPAA-PRV-006",
        "category": "Privacy Rule",
        "title": "Privacy Officer",
        "description": "Designate a privacy official responsible for developing and implementing privacy policies.",
        "remediation": "Appoint a qualified Privacy Officer with documented authority and responsibilities.",
    },
    {
        "id": "HIPAA-PRV-007",
        "category": "Privacy Rule",
        "title": "Patient Complaints",
        "description": "Implement a process for individuals to file complaints about privacy practices.",
        "remediation": "Establish complaint procedures with documentation, investigation, and resolution tracking.",
    },
    {
        "id": "HIPAA-PRV-008",
        "category": "Privacy Rule",
        "title": "Retaliation Prohibition",
        "description": "Do not intimidate, threaten, coerce, discriminate against, or take retaliatory action against individuals.",
        "remediation": "Include anti-retaliation provisions in workforce policies and train staff on whistleblower protections.",
    },
    {
        "id": "HIPAA-PRV-009",
        "category": "Privacy Rule",
        "title": "De-identification Standards",
        "description": "Implement standards for de-identification of PHI using expert determination or safe harbor methods.",
        "remediation": "Document de-identification procedures and validate against the 18 HIPAA identifiers.",
    },
    {
        "id": "HIPAA-PRV-010",
        "category": "Privacy Rule",
        "title": "Limited Data Sets",
        "description": "Implement procedures for creating and sharing limited data sets with data use agreements.",
        "remediation": "Establish limited data set creation workflows and execute data use agreements with recipients.",
    },
    {
        "id": "HIPAA-PRV-011",
        "category": "Privacy Rule",
        "title": "Authorization Requirements",
        "description": "Obtain valid patient authorization before using or disclosing PHI for purposes not otherwise permitted.",
        "remediation": "Implement authorization management system with valid authorization templates and expiration tracking.",
    },
    {
        "id": "HIPAA-PRV-012",
        "category": "Privacy Rule",
        "title": "Research Protections",
        "description": "Implement additional safeguards for PHI used in research, including IRB review and data use agreements.",
        "remediation": "Establish research data governance with IRB oversight and specialized access controls.",
    },
]


SOC2_CHECKLIST = [
    {"id": "SOC2-CC1.1", "category": "Control Environment", "title": "COSO Principle 1: Commitment to Integrity and Ethical Values", "description": "The entity demonstrates a commitment to integrity and ethical values."},
    {"id": "SOC2-CC1.2", "category": "Control Environment", "title": "COSO Principle 2: Board Independence", "description": "The board of directors demonstrates independence from management."},
    {"id": "SOC2-CC1.3", "category": "Control Environment", "title": "COSO Principle 3: Organizational Structure", "description": "Management establishes reporting lines and appropriate authorities."},
    {"id": "SOC2-CC1.4", "category": "Control Environment", "title": "COSO Principle 4: Commitment to Competence", "description": "The entity demonstrates commitment to attracting and retaining competent individuals."},
    {"id": "SOC2-CC1.5", "category": "Control Environment", "title": "COSO Principle 5: Accountability", "description": "The entity holds individuals accountable for internal control responsibilities."},
    {"id": "SOC2-CC2.1", "category": "Communication and Information", "title": "Internal Communication", "description": "The entity internally communicates information necessary to support functioning of internal control."},
    {"id": "SOC2-CC2.2", "category": "Communication and Information", "title": "External Communication", "description": "The entity communicates with external parties regarding matters affecting internal control."},
    {"id": "SOC2-CC3.1", "category": "Risk Assessment", "title": "Objective Specification", "description": "The entity specifies objectives with sufficient clarity to enable identification and assessment of risks."},
    {"id": "SOC2-CC3.2", "category": "Risk Assessment", "title": "Risk Identification", "description": "The entity identifies risks to achievement of objectives."},
    {"id": "SOC2-CC3.3", "category": "Risk Assessment", "title": "Fraud Risk Assessment", "description": "The entity considers potential for fraud in assessing risks."},
    {"id": "SOC2-CC3.4", "category": "Risk Assessment", "title": "Change Management Risk", "description": "The entity identifies and assesses changes that could impact the system of internal control."},
    {"id": "SOC2-CC4.1", "category": "Monitoring Activities", "title": "Ongoing Monitoring", "description": "The entity selects and performs ongoing and/or separate evaluations of internal control."},
    {"id": "SOC2-CC4.2", "category": "Monitoring Activities", "title": "Deficiency Evaluation", "description": "The entity evaluates and communicates internal control deficiencies in a timely manner."},
    {"id": "SOC2-CC5.1", "category": "Control Activities", "title": "Risk Mitigation", "description": "The entity selects and develops control activities that mitigate risks."},
    {"id": "SOC2-CC5.2", "category": "Control Activities", "title": "Technology Controls", "description": "The entity selects and develops technology controls to support achievement of objectives."},
    {"id": "SOC2-CC5.3", "category": "Control Activities", "title": "Policies and Procedures", "description": "The entity deploys control activities through policies and procedures."},
    {"id": "SOC2-CC6.1", "category": "Logical and Physical Access", "title": "Logical Access Security", "description": "The entity implements logical access security software and infrastructure."},
    {"id": "SOC2-CC6.2", "category": "Logical and Physical Access", "title": "User Registration", "description": "The entity implements registration and enrollment of users."},
    {"id": "SOC2-CC6.3", "category": "Logical and Physical Access", "title": "Role-Based Access", "description": "The entity authorizes, modifies, or removes access based on roles and responsibilities."},
    {"id": "SOC2-CC6.4", "category": "Logical and Physical Access", "title": "Physical Access", "description": "The entity implements physical access controls to protect systems and data."},
    {"id": "SOC2-CC6.5", "category": "Logical and Physical Access", "title": "Data Disposal", "description": "The entity securely disposes of data when no longer needed."},
    {"id": "SOC2-CC6.6", "category": "Logical and Physical Access", "title": "Credential Management", "description": "The entity implements credential management for system access."},
    {"id": "SOC2-CC6.7", "category": "Logical and Physical Access", "title": "Remote Access Security", "description": "The entity restricts and monitors remote access to systems."},
    {"id": "SOC2-CC6.8", "category": "Logical and Physical Access", "title": "Unauthorized Software Prevention", "description": "The entity prevents or detects unauthorized software."},
    {"id": "SOC2-CC7.1", "category": "System Operations", "title": "Infrastructure Monitoring", "description": "The entity monitors infrastructure for anomalies and potential security events."},
    {"id": "SOC2-CC7.2", "category": "System Operations", "title": "Incident Response", "description": "The entity designs and implements incident response procedures."},
    {"id": "SOC2-CC7.3", "category": "System Operations", "title": "Security Event Evaluation", "description": "The entity evaluates security events to determine if incidents have occurred."},
    {"id": "SOC2-CC7.4", "category": "System Operations", "title": "Incident Recovery", "description": "The entity implements incident recovery plans to restore operations."},
    {"id": "SOC2-CC7.5", "category": "System Operations", "title": "Threat Intelligence", "description": "The entity identifies and assesses threats from external and internal sources."},
    {"id": "SOC2-CC8.1", "category": "Change Management", "title": "Change Authorization", "description": "The entity authorizes, designs, develops, and tests changes before implementation."},
    {"id": "SOC2-CC8.2", "category": "Change Management", "title": "Change Documentation", "description": "The entity documents changes and maintains change records."},
    {"id": "SOC2-CC9.1", "category": "Risk Mitigation", "title": "Business Continuity", "description": "The entity implements business continuity plans and disaster recovery procedures."},
    {"id": "SOC2-CC9.2", "category": "Risk Mitigation", "title": "Vendor Risk Management", "description": "The entity assesses and monitors risks from vendors and business partners."},
]


FDA_SAMD_CLASSIFICATION = {
    "overview": "FDA Software as a Medical Device (SaMD) classification guidance for healthcare software platforms.",
    "framework": "IMDRF SaMD framework with risk-based classification (I-IV).",
    "categories": [
        {
            "class": "Class I (Low Risk)",
            "description": "Software providing information for general health/wellness without specific disease claims.",
            "examples": ["Fitness tracking", "General wellness apps", "Health education tools"],
            "requirements": ["Establishment registration", "Device listing", "Quality system regulation (exempt from most)"],
        },
        {
            "class": "Class II (Moderate Risk)",
            "description": "Software driving or moderating clinical management for specific conditions.",
            "examples": ["Drug interaction checkers", "Clinical decision support (non-critical)", "Image analysis tools"],
            "requirements": ["510(k) premarket notification", "Quality system regulation", "Unique device identification", "Post-market surveillance"],
        },
        {
            "class": "Class III (High Risk)",
            "description": "Software driving clinical management for critical conditions where erroneous output could cause death or serious injury.",
            "examples": ["Radiation therapy planning", "Automated insulin dosing", "Cardiac arrhythmia detection"],
            "requirements": ["PMA (Premarket Approval)", "Clinical trials", "Quality system regulation", "Post-market surveillance"],
        },
    ],
    "key_considerations": [
        "Intended use determines classification, not the technology itself",
        "Clinical significance of the information provided by the SaMD",
        "Healthcare situation and condition being addressed",
        "State of the art and availability of alternative treatments",
        "Cybersecurity requirements for connected SaMD",
        "Real-world performance monitoring for AI/ML-based SaMD",
    ],
    "predetermined_change_control": "FDA now allows predetermined change control plans for AI/ML-based SaMD, enabling iterative improvements without new submissions.",
    "guidance_documents": [
        "Clinical and Patient Decision Support Software (2022)",
        "Cybersecurity in Medical Devices (2023)",
        "Artificial Intelligence/Machine Learning-Based SaMD Action Plan",
        "Software Functions That Meet the Definition of a Device (2023)",
    ],
}


BAA_TEMPLATE = """BUSINESS ASSOCIATE AGREEMENT

This Business Associate Agreement ("Agreement") is entered into as of [DATE],
by and between [COVERED ENTITY NAME] ("Covered Entity") and
[BUSINESS ASSOCIATE NAME] ("Business Associate").

RECITALS

WHEREAS, Covered Entity is a covered entity as defined under the Health Insurance
Portability and Accountability Act of 1996 ("HIPAA") and the HITECH Act;

WHEREAS, Business Associate performs certain functions or activities on behalf of
Covered Entity that involve the use or disclosure of Protected Health Information ("PHI");

WHEREAS, the parties wish to comply with the requirements of 45 CFR Parts 160 and 164;

NOW, THEREFORE, in consideration of the mutual covenants contained herein, the parties agree as follows:

1. DEFINITIONS

1.1 "Breach" means the acquisition, access, use, or disclosure of PHI in a manner not
permitted under the Privacy Rule which compromises the security or privacy of the PHI.

1.2 "Covered Entity" has the same meaning as the term "covered entity" found at 45 CFR 160.103.

1.3 "Business Associate" has the same meaning as the term "business associate" found at 45 CFR 160.103.

1.4 "HIPAA Rules" means the Privacy Rule, Security Rule, Breach Notification Rule,
and the Omnibus Final Rule as amended by HITECH.

1.5 "Protected Health Information" or "PHI" means individually identifiable health
information as defined under 45 CFR 160.103.

1.6 "Secretary" means the Secretary of the Department of Health and Human Services.

2. OBLIGATIONS OF BUSINESS ASSOCIATE

2.1 Business Associate agrees to not use or further disclose PHI other than as permitted
or required by this Agreement or as Required by Law.

2.2 Business Associate agrees to use appropriate safeguards and comply with the
applicable requirements of the HIPAA Security Rule (45 CFR Part 164, Subpart C)
with respect to electronic PHI.

2.3 Business Associate agrees to report to Covered Entity any use or disclosure of PHI
not provided for by this Agreement of which it becomes aware, including Breaches of
Unsecured PHI, without unreasonable delay and in no case later than sixty (60) days
following discovery of a Breach.

2.4 Business Associate agrees to ensure that any subcontractors that create, receive,
maintain, or transmit PHI on behalf of Business Associate agree in writing to the same
restrictions and conditions that apply to Business Associate.

2.5 Business Associate agrees to make PHI available to Covered Entity as necessary to
satisfy Covered Entity's obligations under 45 CFR 164.524 (individual access).

2.6 Business Associate agrees to make PHI available for amendment and incorporate
amendments as directed by Covered Entity per 45 CFR 164.526.

2.7 Business Associate agrees to make its internal practices, books, and records relating
to the use and disclosure of PHI available to the Secretary for purposes of determining
compliance with the Privacy Rule.

2.8 Business Associate agrees to document such disclosures of PHI and information
related to such disclosures as would be required for Covered Entity to respond to a
request for an accounting of disclosures in accordance with 45 CFR 164.528.

2.9 Business Associate agrees to provide an accounting of disclosures of PHI upon
request by Covered Entity.

2.10 Business Associate agrees to comply with all applicable requirements of the HIPAA
Rules, including but not limited to the minimum necessary standard.

3. OBLIGATIONS OF COVERED ENTITY

3.1 Covered Entity shall notify Business Associate of any limitation(s) in its notice of
privacy practices in accordance with 45 CFR 164.520.

3.2 Covered Entity shall notify Business Associate of any changes in, or revocation or
modification of, permission granted to use or disclose PHI.

3.3 Covered Entity shall notify Business Associate of any restriction to the use or
disclosure of PHI that Covered Entity has agreed to in accordance with 45 CFR 164.522.

4. PERMITTED USES AND DISCLOSURES

4.1 Business Associate may use or disclose PHI as necessary to perform the services
described in the underlying Services Agreement.

4.2 Business Associate may use PHI for the proper management and administration of
Business Associate, provided that such uses and disclosures comply with applicable law.

4.3 Business Associate may use PHI to provide Data Aggregation services as permitted
under 45 CFR 164.504(e)(2)(i)(B).

5. SECURITY SAFEGUARDS

5.1 Business Associate shall implement administrative, physical, and technical safeguards
that reasonably and appropriately protect the confidentiality, integrity, and availability
of electronic PHI.

5.2 Business Associate shall ensure that all electronic PHI created, received, maintained,
or transmitted on behalf of Covered Entity is encrypted in accordance with NIST
standards (AES-256 for data at rest, TLS 1.2+ for data in transit).

5.3 Business Associate shall maintain audit logs of all access to PHI for a minimum of
six (6) years.

5.4 Business Associate shall conduct risk assessments at least annually and upon any
material change to systems or processes.

6. BREACH NOTIFICATION

6.1 Business Associate shall notify Covered Entity of any Breach of Unsecured PHI
without unreasonable delay and in no case later than sixty (60) days following discovery.

6.2 Notification shall include: (a) identification of each individual whose PHI was
involved; (b) identification of the PHI involved; (c) a brief description of what happened;
(d) the date of the Breach and discovery; and (e) any other information required by law.

7. TERM AND TERMINATION

7.1 This Agreement shall be effective as of the date first written above and shall remain
in effect until terminated.

7.2 Either party may terminate this Agreement upon thirty (30) days written notice if
the other party materially breaches this Agreement and fails to cure such breach within
the notice period.

7.3 Upon termination, Business Associate shall return or destroy all PHI received from
or created on behalf of Covered Entity. If return or destruction is not feasible, Business
Associate shall extend the protections of this Agreement to such PHI.

8. MISCELLANEOUS

8.1 This Agreement shall be governed by and construed in accordance with applicable
federal law, including HIPAA and the HITECH Act.

8.2 The Regulatory References in this Agreement mean the cited section of the HIPAA
Rules as amended from time to time.

8.3 If any provision of this Agreement is held to be invalid or unenforceable, the
remaining provisions shall continue in full force and effect.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first above written.

COVERED ENTITY:                          BUSINESS ASSOCIATE:

_________________________                _________________________
Name:                                    Name:
Title:                                   Title:
Date:                                    Date:
"""


class ComplianceAuditor:
    """Manages HIPAA compliance auditing, access logging, and regulatory guidance."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
    ) -> None:
        self.data_dir = Path(data_dir or os.path.join(os.path.dirname(__file__), "..", "data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.audit_log_path = self.data_dir / "audit_log.json"
        self.access_log_path = self.data_dir / "access_log.json"

        self._audit_results: list[dict[str, Any]] = []
        self._access_log: list[dict[str, Any]] = []

        self._load()

    def _load(self) -> None:
        if self.audit_log_path.exists():
            try:
                with open(self.audit_log_path, "r") as f:
                    self._audit_results = json.load(f)
            except (json.JSONDecodeError, KeyError):
                self._audit_results = []
        else:
            self._audit_results = []

        if self.access_log_path.exists():
            try:
                with open(self.access_log_path, "r") as f:
                    self._access_log = json.load(f)
            except (json.JSONDecodeError, KeyError):
                self._access_log = []
        else:
            self._access_log = []

    def _save_audit_log(self) -> None:
        with open(self.audit_log_path, "w") as f:
            json.dump(self._audit_results, f, indent=2)

    def _save_access_log(self) -> None:
        with open(self.access_log_path, "w") as f:
            json.dump(self._access_log, f, indent=2)

    def run_audit(self, overrides: Optional[dict[str, bool]] = None) -> dict[str, Any]:
        """Run all HIPAA compliance checks and return results."""
        overrides = overrides or {}
        results = []
        passed = 0
        failed = 0

        for check in HIPAA_CHECKS:
            check_id = check["id"]
            status = overrides.get(check_id, "fail")
            if status == "pass":
                passed += 1
            else:
                failed += 1

            result = {
                "id": check_id,
                "category": check["category"],
                "title": check["title"],
                "description": check["description"],
                "status": status,
                "remediation": check["remediation"],
                "audited_at": datetime.utcnow().isoformat() + "Z",
            }
            results.append(result)

        self._audit_results = results
        self._save_audit_log()

        total = len(results)
        return {
            "audit_id": f"AUDIT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "score": round((passed / total) * 100, 1) if total > 0 else 0,
            "results": results,
        }

    def get_compliance_score(self) -> dict[str, Any]:
        """Calculate current compliance score."""
        if not self._audit_results:
            self.run_audit()

        total = len(self._audit_results)
        passed = sum(1 for r in self._audit_results if r["status"] == "pass")
        failed = total - passed

        category_scores: dict[str, dict[str, int]] = {}
        for r in self._audit_results:
            cat = r["category"]
            if cat not in category_scores:
                category_scores[cat] = {"total": 0, "passed": 0}
            category_scores[cat]["total"] += 1
            if r["status"] == "pass":
                category_scores[cat]["passed"] += 1

        for cat in category_scores:
            total_cat = category_scores[cat]["total"]
            passed_cat = category_scores[cat]["passed"]
            category_scores[cat]["score"] = round((passed_cat / total_cat) * 100, 1) if total_cat > 0 else 0

        return {
            "overall_score": round((passed / total) * 100, 1) if total > 0 else 0,
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "category_scores": category_scores,
            "last_audit": self._audit_results[-1]["audited_at"] if self._audit_results else None,
        }

    def get_gap_report(self) -> dict[str, Any]:
        """Return list of failing checks with remediation steps."""
        if not self._audit_results:
            self.run_audit()

        gaps = [
            {
                "id": r["id"],
                "category": r["category"],
                "title": r["title"],
                "description": r["description"],
                "remediation": r["remediation"],
                "priority": "high" if r["category"] in ("Technical Safeguards", "Breach Notification") else "medium",
            }
            for r in self._audit_results
            if r["status"] == "fail"
        ]

        return {
            "total_gaps": len(gaps),
            "high_priority": sum(1 for g in gaps if g["priority"] == "high"),
            "medium_priority": sum(1 for g in gaps if g["priority"] == "medium"),
            "gaps": gaps,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def log_access_event(
        self,
        user: str,
        patient_id: str,
        action: str,
        resource: str,
        ip_address: str,
    ) -> dict[str, Any]:
        """Log a PHI access event."""
        event = {
            "event_id": f"EVT-{len(self._access_log) + 1:06d}",
            "user": user,
            "patient_id": patient_id,
            "action": action,
            "resource": resource,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self._access_log.append(event)
        self._save_access_log()
        logger.info("Access event logged: %s by %s on %s", action, user, patient_id)
        return event

    def get_access_log(
        self,
        patient_id: Optional[str] = None,
        user: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve access log entries with optional filtering."""
        results = self._access_log

        if patient_id:
            results = [e for e in results if e.get("patient_id") == patient_id]
        if user:
            results = [e for e in results if e.get("user") == user]

        results = sorted(results, key=lambda e: e.get("timestamp", ""), reverse=True)
        return results[:limit]

    def generate_baa_template(self) -> str:
        """Return a Business Associate Agreement template."""
        return BAA_TEMPLATE

    def get_soc2_checklist(self) -> dict[str, Any]:
        """Return SOC 2 Type II readiness checklist."""
        return {
            "framework": "SOC 2 Type II - Trust Services Criteria",
            "total_controls": len(SOC2_CHECKLIST),
            "categories": list({c["category"] for c in SOC2_CHECKLIST}),
            "checklist": SOC2_CHECKLIST,
            "readiness_notes": [
                "SOC 2 Type II requires evidence of control operation over a period (typically 6-12 months)",
                "Engage a qualified CPA firm for the audit",
                "Gap assessment recommended before formal audit engagement",
                "HIPAA compliance provides strong foundation for Security criteria",
            ],
        }

    def get_fda_samd_classification(self) -> dict[str, Any]:
        """Return FDA Software as Medical Device classification guidance."""
        return FDA_SAMD_CLASSIFICATION
