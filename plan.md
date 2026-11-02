the playwright server might be able to apply to specific jobs , but maybe not able to get the perfect job openings so there are 2 tasks to do 
1) Get the perfect Jobs from internet , get the perfect posts from reddit , Linkedin, X , thread, and main thing is companies career site ; we have to check this daily so we can get new jobs ; and we need diff posts so we can get the HR Mails , many times the posts are more Like to mail the HR and thats more securing spot for any cold mail and for many potehr comapneis the official career sites are important so we should get the career site where we can fill the form 
2) in the second part we will be sending mails to the mails we got from job findings and also we will fill the form to the companies job portals 

this is my goal , we can do brainstorm on this and make the plan to get this done 

============================

You have nailed the real-world dynamic of modern job hunting: **Playwright is an execution engine, not a discovery engine.** If you only feed Playwright generic aggregator links, you end up competing with 2,000 other applicants—whereas catching a fresh founder/HR post on LinkedIn, X, Reddit, or Threads ("DM or email `hr@company.com`") or hitting a company's direct career portal within 24 hours of posting is what actually lands interviews.

To build this properly, we should split your architecture into **two specialized engines** connected by a **Smart Router & Shared Knowledge Pool**:

```text
=====================================================================================
                  PART 1: DAILY OMNI-CHANNEL DISCOVERY & ROUTING ENGINE
=====================================================================================
  [ Social "Hiring Post" Radar ]                 [ Direct Career Portal Radar ]
  - LinkedIn Posts, X, Reddit, Threads           - Greenhouse, Lever, Ashby, Workday
  - Search Dorks + Exa / Brave / Reddit RSS      - JobsPipe MCP / Jobo MCP / Career Watchlist
                 |                                              |
                 +----------------------+-----------------------+
                                        | (Every 6–24 Hours)
                                        v
                   [ Zero-Token Regex & Entity Classifier ]
                   Extracts: Emails, ATS Links, Company Domain
                                        |
         +------------------------------+------------------------------+
         |                              |                              |
         v (Post has HR/Founder Email)  v (Post has only Company Name) v (Has Direct ATS URL)
  [ Route: EMAIL_ONLY ]          [ Career Site Resolver ]       [ Route: PORTAL_APPLY ]
                                 Finds official /careers page
                                 & extracts direct ATS form URL
                                 (Plus checks if BOTH exist -> [ Route: DUAL_ATTACK ])

=====================================================================================
                  PART 2: DUAL-TRACK EXECUTION & SELF-LEARNING ENGINE
=====================================================================================
         |                                                             |
         v (Track A: HR / Founder Cold Mailer)                         v (Track B: Portal Form Applier)
  [ Tailored Gmail Dispatcher ]                                 [ Playwright MCP + 5-Tier Cache ]
  - Cites exact post ("Saw your post on X...")                  - Fills form using Tier 0-2 (0 tokens)
  - Pulls verified answers from Q&A DB                          - Unknown question? -> Emails YOU (HITL)
  - Attaches tailored resume PDF                                - Learns your reply -> Updates Q&A DB

```

### Part 1: How to Get the "Perfect" Jobs Daily (Without Getting Accounts Banned)

If you use Playwright to log into your personal LinkedIn, X, or Threads accounts every day to scrape posts, those platforms will quickly flag and ban your accounts. Instead, Part 1 uses **API feeds, RSS, and Search Engine Dorks** (via [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools) or a lightweight Python discovery scheduler) to harvest posts safely and at near-zero cost:

| Channel | What We Want | How to Scrape It Daily (Zero Ban Risk & Low/Zero Cost) |
| --- | --- | --- |
| **Reddit** | Subreddit hiring threads (`r/forhire`, `r/RemoteJS`, `r/golang`, `r/india`, `r/developersIndia`, "Who is hiring" megathreads) | Append `.json` or `.rss` to any Reddit search URL (e.g., `https://www.reddit.com/r/forhire/new.json?limit=50`)—100% free, structured JSON, no Playwright needed. |
| **LinkedIn Posts** (Not Job Board) | HR & Engineering Managers posting *"We're hiring an AI/Backend Engineer, send resume to `name@company.com`"* | Query Google/Brave/Exa search APIs with time-filtered dorks (`site:linkedin.com/posts ("hiring" OR "looking for") ("send your resume" OR "mail" OR "@")`) restricted to the **past 24 hours** (`tbs=qdr:d`). |
| **X (Twitter) & Threads** | Founders & VPs posting *"Hiring a founding engineer, drop your email or mail `founder@startup.io`"* | Run daily time-bounded search dorks (`site:x.com` and `site:threads.net` with `"we are hiring" OR "hiring a" ("email" OR "apply" OR "DM")`) via [Hermes Agent](https://github.com/nousresearch/hermes-agent) search backends. |
| **Direct Company Career Sites** | Fresh openings on company portals before they hit aggregators | Combine [JobsPipe MCP](https://jobspipe.dev/mcp-server) / [Jobo MCP](https://github.com/JoboAI) with direct JSON polling of [Greenhouse](https://www.greenhouse.com/api), [Lever](https://github.com/lever/postings-api), and Ashby endpoints (`boards.greenhouse.io/<company>`, `jobs.lever.co/<company>`), plus a **Custom Career Page Watcher** for your dream companies. |

#### The Secret Weapon in Part 1: The "Career Site Resolver"

Many social posts on LinkedIn or X mention that a company is hiring *without* including an email or a direct link—or they link to a shortened URL. Whenever the scraper finds a post with no HR email:

1. It extracts the company name and runs a fast search (`"<Company Name>" official site careers OR jobs`).
2. It locates the company's official `/careers` page, inspects the outbound "Apply" links, and resolves the exact underlying ATS portal URL (Greenhouse, Lever, Workday, or custom form) so **Part 2** can fill it out automatically.

---

### Part 2: Executing Both Tracks (HR Emails + Portal Forms)

Once Part 1 classifies a lead and scores it against your resume, it assigns one of three execution modes: **`EMAIL_ONLY`**, **`PORTAL_ONLY`**, or **`DUAL_ATTACK` (Both)**.

#### Track A: Automated HR & Founder Email Engine

When a post says *"Send your resume to `priya@company.com` with subject line 'AI Engineer - [Your Name]'"*, generic cold email templates fail. Your agent will:

* **Follow Post-Specific Instructions:** Extract any special instructions from the post (e.g., required subject line format, portfolio links, or "mention your favorite project in paragraph 1").
* **Cite Exact Social Proof:** Open the email naturally: *"Hi Priya, I saw your LinkedIn post from earlier today about the AI Engineer opening at [Company]..."*
* **Pull from Your Self-Learning Q&A Pool:** If the post asks for specific details (*"Include your notice period, current CTC, and GitHub"*), the email drafter queries your local SQLite `qa_knowledge_base`.
* **Trigger Email HITL if Info Is Missing:** Just like the form filler! If the HR post asks *"Include your experience with Kubernetes in production"* and that isn't in your Q&A database yet, the agent **emails you first**, waits for your reply, saves the fact to your Q&A pool, and then sends/drafts the HR email with your tailored resume PDF attached.

#### Track B: Career Portal Form Filler ([Playwright MCP](https://github.com/microsoft/playwright-mcp) + Self-Learning Cache)

When the lead points to a company career site or ATS form:

* **Fills the Portal Form Automatically:** Uses our **5-Tier Zero-Token Engine** (replaying cached CSS/ARIA selectors for known ATS platforms like Greenhouse, Lever, and Workday so you don't burn LLM tokens on standard fields).
* **Asks You via Email on Edge Cases:** If the company's career form has a custom question outside your data scope, it parks the application, emails you the question, parses your reply, adds the answer to the permanent knowledge pool, and finishes submitting the form.
* **Runs the "Dual Attack" When Both Exist:** If a company has *both* an official career portal form *and* an HR email from a social post, the agent submits the official portal form **first** (so you are in their ATS database) and then sends the HR email 5 minutes later saying: *"I've already submitted my formal application on your careers page, and wanted to reach out directly as mentioned in your post..."*

---

### How to Prevent Spam & Embarrassing Mistakes (Critical Guardrails)

1. **Strict Deduplication Across Channels:** If a recruiter posts the same job on LinkedIn, X, and their career site, a `(company_domain, normalized_role_title)` hash ensures you don't email the same HR person twice or double-apply.
2. **Confidence Mode (`AUTO_SEND` vs. `DRAFT_AND_DIGEST`):** For the first week, you can set HR emails to **Draft Mode** (or Daily Digest Approval) so the agent prepares the exact email + attached tailored PDF in your Gmail Drafts and emails you a 1-click approval summary. Once you trust the formatting, flip high-confidence matches (`score >= 85`) to `AUTO_SEND`.
3. **Never Guess Emails:** The agent only emails addresses explicitly extracted from the post or official careers page (`source_url` + verbatim snippet stored in the database).

Would you like me to update your **[Master Architecture & Agent Spec Google Doc](https://docs.google.com/document/d/1HZdwj4do3zIbx8Kl0dEWFi0csnYbWR_fZxRVJB-mJEw/edit?usp=drivesdk&ouid=115296601398722550451)** right now to restructure the system around this exact **Part 1 (Omni-Channel Social + Career Site Discovery)** and **Part 2 (HR Emailer + Portal Form Applier)** architecture?

========================================


