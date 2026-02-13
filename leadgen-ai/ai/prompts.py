"""
AI prompt templates for Gemini.
Structured prompts that force consistent, usable output.
"""


def audit_summary_prompt(business_name: str, industry: str, location: str, audit: dict) -> str:
    """
    Generate prompt for AI audit summary.
    Forces structured output explaining problems in business terms.
    """
    issues_text = ""
    for issue in audit.get('major_issues', [])[:10]:
        issues_text += f"- [{issue.get('severity', 'info').upper()}] {issue.get('issue', '')}\n"
    
    if not issues_text:
        issues_text = "- No major issues detected\n"
    
    return f"""Analyze this website audit for a {industry} business and provide a brief, professional summary.

BUSINESS: {business_name}
INDUSTRY: {industry}
LOCATION: {location}

AUDIT SCORES:
- Performance: {audit.get('performance_score', 'N/A')}/100
- SEO: {audit.get('seo_score', 'N/A')}/100
- Accessibility: {audit.get('accessibility_score', 'N/A')}/100
- Mobile Friendly: {"Yes" if audit.get('mobile_friendly') else "No"}
- SSL Valid: {"Yes" if audit.get('ssl_valid') else "No"}
- Page Load: {audit.get('load_time_ms', 'N/A')}ms

ISSUES FOUND:
{issues_text}

Respond in EXACTLY this JSON format:
{{
    "summary": "2-3 sentence plain English summary of the website's condition",
    "business_impact": "1-2 sentences explaining how these issues hurt their business specifically as a {industry}",
    "top_problems": ["problem 1 in plain English", "problem 2", "problem 3"],
    "urgency": "high" or "medium" or "low"
}}

Rules:
- Write for a non-technical business owner
- Be factual, not alarmist
- Reference their specific industry
- Keep it under 150 words total
- Output ONLY valid JSON, no other text"""


def outreach_email_prompt(business_name: str, industry: str, location: str,
                          audit_summary: dict, service: str, sender_name: str) -> str:
    """
    Generate prompt for personalized outreach email.
    The email should feel human-written, not AI-generated.
    """
    problems = audit_summary.get('top_problems', ['website performance issues'])
    problems_text = '\n'.join(f"- {p}" for p in problems[:3])
    
    return f"""Write a short, professional outreach email to a {industry} business owner.

RECIPIENT:
- Business: {business_name}
- Industry: {industry}
- Location: {location}

THEIR WEBSITE ISSUES:
{problems_text}

Business Impact: {audit_summary.get('business_impact', 'Their website may be underperforming.')}
Urgency: {audit_summary.get('urgency', 'medium')}

SERVICE OFFERED: {service}
SENDER: {sender_name}

Respond in EXACTLY this JSON format:
{{
    "subject_line": "Email subject - specific to their business, not generic",
    "email_body": "The full email text"
}}

EMAIL RULES:
- Maximum 150 words for the body
- Open with a specific observation about THEIR website (not generic)
- Include a subtle authority line like "I run performance audits for small local businesses" — no bragging, just existence proof
- Mention ONE concrete problem and its business impact
- Frame the loss competitively: "visitors tend to check the next option" or "that traffic goes to a competitor"
- Include a brief social proof hint: "I've helped similar local businesses improve..."
- Offer a quick call, not a hard sell
- Tone: helpful professional, not salesy
- NO fake urgency or pressure tactics
- NO "I noticed your website" cliche opener
- End with a clear but low-pressure close like "If you're open to it, I can show you exactly what I found."
- Include an unsubscribe note at the bottom
- Sound like a real person, not an AI
- Output ONLY valid JSON, no other text"""


def lead_qualification_prompt(business_name: str, industry: str, 
                               audit: dict, scoring: dict) -> str:
    """
    Generate prompt for AI-enhanced lead qualification.
    Supplements deterministic scoring with contextual reasoning.
    """
    return f"""Evaluate this business lead for outreach potential.

BUSINESS: {business_name}
INDUSTRY: {industry}

SCORES:
- Website Performance: {audit.get('performance_score', 'N/A')}/100
- SEO: {audit.get('seo_score', 'N/A')}/100
- Deterministic Priority: {scoring.get('priority', 'N/A')}
- Total Issues: {scoring.get('total_issues', 0)}
- Critical Issues: {scoring.get('critical_issues', 0)}

Respond in EXACTLY this JSON format:
{{
    "should_contact": true or false,
    "confidence": 0-100,
    "reasoning": "One sentence explaining why",
    "best_time_to_contact": "morning" or "afternoon" or "evening",
    "estimated_deal_size": "small" or "medium" or "large"
}}

Rules:
- Base decision on data, not assumptions
- {industry} businesses with poor websites are usually good leads
- If too many critical issues, the site might be abandoned - lower priority
- Output ONLY valid JSON, no other text"""
