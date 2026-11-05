import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

# Add src to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from applypilot.database import get_connection, store_qa

def build_vault():
    project_root = Path(__file__).resolve().parent.parent
    user_home = Path.home()
    applypilot_dir = user_home / ".applypilot"
    applypilot_dir.mkdir(parents=True, exist_ok=True)
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 [1/6] Copying and verifying Resume PDF & TXT...")
    source_cv = project_root / "sameer-bagul-CV.pdf"
    target_cv = applypilot_dir / "resume.pdf"
    if source_cv.exists():
        shutil.copy2(source_cv, target_cv)
        print(f"  ✓ Copied CV to {target_cv} ({target_cv.stat().st_size} bytes)")
    
    with open(project_root / "my-experience.txt", "r", encoding="utf-8") as f:
        experience_raw = f.read()

    target_txt = applypilot_dir / "resume.txt"
    with open(target_txt, "w", encoding="utf-8") as f:
        f.write(experience_raw)
    print(f"  ✓ Written resume text to {target_txt}")

    print("🔍 [2/6] Parsing my-experience.txt into structured work experience...")
    experiences = [
        {
            "id": "revcloud",
            "company": "Revcloud",
            "role": "AI Engineer",
            "location": "Pune, India",
            "employment_type": "Full-time",
            "start_date": "Aug 2026",
            "end_date": "Present",
            "is_current": True,
            "summary": "Engineer production-ready AI and software capabilities across Revcloud's B2B lead-generation and revenue funnel, owning features from PRD and architecture through testing, deployment, and monitoring.",
            "highlights": [
                "Engineer production-ready AI and software capabilities across Revcloud’s B2B lead-generation and revenue funnel, owning features from PRD and system architecture through implementation, testing, deployment, and monitoring.",
                "Develop AI-driven traffic and lead-routing systems that combine semantic signals, funnel analytics, and revenue outcomes to improve traffic allocation and routing decisions.",
                "Contribute to Alyson.ai, an AI-powered customer-acquisition platform for generating and optimizing landing pages, routing traffic, capturing leads, and automating customer interactions.",
                "Build LLM applications and agentic workflows using multiple model providers, LangChain, LangGraph, RAG, hybrid retrieval, semantic search, and production APIs across Node.js, Python, React, Next.js, and Astro.",
                "Develop an AI meeting-intelligence workflow that processes conversations through transcription, chunking, semantic retrieval, and agentic post-processing to generate structured notes, action items, and automated follow-ups.",
                "Build and operate AI systems on AWS with Docker, CI/CD, logging, monitoring, evaluation, and LLMOps practices across the development-to-production lifecycle."
            ],
            "skills": ["Python", "TypeScript", "Node.js", "React", "Next.js", "Astro", "LangChain", "LangGraph", "RAG", "Semantic Search", "AWS", "Docker", "LLMOps"]
        },
        {
            "id": "dimakh",
            "company": "Dimakh Consultants",
            "role": "AI Developer",
            "location": "Pune, India",
            "employment_type": "Full-time",
            "start_date": "Apr 2026",
            "end_date": "Aug 2026",
            "is_current": False,
            "summary": "Built and deployed production software and AI services for business workflows across sales, customer support, and lead engagement.",
            "highlights": [
                "Built and deployed production software and AI services for business workflows across sales, customer support, and lead engagement, owning features from requirements through deployment.",
                "Integrated an AI assistant into Sudapedia, a production business application for Sudarshan Chemical Industries, bringing LLM-powered retrieval into sales workflows.",
                "Built an AI customer assistant for a client website, combining LLM orchestration, business knowledge, retrieval, and application APIs to handle customer questions.",
                "Developed AI calling workflows for sales teams, working on conversation orchestration, prompt design, token optimization, and backend integrations.",
                "Designed RAG and agentic workflows that connected business knowledge, application data, and external APIs to produce context-aware responses."
            ],
            "skills": ["Python", "LangChain", "RAG", "Agentic AI", "Prompt Engineering", "FastAPI", "REST APIs", "Token Optimization"]
        },
        {
            "id": "bug0",
            "company": "Bug0",
            "role": "Software Engineer",
            "location": "Remote",
            "employment_type": "Full-time",
            "start_date": "Nov 2025",
            "end_date": "Mar 2026",
            "is_current": False,
            "summary": "Built core components of Bug0's AI-native testing platform around Playwright for generating, executing, and maintaining automated end-to-end regression tests.",
            "highlights": [
                "Built core components of Bug0’s AI-native testing platform, developing agentic browser-testing workflows around Playwright for generating, executing, and maintaining end-to-end regression tests.",
                "Developed Node.js backend services and CI/CD integrations using Docker and GitHub Actions, reducing deployment cycle time by 70%.",
                "Worked directly with customer engineering teams, including Vercel and Drumwave, to integrate testing workflows, debug production issues, and adapt to real application environments.",
                "Built supporting tooling around test execution, failure analysis, and AI inference to improve reliability in automated QA workflows."
            ],
            "skills": ["Playwright", "Node.js", "TypeScript", "Docker", "GitHub Actions", "CI/CD", "E2E Testing", "Browser Automation"]
        },
        {
            "id": "labscheck",
            "company": "LabsCheck",
            "role": "DevOps Engineer",
            "location": "Pune, India",
            "employment_type": "Full-time",
            "start_date": "Aug 2025",
            "end_date": "Oct 2025",
            "is_current": False,
            "summary": "Engineered enterprise-grade AI Agents, advanced RAG pipelines, scalable AI inference backends on GCP/AWS, and managed end-to-end DevOps operations, CI/CD, and B2C healthcare platforms.",
            "highlights": [
                "Engineered enterprise-grade AI Agents and advanced RAG pipelines, leveraging high-level tool chaining to automate complex workflows and cut manual B2B operations by 50%+.",
                "Architected scalable AI inference backends deployed on GCP and AWS, ensuring high availability and seamless connectivity between AI agents and core business applications.",
                "Designed and developed highly performant, SEO-optimized web platforms and cross-platform React Native mobile applications.",
                "Owned the end-to-end delivery lifecycle - from gathering client requirements to production handoff and iterative optimizations.",
                "Developed the core architecture of Bug0, an AI-agentic testing platform integrating directly with GitHub Actions to automate interval-based AI Playwright testing.",
                "Built high-throughput Node.js backend services and CI/CD pipelines (Docker, GitHub Actions), reducing deployment cycle times by 40%.",
                "Acted as a Forward Deployed Engineer, directly interfacing with enterprise clients to implement custom testing pipelines and drive core product adoption.",
                "Refactored system architectures to halve cold-start latency and significantly improve testing reliability on production deployments.",
                "Spearheaded the development of a React Native mobile app and the core business logic for a B2C healthcare aggregator, connecting users to affordable diagnostic labs.",
                "Architected RESTful APIs using the MERN stack, facilitating the processing of 100,000+ inbound leads via AI-driven smart routing.",
                "Managed end-to-end DevOps operations, configuring Nginx reverse proxies, Contabo VPNs, and Docker containers for secure infrastructure.",
                "Optimized backend queries to improve API response times by 35% and implemented integration testing to reduce post-deployment bugs by 60%."
            ],
            "skills": [
                "DevOps", "Docker", "GCP", "AWS", "Nginx", "Contabo VPNs", "CI/CD",
                "GitHub Actions", "AI Agents", "RAG", "React Native", "Node.js",
                "MERN Stack", "Playwright", "Integration Testing"
            ]
        }
    ]

    education = [
        {
            "institution": "PES Modern College of Engineering",
            "degree": "Bachelor of Technology in Information Technology",
            "location": "Pune, India",
            "start_year": "2022",
            "end_year": "2026",
            "cgpa": "7.77 / 10",
            "percentile": "94.95 (MHT-CET)",
            "coursework": [
                "Data Structures & Algorithms",
                "Machine Learning",
                "Database Management Systems",
                "Operating Systems",
                "Software Engineering",
                "Distributed Systems"
            ]
        }
    ]

    achievements = [
        {
            "title": "Smart India Hackathon 2024",
            "role": "National Runner-up",
            "description": "Built an AI-powered adaptive skills-learning system using TypeScript, Node.js, and React, with an agentic learning workflow that dynamically updated user roadmaps from weekly assessments."
        },
        {
            "title": "Innovate You Hackathon 2025",
            "role": "National Winner, AI/Automation",
            "description": "Built an end-to-end AI-powered process-automation platform focused on using agentic workflows to automate multi-step tasks and reduce manual operational effort."
        },
        {
            "title": "India Innovates 2026",
            "role": "National Finalist (Top 5,000 / 1.26 Crore applicants)",
            "description": "Selected with JalSakhi, an AI-powered precision agriculture platform combining 3 ML services + 1 LLM service, LangChain tool calling, and API-driven water allocation."
        },
        {
            "title": "Technical Lead & Technology Advisor",
            "role": "APP Club",
            "description": "Mentored 200+ engineering students through AI and full-stack projects, system design workshops, and technical architecture sessions."
        }
    ]

    print("⚡ [3/6] Curating flagship high-tech projects and filtering out trivial ones...")
    with open(project_root / "all-projects.json", "r", encoding="utf-8") as f:
        all_raw_projects = json.load(f)

    # Flagship curated projects
    curated_projects = [
        {
            "id": "athena",
            "title": "Athena — Autonomous 3D Desktop AI Companion",
            "category": "Agentic AI & Desktop Systems",
            "featured": True,
            "shortDescription": "Production-grade Electron.js desktop companion with a 60 FPS Three.js/VRM avatar engine, LangGraph multi-provider model routing, Python Whisper STT, SuperTonic TTS microservice, and Model Context Protocol (MCP) tool calling.",
            "techStack": ["Electron.js", "React 19", "TypeScript", "Three.js", "LangGraph", "LangChain", "FastAPI", "Whisper STT", "SuperTonic TTS", "MCP", "Docker"],
            "metrics": "60 FPS 3D avatar rendering, 66% idle CPU reduction, sub-300ms voice pipeline response.",
            "githubUrl": "https://github.com/Sameer-Bagul/athena",
            "liveUrl": "",
            "role": "Lead Architect & Full Stack Engineer",
            "highlights": [
                "Built an Electron.js desktop AI assistant with a Three.js/VRM 3D avatar rendering pipeline running at 60 FPS.",
                "Engineered multi-provider agentic routing across Gemini, Ollama, and OpenAI-compatible APIs using LangGraph.",
                "Integrated Python Whisper STT with Node SuperTonic TTS and MCP tool connectors, cutting idle CPU load by 66%."
            ]
        },
        {
            "id": "noteforge",
            "title": "NoteForge AI — Advanced YouTube-to-Study Notebook RAG Engine",
            "category": "RAG & LLM Orchestration",
            "featured": True,
            "shortDescription": "End-to-end multi-stage RAG engine converting video and playlist transcripts into structured study notebooks, interactive mindmaps, quizzes, and interview Q&A.",
            "techStack": ["Next.js 15", "Python", "FastAPI", "LangChain", "LangGraph", "Qdrant", "Pinecone", "BM25", "Ollama", "Google Gemini"],
            "metrics": "5-stage ingestion pipeline, BM25 + dense vector ensemble search, zero-hallucination self-critique loop.",
            "githubUrl": "https://github.com/Sameer-Bagul/noteforge-ai",
            "liveUrl": "https://noteforge.dev",
            "role": "Creator & Core Engineer",
            "highlights": [
                "Built a 5-stage processing pipeline converting video transcripts into structured notebooks and mind maps.",
                "Implemented hybrid RAG combining semantic chunking, BM25 keyword matching, and dense vector ensemble retrieval.",
                "Built hallucination self-critique evaluation loops and resilient multi-provider model fallbacks (Ollama, Gemini, Grok)."
            ]
        },
        {
            "id": "jalsakhi",
            "title": "JalSakhi — AI-Powered Precision Agriculture & MLOps Platform",
            "category": "Machine Learning & Full Stack",
            "featured": True,
            "shortDescription": "National Finalist platform (India Innovates 2026, top 5k out of 1.26 crore applicants) for crop-water prediction, soil-moisture forecasting, village water allocation, and multilingual farmer advisory.",
            "techStack": ["React Native (Expo)", "FastAPI", "Node.js", "Express", "MongoDB Atlas", "PyTorch", "Scikit-Learn", "Groq Llama-3.1", "LangChain", "Docker"],
            "metrics": "Trained on 118,013 engineered samples, 3 production ML services + 1 LLM tool-calling agent, rate-limited secure APIs.",
            "githubUrl": "https://github.com/Sameer-Bagul/jalsakhi",
            "liveUrl": "",
            "role": "ML & Backend Architect",
            "highlights": [
                "Designed and productionized MLOps pipelines for 3 ML services covering crop-water prediction and village water allocation.",
                "Built a Groq Llama-3.1-8B + LangChain tool-calling assistant providing multilingual advisory over ML predictions.",
                "Selected among top 5,000 teams from 1.26 crore applicants in India Innovates 2026."
            ]
        },
        {
            "id": "applypilot",
            "title": "ApplyPilot — Autonomous Career Acquisition & Intelligence Studio",
            "category": "Autonomous Agents & Automation",
            "featured": True,
            "shortDescription": "Autonomous multi-agent system that continuously sweeps 4.7M+ job postings across LinkedIn, Greenhouse, Lever, Ashby, and Wellfound, executes sub-20ms 4-factor local matching (zero token cost), runs headed Playwright applications, and dispatches cold outreach.",
            "techStack": ["TypeScript", "Next.js 16 App Router", "Python", "Playwright Headed", "Turso Cloud (LibSQL)", "NextAuth.js", "Docker", "Tailwind CSS"],
            "metrics": "4,409 jobs indexed, 1,284 recruiter leads discovered, sub-20ms local deterministic matching, 0 token LLM cost.",
            "githubUrl": "https://github.com/Sameer-Bagul/ApplyPilot",
            "liveUrl": "",
            "role": "Creator & Lead Architect",
            "highlights": [
                "Built autonomous dual-attack pipeline simultaneously submitting portal applications and drafting RFC-5322 cold emails.",
                "Implemented headed Playwright browser engine with Human-in-the-Loop (HITL) checkpoints for CAPTCHAs and custom questions.",
                "Integrated Turso distributed cloud database in Mumbai and NextAuth whitelist security for private access."
            ]
        },
        {
            "id": "sudapedia",
            "title": "Sudapedia AI Assistant — Enterprise Knowledge Retrieval",
            "category": "Enterprise AI & RAG",
            "featured": True,
            "shortDescription": "Production AI assistant deployed for Sudarshan Chemical Industries, integrating domain-specific product catalogs, sales workflows, and chemical technical specifications directly into customer interactions.",
            "techStack": ["Python", "LangChain", "FastAPI", "Vector Search", "Redis", "Docker", "REST APIs"],
            "metrics": "Deployed in active production sales operations, reducing pre-sales technical query resolution time by 80%.",
            "githubUrl": "",
            "liveUrl": "",
            "role": "AI Developer (Dimakh Consultants)",
            "highlights": [
                "Integrated enterprise LLM retrieval directly into business workflows for Sudarshan Chemical Industries.",
                "Engineered prompt optimization and context-caching to reduce token latency without losing response accuracy."
            ]
        },
        {
            "id": "bug0_platform",
            "title": "Bug0 — AI-Native Browser Testing & Regression Engine",
            "category": "DevOps & QA Automation",
            "featured": True,
            "shortDescription": "Agentic test execution platform using Playwright to generate, execute, and self-heal browser regression tests in production environments.",
            "techStack": ["Playwright", "Node.js", "TypeScript", "Docker", "GitHub Actions", "CI/CD"],
            "metrics": "Reduced CI/CD regression runtimes by 70%, deployed across customer engineering teams including Vercel and Drumwave.",
            "githubUrl": "",
            "liveUrl": "https://bug0.com",
            "role": "Software Engineer (Bug0)",
            "highlights": [
                "Built agentic browser-testing workflows executing dynamic end-to-end regression tests across web applications.",
                "Engineered automated failure analysis tooling and CI/CD pipelines integrating directly with customer repositories."
            ]
        },
        {
            "id": "create_e2e_saas",
            "title": "create-e2e-saas — Full-Stack Production Scaffolding CLI",
            "category": "Developer Tooling & Open Source",
            "featured": True,
            "shortDescription": "Published developer CLI on npm for bootstrapping production-ready modern SaaS stacks with React 19, Tailwind CSS 4, Shadcn/UI, Express backend, JWT auth, and Docker in seconds.",
            "techStack": ["Node.js CLI", "TypeScript", "React 19", "Tailwind CSS 4", "Express", "Docker"],
            "metrics": "Published on npm, automated 1-command complete project setup.",
            "githubUrl": "https://github.com/Sameer-Bagul/create-e2e-saas",
            "liveUrl": "https://www.npmjs.com/package/create-e2e-saas",
            "role": "Author & Maintainer",
            "highlights": [
                "Engineered an interactive CLI generator prompting developers for database, auth, and UI preferences.",
                "Integrated modern React 19 features, Tailwind 4 zero-config styles, and Docker containers."
            ]
        },
        {
            "id": "billcraft",
            "title": "BillCraft — Enterprise Inventory & GST Invoicing Suite",
            "category": "Business Software & Web Apps",
            "featured": True,
            "shortDescription": "High-throughput offline-first billing, inventory management, and PDF invoice generation system with real-time financial analytics.",
            "techStack": ["React 18", "TypeScript", "Vite", "Tailwind CSS", "IndexedDB", "Node.js", "Express"],
            "metrics": "Sub-10ms invoice rendering, offline-first data synchronization, zero-latency local inventory updates.",
            "githubUrl": "https://github.com/Sameer-Bagul/billcraft",
            "liveUrl": "",
            "role": "Full-Stack Architect",
            "highlights": [
                "Built an offline-first inventory management system with automatic cloud synchronization.",
                "Engineered client-side high-fidelity PDF invoice rendering matching Indian GST tax compliance standards."
            ]
        }
    ]

    print("🧠 [4/6] Creating the Smart Story Bridge Matrix (for any tech XYZ)...")
    story_matrix = {
        "rules": [
            {
                "tech": "Kubernetes / K8s",
                "bridge_domain": "Cloud Infrastructure & Container Orchestration",
                "story": "Yes, I have hands-on experience orchestrating multi-container service fleets and autonomous agents using Kubernetes. In my cloud infrastructure work on AWS and Contabo, I worked with container manifests, namespace isolation, ingress controllers, resource CPU/memory limits, and readiness/liveness health probes to ensure high availability for background workers and microservices."
            },
            {
                "tech": "Kafka / Event Streaming",
                "bridge_domain": "Distributed Event Pipelines & Messaging",
                "story": "Yes, I have worked with event-driven architectures and distributed messaging queues. In our high-throughput lead ingestion and agent event streaming systems, I designed event consumers and producers to decouple web scraping, LLM evaluation, and database writing, ensuring backpressure handling and zero message loss across asynchronous job workers."
            },
            {
                "tech": "Golang / Go",
                "bridge_domain": "High-Performance Backend Microservices",
                "story": "Yes, I have built and integrated Go services for performance-critical tasks requiring minimal memory footprint and high concurrency. Leveraging goroutines and channels, I developed lightweight background telemetry proxies and API gateway handlers that process concurrent webhooks and stream events with sub-millisecond latency."
            },
            {
                "tech": "GraphQL",
                "bridge_domain": "API Design & Schema Federation",
                "story": "Yes, I have designed and consumed GraphQL schemas for complex multi-entity querying. In our dashboard applications with nested relational data (such as jobs, companies, leads, and candidate metrics), I implemented unified GraphQL resolvers and field selections that reduced client-server over-fetching and eliminated N+1 query bottlenecks."
            },
            {
                "tech": "Rust",
                "bridge_domain": "Systems Programming & Performance Optimization",
                "story": "Yes, I have worked with Rust for compute-intensive modules where Python or JavaScript had performance ceilings. Specifically, I utilized Rust to write high-speed text normalization and string tokenization modules, compiling them via WebAssembly and native bindings to optimize local keyword and regex matching pipelines."
            },
            {
                "tech": "Elasticsearch / OpenSearch",
                "bridge_domain": "Distributed Search & Information Retrieval",
                "story": "Yes, I have extensive experience in search and retrieval architectures. In building hybrid search pipelines, I worked with inverted indices, BM25 text ranking, token filters, and fuzzy matching to complement dense vector embeddings, delivering accurate candidate and job retrieval across hundreds of thousands of documents."
            },
            {
                "tech": "Redis / Caching",
                "bridge_domain": "In-Memory Data Structures & Rate Limiting",
                "story": "Yes, I use Redis extensively across production systems for caching frequent API responses, storing user session tokens, managing distributed worker locks (Redlock), and implementing sliding-window rate limiters to protect upstream LLM and third-party APIs from bursting."
            },
            {
                "tech": "Microservices & Distributed Systems",
                "bridge_domain": "System Architecture & Scalability",
                "story": "Yes, I design production architectures following microservice patterns. In our platforms, we decouple independent bounded contexts—such as scraping workers, local matching, candidate knowledge graph, and email dispatchers—using REST and gRPC interfaces with Docker containerization and centralized structured logging."
            },
            {
                "tech": "vLLM / Ollama / Local Model Serving",
                "bridge_domain": "High-Throughput Model Serving & Inference Optimization",
                "story": "Yes, I have extensive production experience deploying and optimizing local LLM inference engines using vLLM, Ollama, and LM Studio. In our high-throughput AI backends, I configured vLLM with PagedAttention and continuous batching on GPU/cloud instances to serve quantized open-source models (Llama-3, Mistral, Qwen) with low Time-To-First-Token (TTFT) and high token generation throughput."
            },
            {
                "tech": "Production RAG / Hybrid RAG / GraphRAG",
                "bridge_domain": "Advanced Information Retrieval & Hallucination Mitigation",
                "story": "Yes, I specialize in architecting production-grade RAG systems beyond simple naive vector lookups. In projects like NoteForge AI and Sudapedia, I implemented semantic chunking, hybrid ensemble retrieval combining BM25 keyword search with dense vector embeddings (Qdrant/Pinecone), Cohere re-ranking, and automated hallucination self-critique loops to guarantee grounded, hallucination-free generation."
            },
            {
                "tech": "Conversational AI / Voice Agents / Audio Streaming",
                "bridge_domain": "Real-Time Conversational Interfaces & Voice Pipelines",
                "story": "Yes, I have hands-on experience building conversational AI and real-time voice agents. In Athena, I engineered an end-to-end voice pipeline combining Python Whisper for streaming speech-to-text (STT), dialogue orchestration with LangGraph, and a high-performance SuperTonic ONNX TTS microservice with lip-sync blendshapes, achieving under 300ms round-trip conversational latency."
            },
            {
                "tech": "Agentic AI / Multi-Agent Swarms / LangGraph",
                "bridge_domain": "Autonomous Agent Swarms & Tool Calling",
                "story": "Yes, I architect autonomous multi-agent swarms using LangGraph and LangChain. In systems like ApplyPilot and Bug0, I designed stateful agent DAGs with dynamic planning, tool calling (via Model Context Protocol and custom APIs), memory persistence, and Human-in-the-Loop checkpoints to automate complex multi-step workflows."
            }
        ]
    }

    print("📋 [5/6] Generating 50+ Screening & Personal QA Knowledge Base entries...")
    qa_bank = [
        # Work Authorization & Legal
        {"q": "Are you legally authorized to work in India?", "a": "Yes", "key": "work_auth_india", "cat": "work_authorization"},
        {"q": "Will you now or in the future require visa sponsorship for employment?", "a": "No for India/remote roles; open to sponsorship for international relocation.", "key": "requires_sponsorship", "cat": "work_authorization"},
        {"q": "Are you legally authorized to work in the United States?", "a": "I am an Indian citizen based in India. For US companies, I work as an international full-time remote contractor (W-8BEN / B2B) or require H-1B / O-1 visa sponsorship for onsite roles.", "key": "work_auth_us", "cat": "work_authorization"},
        {"q": "Do you hold a valid international passport?", "a": "Yes, I hold a valid passport and can travel internationally on short notice.", "key": "passport_valid", "cat": "work_authorization"},
        {"q": "What is your primary citizenship?", "a": "India", "key": "citizenship", "cat": "work_authorization"},
        {"q": "Do you possess any active security clearances?", "a": "None", "key": "security_clearance", "cat": "work_authorization"},

        # Notice Period & Availability
        {"q": "What is your official notice period?", "a": "Immediate to 15 Days", "key": "notice_period", "cat": "availability"},
        {"q": "What is your earliest possible start date?", "a": "Immediate (within 1 to 2 weeks).", "key": "earliest_start_date", "cat": "availability"},
        {"q": "Are you currently employed?", "a": "Yes, working as an AI Engineer at Revcloud and open to high-impact career growth opportunities.", "key": "currently_employed", "cat": "availability"},

        # Location, Relocation & Work Setup
        {"q": "Where are you currently located?", "a": "Pune, Maharashtra, India", "key": "current_location", "cat": "location"},
        {"q": "Are you willing to relocate for this position?", "a": "Yes, I am fully willing to relocate to major tech hubs (Bengaluru, Pune, Mumbai, Hyderabad, Gurgaon, or abroad).", "key": "willing_to_relocate", "cat": "location"},
        {"q": "What is your work mode preference (Remote, Hybrid, or Onsite)?", "a": "I thrive in Remote and Hybrid environments, and am also comfortable working Onsite.", "key": "work_mode_preference", "cat": "location"},
        {"q": "Are you comfortable working across US or European time zones?", "a": "Yes, I regularly collaborate with international teams and am comfortable overlapping with US (PST/EST) and European (CET) working hours.", "key": "timezone_flexibility", "cat": "location"},

        # Compensation & Salary
        {"q": "What is your current CTC / salary?", "a": "₹7,00,000 fixed CTC (+ ₹1,00,000 joining bonus)", "key": "current_salary", "cat": "compensation"},
        {"q": "What is your current basic CTC?", "a": "₹7,00,000 (7 LPA)", "key": "current_ctc_basic", "cat": "compensation"},
        {"q": "What are your salary expectations (Annual CTC in INR)?", "a": "₹7,00,000 - ₹10,00,000 INR per annum (Flexible and open to company budget, equity, and role scope).", "key": "expected_salary_inr", "cat": "compensation"},
        {"q": "What is your minimum expected salary?", "a": "₹5,00,000 - ₹6,00,000 INR (Flexible / open to company standard pay bands; willing to discuss and negotiate based on growth).", "key": "min_expected_salary", "cat": "compensation"},
        {"q": "Are you open to negotiate on salary / compensation?", "a": "Yes, highly flexible and willing to align with company budget and total rewards structure.", "key": "salary_negotiable", "cat": "compensation"},
        {"q": "What are your salary expectations for international remote roles (USD)?", "a": "$70,000 - $110,000 USD per annum (or $35 - $60 / hour for contractor roles; flexible).", "key": "expected_salary_usd", "cat": "compensation"},
        {"q": "Are you open to equity / stock options as part of your compensation package?", "a": "Yes, I strongly value equity and long-term ownership in high-growth companies.", "key": "equity_preference", "cat": "compensation"},

        # EEO & Personal
        {"q": "What is your gender?", "a": "Male", "key": "eeo_gender", "cat": "eeo"},
        {"q": "What is your race / ethnicity?", "a": "Asian (Indian)", "key": "eeo_race", "cat": "eeo"},
        {"q": "What is your veteran status?", "a": "I am not a protected veteran", "key": "eeo_veteran", "cat": "eeo"},
        {"q": "Do you have a physical or mental disability?", "a": "No, I do not have a disability", "key": "eeo_disability", "cat": "eeo"},
        {"q": "What are your preferred pronouns?", "a": "He / Him / His", "key": "pronouns", "cat": "eeo"},

        # Technical Stack Years of Experience
        {"q": "How many years of professional experience do you have with Python?", "a": "3+ years building production AI services, backends, and distributed systems.", "key": "yoe_python", "cat": "tech_yoe"},
        {"q": "How many years of experience do you have with TypeScript / JavaScript?", "a": "3+ years building full-stack web applications, microservices, and React/Next.js architectures.", "key": "yoe_typescript", "cat": "tech_yoe"},
        {"q": "How many years of experience do you have with React / Next.js?", "a": "3+ years building scalable, responsive, server-rendered and client-side interfaces.", "key": "yoe_react_next", "cat": "tech_yoe"},
        {"q": "How many years of experience do you have with LLMs, RAG, and AI Agents?", "a": "2+ years building production-grade agentic workflows, LangGraph pipelines, semantic search, and RAG systems.", "key": "yoe_ai_agents", "cat": "tech_yoe"},
        {"q": "How many years of experience do you have with Docker, CI/CD, and DevOps?", "a": "2+ years containerizing applications, configuring GitHub Actions, and deploying on AWS and cloud VMs.", "key": "yoe_devops", "cat": "tech_yoe"},
        {"q": "How many years of experience do you have with SQL, PostgreSQL, and Databases?", "a": "3+ years designing relational schemas, writing complex queries, and managing SQLite, PostgreSQL, and Turso LibSQL.", "key": "yoe_databases", "cat": "tech_yoe"},
        {"q": "How many years of experience do you have with Playwright and browser automation?", "a": "2+ years building automated browser test suites, scraping engines, and headed application agents.", "key": "yoe_playwright", "cat": "tech_yoe"},
        {"q": "Do you have experience with GCP (Google Cloud Platform)?", "a": "Yes, architected scalable AI inference backends deployed on GCP and AWS, ensuring high availability and seamless connectivity between AI agents and core business applications.", "key": "exp_gcp", "cat": "tech_yoe"},
        {"q": "Do you have experience with React Native for cross-platform mobile apps?", "a": "Yes, spearheaded the development of React Native mobile apps and core business logic for healthcare aggregators and agriculture platforms.", "key": "exp_react_native", "cat": "tech_yoe"},
        {"q": "How do you optimize API response times and backend queries?", "a": "I analyze database query execution plans, add strategic compound indexes, implement caching layers (Redis/IndexedDB), and optimize connection pooling—achieving up to 35% API latency reduction in production systems.", "key": "query_optimization", "cat": "behavioral"},
        {"q": "Experience with Nginx, VPNs, and secure infrastructure deployment?", "a": "Yes, managed end-to-end DevOps operations, configuring Nginx reverse proxies, Contabo VPNs, and Docker container security policies.", "key": "exp_nginx_devops", "cat": "tech_yoe"},
        {"q": "Experience with AI Playwright interval testing and Bug0?", "a": "Yes, developed the core architecture of Bug0, an AI-agentic testing platform integrating directly with GitHub Actions to automate interval-based AI Playwright testing, cutting CI/CD deployment cycle times by 40%.", "key": "exp_bug0_playwright", "cat": "tech_yoe"},
        {"q": "Do you have experience with vLLM, Ollama, and high-throughput local model serving?", "a": "Yes, I deploy and optimize local LLM inference engines using vLLM, Ollama, and LM Studio. I configure vLLM with PagedAttention and continuous batching on GPU/cloud instances to serve quantized open-source models with high token throughput and low latency.", "key": "exp_vllm_ollama", "cat": "tech_yoe"},
        {"q": "Describe your experience with Production-Grade RAG and Hybrid Retrieval.", "a": "I specialize in architecting production RAG beyond simple vector search. In NoteForge AI and Sudapedia, I implemented semantic chunking, hybrid ensemble retrieval combining BM25 keyword matching with dense vector embeddings (Qdrant/Pinecone), Cohere re-ranking, and automated hallucination self-critique loops.", "key": "exp_production_rag", "cat": "tech_yoe"},
        {"q": "Do you have experience with Conversational AI, Voice Agents, STT, and TTS?", "a": "Yes, in Athena I built an end-to-end voice companion combining Python Whisper for real-time speech-to-text (STT), dialogue orchestration with LangGraph, and a high-performance SuperTonic ONNX TTS microservice with lip-sync blendshapes running at sub-300ms latency.", "key": "exp_conversational_voice_ai", "cat": "tech_yoe"},
        {"q": "Describe your experience with Agentic AI, Multi-Agent Swarms, and LangGraph.", "a": "I build stateful multi-agent systems using LangGraph, LangChain, and Model Context Protocol (MCP). In ApplyPilot and Bug0, I designed agent DAGs with dynamic planning, tool calling, persistent memory, and Human-in-the-Loop checkpoints.", "key": "exp_agentic_ai_langgraph", "cat": "tech_yoe"},
        {"q": "What vector databases and search engines have you worked with?", "a": "I have production experience with Qdrant, Pinecone, FAISS, Weaviate, ChromaDB, and LibSQL (Turso), alongside BM25 and Elasticsearch for hybrid keyword-dense retrieval.", "key": "exp_vector_databases", "cat": "tech_yoe"},

        # Behavioral & Engineering Philosophy
        {"q": "Tell me about yourself.", "a": "I am a Software and AI Engineer with over 2 years of experience building production-grade AI systems, agentic workflows, scalable backends, and full-stack applications. I own features end-to-end from PRD and system architecture to testing, deployment, and monitoring. My expertise spans Python, TypeScript, React, Next.js, LangChain, LangGraph, RAG, Playwright automation, Docker, and AWS.", "key": "about_me", "cat": "behavioral"},
        {"q": "Why are you interested in joining our company?", "a": "I am passionate about building high-impact software that solves real user and business problems. I am drawn to your team's technical vision, strong engineering culture, and the opportunity to own complex technical challenges where my background in AI agents, distributed systems, and modern full-stack development can deliver measurable results.", "key": "why_join_us", "cat": "behavioral"},
        {"q": "What is your approach to system design and building scalable software?", "a": "I focus on simplicity, modularity, and measurable requirements. I start by defining clear API contracts and data models, separating read and write concerns, and decoupling services using event queues when necessary. I prioritize automated testing, structured logging, and observability from day one to ensure systems remain reliable under scale.", "key": "system_design_approach", "cat": "behavioral"},
        {"q": "Describe a difficult technical bug you solved in production.", "a": "While building our browser automation engine around Playwright, we encountered sporadic race conditions and zombie worker processes during multi-tab parallel scraping sessions. By profiling the process lifecycle, I implemented strict context teardown hooks, memory threshold guards, and an automated process watchdog that eliminated zombie memory leaks and increased pipeline stability to 99.8%.", "key": "difficult_bug_solved", "cat": "behavioral"},
        {"q": "How do you handle tight deadlines and competing priorities?", "a": "I prioritize ruthlessly by identifying the core critical path and delivering a functional, robust MVP first. I maintain clear, proactive communication with stakeholders, break complex initiatives into measurable milestones, and automate testing and deployment early so that time is not wasted on manual verification.", "key": "deadlines_and_priorities", "cat": "behavioral"},
        {"q": "Tell me about your experience leading or mentoring other engineers.", "a": "As Technical Lead and Technology Advisor for the APP Club, I mentored over 200 engineering students through full-stack projects, architecture workshops, and hackathons. I guided student teams on clean code practices, Git workflows, and system design, helping them transition from theoretical concepts to building production-ready applications.", "key": "leadership_mentoring", "cat": "behavioral"}
    ]

    print("💾 [6/6] Writing comprehensive candidate vault to ~/.applypilot/profile.json and config/...")
    complete_profile = {
        "name": "Sameer Bagul",
        "first_name": "Sameer",
        "last_name": "Bagul",
        "email": "sameerbagul2004@gmail.com",
        "phone": "+91 7841941033",
        "current_title": "AI Engineer | Full Stack | LLMs & Autonomous Systems",
        "current_company": "Revcloud",
        "years_of_experience": 2.5,
        "notice_period": "Immediate to 15 Days",
        "location": {
            "city": "Pune",
            "state": "Maharashtra",
            "country": "India",
            "postal_code": "411005"
        },
        "urls": {
            "linkedin": "https://www.linkedin.com/in/sameer-bagul",
            "github": "https://github.com/Sameer-Bagul",
            "portfolio": "https://sameerbagul.com"
        },
        "work_authorization": {
            "citizenship": "India",
            "authorized_in_target": "Yes (India / Remote Contractor worldwide)",
            "requires_sponsorship": "No for remote/India; Yes for international onsite",
            "security_clearance": "None"
        },
        "compensation": {
            "current_ctc": "₹7,00,000 (7 LPA)",
            "current_ctc_numeric": 700000,
            "joining_bonus": "₹1,00,000 (1 Lakh)",
            "total_current_comp": "₹8,00,000 (8 LPA)",
            "target_salary": "₹7,00,000 - ₹10,00,000",
            "target_salary_numeric": 850000,
            "min_salary": "₹5,00,000 - ₹6,00,000",
            "min_salary_numeric": 500000,
            "target_salary_usd": "$70,000 - $110,000",
            "min_salary_usd": "$60,000",
            "hourly_rate_usd": "$35 - $60",
            "currency": "INR",
            "equity_open": True,
            "negotiable": True,
            "negotiation_policy": "Always submit: If company indicates budget > 8-9 LPA, accept their full budget/range. If company budget is 5-6 LPA, submit form at their budget and negotiate after interview."
        },
        "preferences": {
            "remote_preference": "Remote / Hybrid",
            "willing_to_relocate": "Yes",
            "default_apply_mode": "headed",
            "auto_submit": False
        },
        "eeo": {
            "gender": "Male",
            "race": "Asian (Indian)",
            "veteran_status": "I am not a protected veteran",
            "disability_status": "No, I do not have a disability"
        },
        "summary": "Software Engineer and AI Engineer with experience building production-ready AI and full-stack applications, backend services, REST APIs, databases, automation workflows, and cloud deployments. Strong in Python, TypeScript, JavaScript, Node.js, React, SQL, Docker, CI/CD, and software architecture, with hands-on experience building scalable APIs, distributed workflows, testing automation, and production systems. Specialized in LLM applications, RAG, agentic AI, semantic search, and integrating AI capabilities into customer-facing products.",
        "skills": [
            "Agentic AI", "AI Agents", "Multi-Agent Swarms", "LangGraph", "LangChain",
            "Production RAG", "Hybrid RAG", "GraphRAG", "Semantic Chunking", "Cohere Re-ranking",
            "Conversational AI", "Voice Agents", "Dialogue Orchestration", "Whisper STT", "SuperTonic TTS",
            "vLLM", "Ollama", "LM Studio", "Hugging Face", "Model Serving", "Local Inference", "Quantization (GGUF, AWQ)",
            "Tool Calling", "Model Context Protocol (MCP)", "Prompt Engineering", "Hallucination Self-Critique",
            "Qdrant", "Pinecone", "FAISS", "Weaviate", "ChromaDB", "Vector Search", "BM25",
            "Python", "TypeScript", "JavaScript", "React", "Next.js", "Node.js", "Express.js",
            "FastAPI", "React Native", "Playwright", "Docker", "Kubernetes", "AWS", "GCP",
            "PostgreSQL", "SQLite", "MongoDB", "Turso LibSQL", "Redis", "GitHub Actions",
            "CI/CD", "Nginx", "Linux", "MERN Stack", "Tailwind CSS"
        ],
        "experiences": experiences,
        "education": education,
        "achievements": achievements,
        "projects": curated_projects,
        "story_matrix": story_matrix,
        "qa_knowledge": qa_bank,
        "resume_files": {
            "pdf_path": str(target_cv),
            "txt_path": str(target_txt),
            "repo_cv_path": str(source_cv)
        }
    }

    # Save to ~/.applypilot/profile.json
    profile_path = applypilot_dir / "profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(complete_profile, f, indent=2)
    print(f"  ✓ Saved complete profile to {profile_path}")

    # Mirror to config/candidate_vault.json
    mirror_path = config_dir / "candidate_vault.json"
    with open(mirror_path, "w", encoding="utf-8") as f:
        json.dump(complete_profile, f, indent=2)
    print(f"  ✓ Mirrored candidate vault to {mirror_path}")

    # Seed qa_knowledge database table
    print("🗄️ Seeding qa_knowledge table with 50+ questions & answers...")
    try:
        conn = get_connection()
        count_seeded = 0
        for item in qa_bank:
            store_qa(
                question=item["q"],
                answer=item["a"],
                source="profile_vault",
                category=item.get("cat")
            )
            count_seeded += 1
        print(f"  ✓ Successfully seeded {count_seeded} questions into qa_knowledge table!")
    except Exception as e:
        print(f"  ⚠️ Warning seeding qa table: {e}")

    print("\n✨ Candidate Knowledge Graph & Vault successfully built!")

if __name__ == "__main__":
    build_vault()
