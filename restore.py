import re
import os

log_path = r'c:\Users\Anura\.gemini\antigravity\brain\4753e62c-6425-4287-bd7c-ea97ee74f979\.system_generated\logs\overview.txt'

with open(log_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the JSON array of emails
match = re.search(r'\[\s*\{\s*"id":\s*"email_.*?\n\s*\]', content, re.DOTALL)
if match:
    # Ensure it's purely ascii
    json_str = match.group(0).encode('ascii', 'ignore').decode('ascii')
    out_path = r'c:\Users\Anura\Python\Hackathons\MPO X SST Hackathon [25-03-26]\email_triage_env\data\emails.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(json_str)
    print("Extracted emails successfully.")
else:
    print("Could not find the JSON array in the log.")
