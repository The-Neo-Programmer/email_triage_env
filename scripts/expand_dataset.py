import json
import os

new_emails = [
    {
        "id": "email_011",
        "sender": "angry.customer@external.com",
        "recipient": "support@company.com",
        "subject": "URGENT: Broken feature costing us money",
        "body": "I am absolutely furious. The new update you pushed last night broke the payment gateway integration. We have lost over $10,000 in sales in the last 4 hours alone. I need someone to fix this immediately or we are taking our business elsewhere. Call me on my cell.",
        "timestamp": "2026-04-07T08:15:00Z",
        "ground_truth": {
            "urgency": "critical",
            "category": "incident",
            "action_items": [
                "Fix the payment gateway integration immediately",
                "Call the customer on their cell to provide an update/apology",
                "Escalate the issue to the engineering and account management teams"
            ],
            "ideal_response_keywords": [
                "apologize", "escalating", "fix", "payment", "call", "urgent"
            ]
        }
    },
    {
        "id": "email_012",
        "sender": "ceo@company.com",
        "recipient": "all-employees@company.com",
        "subject": "Company All-Hands Next Thursday",
        "body": "Team, please join us for our quarterly all-hands meeting next Thursday at 10 AM. We will be sharing our Q1 results and detailing the roadmap for the rest of the year. The meeting link is attached. Attendance is mandatory.",
        "timestamp": "2026-04-07T09:00:00Z",
        "ground_truth": {
            "urgency": "medium",
            "category": "info",
            "action_items": [
                "Attend the quarterly all-hands meeting next Thursday at 10 AM"
            ],
            "ideal_response_keywords": [
                "attend", "roadmap", "meeting", "confirm"
            ]
        }
    },
    {
        "id": "email_013",
        "sender": "sales.guru@sales.marketing.com",
        "recipient": "lead.engineer@company.com",
        "subject": "10x your engineering velocity?",
        "body": "Hi there, I noticed your company has been growing rapidly. We offer a cutting-edge AI-driven platform that guarantees to 10x your engineers' productivity. Do you have 15 minutes next Tuesday for a quick demo?",
        "timestamp": "2026-04-07T10:30:00Z",
        "ground_truth": {
            "urgency": "low",
            "category": "spam",
            "action_items": [],
            "ideal_response_keywords": []
        }
    },
    {
        "id": "email_014",
        "sender": "backend.dev@company.com",
        "recipient": "devops-team@company.com",
        "subject": "Bug Report: OOM error in auth microservice",
        "body": "Hey DevOps, the authentication microservice just crashed with an OutOfMemoryError. \nStack trace:\njava.lang.OutOfMemoryError: Java heap space\n    at com.auth.TokenGenerator.generate(TokenGenerator.java:45)\nPlease bump the memory limit for the auth pods in production and restart the service.",
        "timestamp": "2026-04-07T14:45:00Z",
        "ground_truth": {
            "urgency": "high",
            "category": "incident",
            "action_items": [
                "Increase the memory limit for auth pods in production",
                "Restart the authentication microservice"
            ],
            "ideal_response_keywords": [
                "memory", "limit", "restart", "auth", "fix", "microservice"
            ]
        }
    },
    {
        "id": "email_015",
        "sender": "project.manager@company.com",
        "recipient": "design-team@company.com, engineering-lead@company.com",
        "subject": "Kickoff: Mobile App Redesign",
        "body": "Hi everyone, we are officially kicking off the Mobile App Redesign project. Design team, please share the initial wireframes by next Wednesday. Engineering, please prepare the technical feasibility document by Friday. Let me know if you need any clarification on the PRD.",
        "timestamp": "2026-04-08T09:15:00Z",
        "ground_truth": {
            "urgency": "medium",
            "category": "collaboration",
            "action_items": [
                "Share initial wireframes by next Wednesday (Design team)",
                "Prepare technical feasibility document by Friday (Engineering)"
            ],
            "ideal_response_keywords": [
                "wireframes", "feasibility", "Wednesday", "Friday", "design", "PRD"
            ]
        }
    },
    {
        "id": "email_016",
        "sender": "facilities@company.com",
        "recipient": "all-employees@company.com",
        "subject": "Elevator Maintenance Notice",
        "body": "Please be advised that the main elevators in Building B will be undergoing maintenance this weekend from Saturday 8 AM to Sunday 5 PM. If you need building access during this time, please use the freight elevator.",
        "timestamp": "2026-04-08T11:00:00Z",
        "ground_truth": {
            "urgency": "low",
            "category": "info",
            "action_items": [],
            "ideal_response_keywords": []
        }
    },
    {
        "id": "email_017",
        "sender": "recruiter@headhunters.io",
        "recipient": "senior.dev@company.com",
        "subject": "Exclusive Opportunity at a Stealth Startup",
        "body": "Hi, I came across your profile and was very impressed by your background. We are hiring for a Lead Developer role at a well-funded stealth AI startup with a competitive compensation package. Would you be open to a brief chat?",
        "timestamp": "2026-04-08T13:20:00Z",
        "ground_truth": {
            "urgency": "low",
            "category": "spam",
            "action_items": [],
            "ideal_response_keywords": []
        }
    },
    {
        "id": "email_018",
        "sender": "billing@cloudprovider.com",
        "recipient": "finance@company.com",
        "subject": "Action Required: Update Payment Method",
        "body": "Your recent payment for your cloud services invoice failed because the credit card on file has expired. Please log into your billing dashboard and update your payment method within 48 hours to prevent account suspension.",
        "timestamp": "2026-04-08T15:05:00Z",
        "ground_truth": {
            "urgency": "high",
            "category": "request",
            "action_items": [
                "Log into the cloud provider billing dashboard",
                "Update payment method with a valid credit card within 48 hours"
            ],
            "ideal_response_keywords": [
                "billing", "update", "payment", "card", "failed"
            ]
        }
    },
    {
        "id": "email_019",
        "sender": "client.success@company.com",
        "recipient": "onboarding@company.com",
        "subject": "New Enterprise Client Onboarding - Acme Corp",
        "body": "Hi team, Acme Corp just signed the enterprise contract. We need to set up their dedicated tenant by end of day tomorrow. Please provision the database and create admin accounts for john.doe@acme.com and jane.smith@acme.com. Let me know once done.",
        "timestamp": "2026-04-09T08:30:00Z",
        "ground_truth": {
            "urgency": "high",
            "category": "request",
            "action_items": [
                "Provision dedicated database tenant for Acme Corp by EoD tomorrow",
                "Create admin accounts for john.doe@acme.com and jane.smith@acme.com",
                "Notify Client Success once onboarding setup is complete"
            ],
            "ideal_response_keywords": [
                "provision", "tenant", "accounts", "done", "tomorrow", "Acme"
            ]
        }
    },
    {
        "id": "email_020",
        "sender": "design.lead@company.com",
        "recipient": "marketing.team@company.com",
        "subject": "Review: Q2 Campaign Assets",
        "body": "Hi Marketing, the initial drafts for the Q2 social media campaign are ready for your review. I've uploaded them to the shared Drive folder. Please leave your comments directly on the files by Thursday so we can finalize by Friday.",
        "timestamp": "2026-04-09T10:15:00Z",
        "ground_truth": {
            "urgency": "medium",
            "category": "collaboration",
            "action_items": [
                "Review Q2 social media campaign assets in the shared Drive",
                "Leave comments on the asset files by Thursday"
            ],
            "ideal_response_keywords": [
                "review", "assets", "Drive", "Thursday", "feedback"
            ]
        }
    },
    {
        "id": "email_021",
        "sender": "security-system@internal.domain",
        "recipient": "sysadmin@company.com",
        "subject": "CRITICAL: Multiple failed SSH login attempts",
        "body": "Automated alert: 500+ failed SSH login attempts detected on production server 'db-master-01' from IP 192.168.45.12 within the last 5 minutes. Possible brute-force attack in progress. Immediate intervention advised.",
        "timestamp": "2026-04-09T23:45:00Z",
        "ground_truth": {
            "urgency": "critical",
            "category": "incident",
            "action_items": [
                "Investigate multiple failed SSH login attempts on db-master-01",
                "Block IP 192.168.45.12 to mitigate potential brute-force attack"
            ],
            "ideal_response_keywords": [
                "investigate", "block", "IP", "SSH", "attack", "db-master"
            ]
        }
    },
    {
        "id": "email_022",
        "sender": "compliance-officer@company.com",
        "recipient": "legal-team@company.com",
        "subject": "New Data Privacy Regulations (GDPR Update)",
        "body": "There has been an update to the GDPR guidelines regarding cookie consent. Please review the attached summary document and advise on necessary changes to our website's privacy policy by end of month.",
        "timestamp": "2026-04-10T09:00:00Z",
        "ground_truth": {
            "urgency": "medium",
            "category": "request",
            "action_items": [
                "Review the attached GDPR update summary document",
                "Advise on required changes to the website privacy policy by EOM"
            ],
            "ideal_response_keywords": [
                "review", "GDPR", "policy", "privacy", "advise"
            ]
        }
    },
    {
        "id": "email_023",
        "sender": "lunch@food-delivery.com",
        "recipient": "employee@company.com",
        "subject": "Your lunch order is on the way!",
        "body": "Good news! Your order from 'Salad Spot' has been picked up and is arriving soon. Track your assigned driver in the app.",
        "timestamp": "2026-04-10T11:45:00Z",
        "ground_truth": {
            "urgency": "low",
            "category": "info",
            "action_items": [],
            "ideal_response_keywords": []
        }
    },
    {
        "id": "email_024",
        "sender": "partner-support@api-service.net",
        "recipient": "dev-team@company.com",
        "subject": "Deprecation Notice: API v2 ending May 1",
        "body": "This is a reminder that API v2 will be permanently retired on May 1. Based on our logs, your integration is still making calls to v2 endpoints. Please migrate to API v3 immediately to avoid service disruptions.",
        "timestamp": "2026-04-10T14:30:00Z",
        "ground_truth": {
            "urgency": "high",
            "category": "info",
            "action_items": [
                "Migrate integrations from API v2 to API v3 before May 1"
            ],
            "ideal_response_keywords": [
                "migrate", "API", "v3", "deprecation", "update"
            ]
        }
    },
    {
        "id": "email_025",
        "sender": "ceo-update@suspicious-domain.com",
        "recipient": "finance@company.com",
        "subject": "Urgent Wire Transfer Needed",
        "body": "I am currently in a meeting with a potential supplier and cannot talk. I need you to initiate a wire transfer of $50,000 to the attached bank details immediately to secure this deal. Do it ASAP and keep it confidential.",
        "timestamp": "2026-04-10T16:00:00Z",
        "ground_truth": {
            "urgency": "critical",
            "category": "incident",
            "action_items": [
                "Report suspicious email to IT security team as potential CEO fraud",
                "Do NOT process the requested wire transfer"
            ],
            "ideal_response_keywords": [
                "phishing", "fraud", "security", "report", "wire"
            ]
        }
    }
]

import os

dataset_path = r"c:\Users\Anura\Python\Hackathons\MPO X SST Hackathon [25-03-26]\email_triage_env\data\emails.json"
with open(dataset_path, "r", encoding="utf-8") as f:
    data = json.load(f)

data.extend(new_emails)

with open(dataset_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print("Dataset expanded successfully.")
