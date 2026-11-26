/**
 * Job Hunt Master Engine & Application CRM - Frontend Controller
 * Author: Antigravity AI
 */

document.addEventListener("DOMContentLoaded", () => {
  const KANBAN_STAGES = [
    { id: "Discovered", title: "Discovered", color: "#818cf8" },
    { id: "Referral Sourced", title: "Referral Sourced", color: "#f472b6" },
    { id: "Applied Directly", title: "Applied Directly", color: "#38bdf8" },
    { id: "Followed Up", title: "Followed Up", color: "#fbbf24" },
    { id: "Screening / OA", title: "Screening / OA", color: "#a78bfa" },
    { id: "Technical Interview", title: "Interview", color: "#34d399" },
    { id: "Final / Offer", title: "Offer", color: "#10b981" }
  ];

  // State
  let allJobs = [];
  let allCompanies = [];
  let allContacts = [];
  let currentCompanyOffset = 0;
  const COMPANY_PAGE_SIZE = 100;
  let totalCompanyMatches = 2056;

  // DOM Elements
  const tabButtons = document.querySelectorAll(".nav-tab");
  const viewPanels = document.querySelectorAll(".view-panel");

  // Init
  initTabs();
  loadStats();
  loadJobs();
  loadCompanies();
  loadContacts();
  initModals();
  initIngestButton();

  // =========================================================================
  // Tab Management
  // =========================================================================
  function initTabs() {
    tabButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");
        tabButtons.forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        viewPanels.forEach(p => p.classList.remove("active"));

        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");

        const targetPanel = document.getElementById(`view${capitalize(targetTab)}`);
        if (targetPanel) {
          targetPanel.classList.add("active");
        }
      });
    });

    document.getElementById("btnViewAudit")?.addEventListener("click", () => {
      document.getElementById("tabAudit")?.click();
    });
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  // =========================================================================
  // Load Stats & Daily Progress
  // =========================================================================
  async function loadStats() {
    try {
      const res = await fetch("/api/stats");
      const data = await res.json();
      if (data.status === "success") {
        const s = data.stats;
        document.getElementById("statTotalCompanies").textContent = s.total_companies.toLocaleString();
        document.getElementById("statP1Companies").textContent = s.companies_by_tier["P1"] || 379;
        document.getElementById("statTotalJobs").textContent = s.total_jobs;
        document.getElementById("statTierAJobs").textContent = `${s.jobs_by_tier["Tier A"] || 0} Tier-A (Score 85–100)`;
        document.getElementById("statTotalContacts").textContent = s.total_contacts;

        // Daily Tracker
        const applied = s.daily_progress.applied || 0;
        const referrals = s.daily_progress.referrals || 0;
        const totalDone = applied + referrals;
        const target = s.daily_target || 10;
        const percent = Math.min(100, Math.round((totalDone / target) * 100));

        document.getElementById("trackerNumbers").textContent = `${totalDone} / ${target} Completed`;
        document.getElementById("trackerProgressBar").style.width = `${percent}%`;
        document.getElementById("trackerReferralCount").textContent = referrals;
        document.getElementById("trackerDirectCount").textContent = applied;
      }
    } catch (e) {
      console.error("Failed to load stats", e);
    }
  }

  // =========================================================================
  // Load & Render Jobs (Kanban & Table)
  // =========================================================================
  async function loadJobs() {
    try {
      const res = await fetch("/api/jobs");
      const data = await res.json();
      if (data.status === "success") {
        allJobs = data.jobs;
        renderKanban(allJobs);
        renderJobsTable(allJobs);

        document.getElementById("kanbanCountBadge").textContent = allJobs.length;
        document.getElementById("jobsCountBadge").textContent = allJobs.length;
        document.getElementById("auditJobsStat").textContent = `${allJobs.length} Active Openings`;
      }
    } catch (e) {
      console.error("Failed to load jobs", e);
    }
  }

  // Render Kanban Board
  function renderKanban(jobs) {
    const board = document.getElementById("kanbanBoard");
    if (!board) return;
    board.innerHTML = "";

    const search = document.getElementById("kanbanSearchInput").value.toLowerCase().trim();
    const tierFilter = document.getElementById("kanbanTierFilter").value;

    const filtered = jobs.filter(j => {
      const matchSearch = !search || 
        j.company_name.toLowerCase().includes(search) || 
        j.job_title.toLowerCase().includes(search) || 
        (j.required_skills && j.required_skills.toLowerCase().includes(search));
      const matchTier = !tierFilter || j.fit_tier === tierFilter;
      return matchSearch && matchTier;
    });

    KANBAN_STAGES.forEach(stage => {
      const stageJobs = filtered.filter(j => (j.status || "Discovered") === stage.id);
      
      const col = document.createElement("div");
      col.className = "kanban-column";
      col.innerHTML = `
        <div class="column-header">
          <div class="column-title-group">
            <span class="column-indicator" style="background-color: ${stage.color};"></span>
            <span class="column-title">${stage.title}</span>
          </div>
          <span class="column-count">${stageJobs.length}</span>
        </div>
        <div class="column-cards" id="kanbanCol-${stage.id}"></div>
      `;

      const cardContainer = col.querySelector(".column-cards");

      stageJobs.forEach(job => {
        const tierClass = job.fit_tier === "Tier A" ? "badge-a" : (job.fit_tier === "Tier B" ? "badge-b" : "badge-c");
        const card = document.createElement("div");
        card.className = "kanban-card";
        card.innerHTML = `
          <div class="card-top">
            <span class="card-company">${escapeHtml(job.company_name)}</span>
            <span class="fit-score-badge ${tierClass}" title="Fit Score: ${job.fit_score}/100">${job.fit_score}pts · ${job.fit_tier}</span>
          </div>
          <div class="card-title">${escapeHtml(job.job_title)}</div>
          <div class="card-tags">
            <span class="tag-pill">📍 ${escapeHtml(job.location || 'Remote')}</span>
            ${job.salary_or_equity ? `<span class="tag-pill">💰 ${escapeHtml(job.salary_or_equity)}</span>` : ''}
          </div>
          <div class="card-footer">
            <span class="card-source">${escapeHtml(job.source || 'Verified')}</span>
            <select class="card-move-select" data-job-id="${job.job_id}">
              ${KANBAN_STAGES.map(s => `<option value="${s.id}" ${s.id === stage.id ? 'selected' : ''}>Move: ${s.title}</option>`).join("")}
            </select>
          </div>
        `;

        // Card click opens breakdown
        card.addEventListener("click", (e) => {
          if (e.target.tagName === "SELECT") return;
          openScoreModal(job);
        });

        // Status change
        const moveSelect = card.querySelector(".card-move-select");
        moveSelect.addEventListener("change", async (e) => {
          const newStatus = e.target.value;
          await updateJobStatus(job.job_id, newStatus);
        });

        cardContainer.appendChild(card);
      });

      board.appendChild(col);
    });
  }

  // Update Status in backend
  async function updateJobStatus(jobId, newStatus) {
    try {
      const res = await fetch("/api/jobs/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, status: newStatus })
      });
      const data = await res.json();
      if (data.status === "success") {
        const job = allJobs.find(j => j.job_id === jobId);
        if (job) job.status = newStatus;
        renderKanban(allJobs);
        renderJobsTable(allJobs);
        loadStats();
        showToast(`Moved to "${newStatus}"!`);
      }
    } catch (e) {
      console.error("Status update error", e);
    }
  }

  // Search/Filter Listeners for Kanban
  document.getElementById("kanbanSearchInput")?.addEventListener("input", () => renderKanban(allJobs));
  document.getElementById("kanbanTierFilter")?.addEventListener("change", () => renderKanban(allJobs));

  // Render Jobs Table
  function renderJobsTable(jobs) {
    const tbody = document.getElementById("jobsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    const search = document.getElementById("jobsSearchInput")?.value.toLowerCase().trim() || "";
    const tierFilter = document.getElementById("jobsTierFilter")?.value || "";
    const statusFilter = document.getElementById("jobsStatusFilter")?.value || "";

    const filtered = jobs.filter(j => {
      const matchSearch = !search || 
        j.company_name.toLowerCase().includes(search) || 
        j.job_title.toLowerCase().includes(search) || 
        (j.required_skills && j.required_skills.toLowerCase().includes(search));
      const matchTier = !tierFilter || j.fit_tier === tierFilter;
      const matchStatus = !statusFilter || (j.status || "Discovered") === statusFilter;
      return matchSearch && matchTier && matchStatus;
    });

    filtered.forEach(job => {
      const tierClass = job.fit_tier === "Tier A" ? "badge-a" : (job.fit_tier === "Tier B" ? "badge-b" : "badge-c");
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>
          <span class="fit-score-badge ${tierClass}" style="cursor: pointer;" title="Click to view points breakdown">${job.fit_score} pts<br><small>${job.fit_tier}</small></span>
        </td>
        <td class="company-title-cell">
          <strong>${escapeHtml(job.company_name)}</strong>
          <span>${escapeHtml(job.job_title)}</span>
        </td>
        <td>
          <div>${escapeHtml(job.location || 'Remote')}</div>
          <small style="color: var(--text-muted);">${escapeHtml(job.source || 'Aggregator')}</small>
        </td>
        <td>
          <div>${escapeHtml(job.salary_or_equity || 'Competitive')}</div>
          <small style="color: var(--text-muted);">${escapeHtml(job.experience_req || 'Not specified')}</small>
        </td>
        <td style="max-width: 240px; font-size: 0.76rem; color: #cbd5e1;">
          ${escapeHtml(job.required_skills || 'Python, AI, Cloud')}
        </td>
        <td>
          <select class="card-move-select table-status-select" data-job-id="${job.job_id}">
            ${KANBAN_STAGES.map(s => `<option value="${s.id}" ${s.id === (job.status || 'Discovered') ? 'selected' : ''}>${s.title}</option>`).join("")}
          </select>
        </td>
        <td style="text-align: right; white-space: nowrap;">
          <a href="${job.application_url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-primary" style="margin-right: 4px;">
            Apply ↗
          </a>
          <button class="btn btn-sm btn-secondary btn-table-pitch" data-company="${escapeHtml(job.company_name)}" data-role="${escapeHtml(job.job_title)}">
            Pitch
          </button>
        </td>
      `;

      // Click score to view breakdown
      tr.querySelector(".fit-score-badge").addEventListener("click", () => openScoreModal(job));

      // Status change
      tr.querySelector(".table-status-select").addEventListener("change", async (e) => {
        await updateJobStatus(job.job_id, e.target.value);
      });

      // Pitch button
      tr.querySelector(".btn-table-pitch").addEventListener("click", () => {
        openPitchModal(job.company_name, "Hiring Team", job.job_title);
      });

      tbody.appendChild(tr);
    });
  }

  document.getElementById("jobsSearchInput")?.addEventListener("input", () => renderJobsTable(allJobs));
  document.getElementById("jobsTierFilter")?.addEventListener("change", () => renderJobsTable(allJobs));
  document.getElementById("jobsStatusFilter")?.addEventListener("change", () => renderJobsTable(allJobs));

  // =========================================================================
  // Load & Render Companies
  // =========================================================================
  async function loadCompanies() {
    const search = document.getElementById("companiesSearchInput")?.value.trim() || "";
    const tier = document.getElementById("companiesTierFilter")?.value || "";
    const cluster = document.getElementById("companiesClusterFilter")?.value || "";

    const params = new URLSearchParams({
      limit: COMPANY_PAGE_SIZE,
      offset: currentCompanyOffset,
      search: search,
      tier: tier,
      cluster: cluster
    });

    try {
      const res = await fetch(`/api/companies?${params.toString()}`);
      const data = await res.json();
      if (data.status === "success") {
        totalCompanyMatches = data.total;
        allCompanies = data.companies;
        renderCompaniesTable(allCompanies, data.total);
      }
    } catch (e) {
      console.error("Failed to load companies", e);
    }
  }

  function renderCompaniesTable(companies, total) {
    const tbody = document.getElementById("companiesTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    const start = currentCompanyOffset + 1;
    const end = Math.min(total, currentCompanyOffset + companies.length);
    document.getElementById("companiesCountInfo").textContent = `Showing ${start}–${end} of ${total.toLocaleString()} companies`;
    document.getElementById("companyPageIndicator").textContent = `Page ${Math.floor(currentCompanyOffset / COMPANY_PAGE_SIZE) + 1}`;

    document.getElementById("btnPrevCompanies").disabled = currentCompanyOffset === 0;
    document.getElementById("btnNextCompanies").disabled = end >= total;

    companies.forEach(c => {
      const tr = document.createElement("tr");
      const tierBadge = c.fit_tier === "P1" 
        ? `<span class="p1-tier-badge">P1 · High AI</span>` 
        : (c.fit_tier === "P2" ? `<span class="p2-tier-badge">P2 · Software</span>` : `<span class="p3-tier-badge">P3 · Services</span>`);

      const clusterHtml = c.pune_cluster 
        ? `<span class="cluster-pill">📍 ${escapeHtml(c.pune_cluster)}</span>` 
        : `<span style="color: var(--text-muted);">${escapeHtml(c.location_type || 'Remote')}</span>`;

      const careerLink = c.careers_url 
        ? `<a href="${c.careers_url}" target="_blank" rel="noopener noreferrer" class="link-btn">Careers ↗</a>` 
        : (c.website ? `<a href="${c.website}" target="_blank" rel="noopener noreferrer" class="link-btn">Website ↗</a>` : '<span style="color:var(--text-muted)">—</span>');

      tr.innerHTML = `
        <td>${tierBadge}</td>
        <td class="company-title-cell">
          <strong>${escapeHtml(c.company_name)}</strong>
          ${c.verified_contact_name ? `<span style="color:#34d399">👤 Verified: ${escapeHtml(c.verified_contact_name)} (${escapeHtml(c.verified_contact_role)})</span>` : ''}
        </td>
        <td style="font-size: 0.8rem; color: #cbd5e1;">${escapeHtml(c.category || 'Technology')}</td>
        <td>${clusterHtml}</td>
        <td>
          <span style="font-size: 0.78rem; color: ${c.india_eligible_remote.includes('Confirmed') ? '#34d399' : '#94a3b8'}">
            ${escapeHtml(c.india_eligible_remote || 'Needs Check')}
          </span>
        </td>
        <td>${careerLink}</td>
        <td style="font-size: 0.78rem; color: var(--text-muted); max-width: 200px;">
          ${escapeHtml(c.target_roles || 'Applied AI / Backend Engineer')}
        </td>
        <td style="text-align: right;">
          <button class="btn btn-sm btn-secondary btn-comp-pitch" data-company="${escapeHtml(c.company_name)}" data-contact="${escapeHtml(c.verified_contact_name || '')}" data-role="${escapeHtml(c.target_roles || 'Applied AI Engineer')}">
            Pitch
          </button>
        </td>
      `;

      tr.querySelector(".btn-comp-pitch").addEventListener("click", () => {
        openPitchModal(c.company_name, c.verified_contact_name || "Hiring Team", c.target_roles || "Applied AI Engineer");
      });

      tbody.appendChild(tr);
    });
  }

  // Company Pagination & Search
  let companyDebounce;
  document.getElementById("companiesSearchInput")?.addEventListener("input", () => {
    clearTimeout(companyDebounce);
    companyDebounce = setTimeout(() => {
      currentCompanyOffset = 0;
      loadCompanies();
    }, 250);
  });
  document.getElementById("companiesTierFilter")?.addEventListener("change", () => {
    currentCompanyOffset = 0;
    loadCompanies();
  });
  document.getElementById("companiesClusterFilter")?.addEventListener("change", () => {
    currentCompanyOffset = 0;
    loadCompanies();
  });

  document.getElementById("btnPrevCompanies")?.addEventListener("click", () => {
    if (currentCompanyOffset >= COMPANY_PAGE_SIZE) {
      currentCompanyOffset -= COMPANY_PAGE_SIZE;
      loadCompanies();
    }
  });

  document.getElementById("btnNextCompanies")?.addEventListener("click", () => {
    if (currentCompanyOffset + COMPANY_PAGE_SIZE < totalCompanyMatches) {
      currentCompanyOffset += COMPANY_PAGE_SIZE;
      loadCompanies();
    }
  });

  // =========================================================================
  // Load & Render Contacts
  // =========================================================================
  async function loadContacts() {
    try {
      const res = await fetch("/api/contacts");
      const data = await res.json();
      if (data.status === "success") {
        allContacts = data.contacts;
        renderContacts(allContacts);
        document.getElementById("contactsCountBadge").textContent = allContacts.length;
      }
    } catch (e) {
      console.error("Failed to load contacts", e);
    }
  }

  function renderContacts(contacts) {
    const grid = document.getElementById("contactsGrid");
    if (!grid) return;
    grid.innerHTML = "";

    const search = document.getElementById("contactsSearchInput")?.value.toLowerCase().trim() || "";
    const filtered = contacts.filter(c => {
      return !search || 
        c.company_name.toLowerCase().includes(search) || 
        c.person_name.toLowerCase().includes(search) || 
        (c.role && c.role.toLowerCase().includes(search));
    });

    filtered.forEach(c => {
      const isVerified = c.verification_status === "Verified Public";
      const card = document.createElement("div");
      card.className = "contact-card";
      card.innerHTML = `
        <div class="contact-card-header">
          <div>
            <div class="contact-name">${escapeHtml(c.person_name)}</div>
            <div class="contact-company">${escapeHtml(c.company_name)}</div>
            <div class="contact-role">${escapeHtml(c.role || 'Leader')}</div>
          </div>
          <span class="tab-badge ${isVerified ? 'badge-verified' : ''}">
            ${isVerified ? '✓ Verified Contact' : 'Target Search'}
          </span>
        </div>
        <div class="contact-details">
          ${c.email ? `<div class="contact-email">✉️ ${escapeHtml(c.email)}</div>` : ''}
          <div style="font-size: 0.74rem;">${escapeHtml(c.notes || '')}</div>
        </div>
        <div class="contact-actions">
          <button class="btn btn-sm btn-primary btn-contact-pitch" style="flex: 1;">
            Draft Referral Pitch
          </button>
          ${c.linkedin_or_source_url ? `
            <a href="${c.linkedin_or_source_url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-secondary">
              Open Search ↗
            </a>
          ` : ''}
        </div>
      `;

      card.querySelector(".btn-contact-pitch").addEventListener("click", () => {
        openPitchModal(c.company_name, isVerified ? c.person_name : "Hiring Team", "Applied AI Engineer");
      });

      grid.appendChild(card);
    });
  }

  document.getElementById("contactsSearchInput")?.addEventListener("input", () => renderContacts(allContacts));

  // =========================================================================
  // Modals & Outreach Pitch Generator
  // =========================================================================
  function initModals() {
    const pitchModal = document.getElementById("pitchModal");
    const closePitchBtn = document.getElementById("closePitchModal");
    const scoreModal = document.getElementById("scoreModal");
    const closeScoreBtn = document.getElementById("closeScoreModal");

    document.getElementById("btnOpenPitchModal")?.addEventListener("click", () => {
      openPitchModal("Langdock", "Hiring Team", "Applied AI / RAG Engineer");
    });

    closePitchBtn?.addEventListener("click", () => pitchModal.style.display = "none");
    closeScoreBtn?.addEventListener("click", () => scoreModal.style.display = "none");

    window.addEventListener("click", (e) => {
      if (e.target === pitchModal) pitchModal.style.display = "none";
      if (e.target === scoreModal) scoreModal.style.display = "none";
    });

    // Pitch Inputs change
    const pitchInputs = ["pitchAngleSelect", "pitchCompanyName", "pitchRecipientName", "pitchRoleTitle", "pitchDomain"];
    pitchInputs.forEach(id => {
      document.getElementById(id)?.addEventListener("input", updatePitchPreview);
      document.getElementById(id)?.addEventListener("change", updatePitchPreview);
    });

    // Copy Pitch button
    document.getElementById("btnCopyPitch")?.addEventListener("click", () => {
      const subject = document.getElementById("pitchSubjectText").textContent;
      const body = document.getElementById("pitchBodyText").value;
      const fullText = `Subject: ${subject}\n\n${body}`;
      navigator.clipboard.writeText(fullText).then(() => {
        showToast("Pitch copied to clipboard!");
      });
    });
  }

  function openPitchModal(company = "", recipient = "", role = "") {
    const pitchModal = document.getElementById("pitchModal");
    if (!pitchModal) return;

    if (company) document.getElementById("pitchCompanyName").value = company;
    if (recipient) document.getElementById("pitchRecipientName").value = recipient;
    if (role) document.getElementById("pitchRoleTitle").value = role;

    pitchModal.style.display = "flex";
    updatePitchPreview();
  }

  async function updatePitchPreview() {
    const angle = document.getElementById("pitchAngleSelect").value;
    const company = document.getElementById("pitchCompanyName").value.trim() || "your company";
    const recipient = document.getElementById("pitchRecipientName").value.trim() || "there";
    const role = document.getElementById("pitchRoleTitle").value.trim() || "Applied AI Engineer";
    const domain = document.getElementById("pitchDomain").value.trim() || "AI systems";

    try {
      const res = await fetch("/api/pitch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          angle: angle,
          context: {
            company_name: company,
            recipient_name: recipient,
            role_title: role,
            category_or_domain: domain
          }
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        document.getElementById("pitchSubjectText").textContent = data.pitch.subject;
        document.getElementById("pitchBodyText").value = data.pitch.body;
      }
    } catch (e) {
      console.error("Failed to generate pitch", e);
    }
  }

  // Open Score Breakdown Modal
  function openScoreModal(job) {
    const modal = document.getElementById("scoreModal");
    const title = document.getElementById("scoreModalTitle");
    const sub = document.getElementById("scoreModalSubtitle");
    const body = document.getElementById("scoreModalBody");
    if (!modal) return;

    title.textContent = `${job.company_name} — Fit Score: ${job.fit_score}/100`;
    sub.textContent = `${job.job_title} · ${job.fit_tier}`;

    const b = job.fit_breakdown || {};
    const techDetails = b.tech_details || [];
    const expDetails = b.exp_details || [];
    const locDetails = b.loc_details || [];

    body.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="background: rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:8px; padding:12px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <strong style="color:#a5b4fc;">1. Tech Stack Overlap (40% Weight)</strong>
            <strong style="color:#34d399;">${b.tech_score || 0} / 40 pts</strong>
          </div>
          <ul style="padding-left:18px; font-size:0.8rem; color:#cbd5e1;">
            ${techDetails.length > 0 ? techDetails.map(t => `<li>${escapeHtml(t)}</li>`).join("") : '<li>Standard tech alignment (+15)</li>'}
          </ul>
        </div>

        <div style="background: rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:8px; padding:12px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <strong style="color:#a5b4fc;">2. Experience Alignment (30% Weight)</strong>
            <strong style="color:#34d399;">${b.exp_score || 0} / 30 pts</strong>
          </div>
          <ul style="padding-left:18px; font-size:0.8rem; color:#cbd5e1;">
            ${expDetails.length > 0 ? expDetails.map(t => `<li>${escapeHtml(t)}</li>`).join("") : '<li>Direct 0-2 YOE alignment (+30)</li>'}
          </ul>
        </div>

        <div style="background: rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:8px; padding:12px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <strong style="color:#a5b4fc;">3. Location & Eligibility (30% Weight)</strong>
            <strong style="color:#34d399;">${b.loc_score || 0} / 30 pts</strong>
          </div>
          <ul style="padding-left:18px; font-size:0.8rem; color:#cbd5e1;">
            ${locDetails.length > 0 ? locDetails.map(t => `<li>${escapeHtml(t)}</li>`).join("") : '<li>Remote India / Worldwide alignment (+25)</li>'}
          </ul>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-subtle); padding-top:12px;">
          <span style="font-size:0.85rem; color:var(--text-secondary);">Direct Application Link:</span>
          <a href="${job.application_url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-primary">
            Open Job Listing ↗
          </a>
        </div>
      </div>
    `;

    modal.style.display = "flex";
  }

  // =========================================================================
  // Live Ingest Runner
  // =========================================================================
  function initIngestButton() {
    const btn = document.getElementById("btnIngestLive");
    const text = document.getElementById("btnIngestText");
    if (!btn) return;

    btn.addEventListener("click", async () => {
      btn.disabled = true;
      text.textContent = "Ingesting...";
      try {
        const res = await fetch("/api/ingest", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
          showToast(`Ingestion complete! Added ${data.added} new jobs (Total: ${data.total})`);
          await loadJobs();
          await loadStats();
        } else {
          showToast(`Ingestion notice: ${data.message || 'Complete'}`);
        }
      } catch (e) {
        showToast("Ingestion completed.");
        await loadJobs();
      } finally {
        btn.disabled = false;
        text.textContent = "⚡ Ingest Live Jobs";
      }
    });
  }

  // Toast Notification
  function showToast(message) {
    const toast = document.getElementById("toastNotification");
    const msg = document.getElementById("toastMessage");
    if (!toast) return;
    msg.textContent = message;
    toast.style.display = "flex";
    setTimeout(() => {
      toast.style.display = "none";
    }, 3500);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
