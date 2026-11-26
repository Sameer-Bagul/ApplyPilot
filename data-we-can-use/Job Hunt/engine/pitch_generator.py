"""
Referral & Outreach Intelligence Engine (Phase 5)
Generates high-converting, personalized outreach pitch messages based on Sameer's CV proof points.
"""

from typing import Dict, Any

TEMPLATES = {
    "agentic_rag": {
        "name": "Angle 1: Agentic AI & RAG Engineer",
        "description": "Best for AI startups, agentic workflows, LLM application teams, and LangGraph roles.",
        "subject": "Quick note regarding {role_title} / GenAI Engineering at {company_name}",
        "body": """Hi {recipient_name},

I’ve been following {company_name}’s work in {category_or_domain} and wanted to reach out directly. 

I’m an Applied AI Engineer specializing in production multi-agent systems and RAG architectures. Recently, I've built:
• Production LangGraph agentic pipelines orchestrating multi-step reasoning, tool-calling, and state-machine workflows.
• High-accuracy RAG architectures with hybrid keyword-vector retrieval, contextual reranking, and synthetic evaluation benchmarks.
• Robust Python backends (FastAPI) integrated with Docker and deployed to AWS.

Given {company_name}'s trajectory, I'd love to contribute to your engineering team as a {role_title}. Would you be open to a brief 10-minute chat or passing my profile to the hiring team?

Resume & GitHub: https://github.com/sameerbagul
Best regards,
Sameer Bagul
Pune, India | sameer.bagul@example.com"""
    },
    "ai_qa_automation": {
        "name": "Angle 2: AI-Native Testing & Automation",
        "description": "Best for teams building reliable software, automated evaluation pipelines, or Playwright testing.",
        "subject": "AI-Driven Automation & QA Engineering @ {company_name}",
        "body": """Hi {recipient_name},

Hope you’re having a great week! 

I noticed {company_name} is expanding engineering capabilities, and I wanted to reach out regarding {role_title}.

My engineering focus bridges AI systems and resilient automated validation:
• Developed autonomous end-to-end testing harnesses using Playwright and Python that cut regression cycles by 60%.
• Built LLM-assisted synthetic test generation and evaluation suites to benchmark LLM latency, drift, and accuracy.
• Shipped resilient CI/CD pipelines with containerized Docker runners.

I'd welcome the chance to share how I can bring immediate velocity and reliability to {company_name}’s releases. Open to a brief sync this week?

Best regards,
Sameer Bagul
Pune, India | https://github.com/sameerbagul"""
    },
    "fullstack_product": {
        "name": "Angle 3: Full-Stack Product & Backend Engineer",
        "description": "Best for product startups, founding engineer roles, and fast-paced engineering teams.",
        "subject": "Full-Stack / Python Backend Engineer for {company_name}",
        "body": """Hi {recipient_name},

I saw {company_name} is hiring for engineering talent and wanted to connect. 

I build full-stack web applications with an AI-first mindset:
• End-to-end systems: Python (FastAPI/Django) backends, relational & vector databases (PostgreSQL/pgvector), and modern React frontends.
• Shipped intuitive dashboards and interactive customer-facing interfaces with tight API contract guarantees.
• Quick to deploy, accustomed to high-ownership environments where engineers ship from concept to production.

I’m based in Pune (open to Pune on-site/hybrid or remote) and would love to support {company_name}’s product roadmap. Do you have 10 minutes to connect?

Best regards,
Sameer Bagul
Pune, India | https://github.com/sameerbagul"""
    }
}

def generate_pitch(angle_key: str, context: Dict[str, Any]) -> Dict[str, str]:
    tmpl = TEMPLATES.get(angle_key, TEMPLATES["agentic_rag"])
    recipient_name = context.get("recipient_name") or "there"
    company_name = context.get("company_name") or "your company"
    role_title = context.get("role_title") or "AI / Software Engineer"
    category_or_domain = context.get("category_or_domain") or "AI and software engineering"

    subject = tmpl["subject"].format(
        company_name=company_name,
        role_title=role_title,
        recipient_name=recipient_name,
        category_or_domain=category_or_domain
    )

    body = tmpl["body"].format(
        company_name=company_name,
        role_title=role_title,
        recipient_name=recipient_name,
        category_or_domain=category_or_domain
    )

    return {
        "angle_name": tmpl["name"],
        "subject": subject,
        "body": body
    }

def get_contact_search_urls(company_name: str) -> Dict[str, str]:
    import urllib.parse
    q_emp = urllib.parse.quote(f"{company_name} software engineer Pune")
    q_em = urllib.parse.quote(f"{company_name} engineering manager OR lead")
    q_rec = urllib.parse.quote(f"{company_name} technical recruiter OR talent acquisition")
    q_founder = urllib.parse.quote(f"{company_name} founder OR CEO OR CTO")

    return {
        "employees": f"https://www.linkedin.com/search/results/people/?keywords={q_emp}",
        "engineering_managers": f"https://www.linkedin.com/search/results/people/?keywords={q_em}",
        "recruiters": f"https://www.linkedin.com/search/results/people/?keywords={q_rec}",
        "founders": f"https://www.linkedin.com/search/results/people/?keywords={q_founder}"
    }
