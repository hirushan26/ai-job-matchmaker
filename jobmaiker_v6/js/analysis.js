// JobMaker Analysis & Skill Gap Module

let currentJobAnalyses = [];

function escapeText(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderEducation(education) {
  const container = document.getElementById("education-scroll");
  if (!container) return;

  const deg = (education && education.degree) ? education.degree.trim() : "";
  const inst = (education && education.institute) ? education.institute.trim() : "";

  const hasDegree = deg && deg.toLowerCase() !== "not specified";
  const hasInstitute = inst && !inst.toLowerCase().includes("upload your cv");

  if (hasDegree || hasInstitute) {
    const degreeText = hasDegree ? deg : "Degree";
    const instituteHtml = hasInstitute ? `<div class="university-name">${escapeText(inst)}</div>` : "";
    container.innerHTML = `
      <div id="degree-uni">
        <div class="degree">${escapeText(degreeText)}</div>
        ${instituteHtml}
      </div>
    `;
  } else {
    // Render clean text directly on the card without a pill container
    container.innerHTML = `
      <div class="education-empty-state">
        <div class="edu-empty-title">Not Specified</div>
        <div class="edu-empty-sub">Upload your CV to add education</div>
      </div>
    `;
  }
}

function renderSkillsCloud(skills) {
  const container = document.getElementById("skill-cloud");
  if (!container) return;
  container.innerHTML = "";

  if (!skills || skills.length === 0) {
    container.innerHTML = "<p style='color: #94a3b8; font-size: 13px; padding: 12px 0;'>No skills extracted yet. Upload your CV to build your skill cloud.</p>";
    return;
  }

  skills.forEach(skill => {
    const tag = document.createElement("div");
    tag.className = "skill-tag";
    tag.textContent = skill;
    container.appendChild(tag);
  });
}

function renderAnalysisRoles(roles) {
  const container = document.getElementById("analysis-job-roles");
  if (!container) return;
  container.innerHTML = "";

  if (!roles || roles.length === 0) {
    container.innerHTML = "<p style='color: #64748b; padding: 20px;'>No job role analyses available. Upload your CV in Profile to analyze matches.</p>";
    return;
  }

  currentJobAnalyses = roles;

  roles.forEach((job, index) => {
    const card = document.createElement("div");
    card.className = "job-description clickable-job";
    card.dataset.index = index;

    // Match badge color styling based on score
    let badgeColor = "#10b981"; // green
    if (job.match_percentage < 60) {
      badgeColor = "#ef4444"; // red
    } else if (job.match_percentage < 80) {
      badgeColor = "#d97706"; // orange
    }

    card.innerHTML = `
      <div class="job-header-row">
        <div class="job-role-main">
          <p class="job-title">${job.job_title}</p>
          <div class="job-match-badge-analysis" style="color: ${badgeColor};">${job.match_percentage}% Match</div>
        </div>
        <div class="job-title-details">
          <p class="job-title-para">${job.compatibility_summary || "Compatibility calculated by Gemini AI"}</p>
        </div>
        <div class="analysis-job-search">
          <img src="icons/Arrow-Down.png" alt="Arrow" class="gap-arrow-icon">
          <div class="action-text">Gap Analysis</div>
        </div>
      </div>
      <div class="job-expanded-content"></div>
    `;

    // Click handler to expand accordion with full skill gap & score breakdown
    card.addEventListener("click", function(e) {
      // Don't trigger if clicked on child buttons
      if (e.target.closest(".inline-apply-btn")) return;

      const isExpanded = this.classList.contains("expanded");
      const expandedContent = this.querySelector(".job-expanded-content");
      const actionText = this.querySelector(".action-text");
      const arrowIcon = this.querySelector(".gap-arrow-icon");

      // If already expanded, collapse this card
      if (isExpanded) {
        this.classList.remove("expanded");
        if (actionText) actionText.textContent = "Gap Analysis";
        if (arrowIcon) arrowIcon.src = "icons/Arrow-Down.png";
        return;
      }

      // Close other accordions
      document.querySelectorAll(".clickable-job").forEach(c => {
        c.classList.remove("expanded");
        const act = c.querySelector(".action-text");
        const arr = c.querySelector(".gap-arrow-icon");
        if (act) act.textContent = "Gap Analysis";
        if (arr) arr.src = "icons/Arrow-Down.png";
      });

      // Expand this card
      this.classList.add("expanded");
      if (actionText) actionText.textContent = "Close";
      if (arrowIcon) arrowIcon.src = "icons/Arrow-Up.png";

        // Generate adaptive score breakdown HTML
        const sb = job.score_breakdown || {};
        const maxW = sb.max_weights || {};
        const isInternRubric = (maxW.core_skills === 60) || (sb.core_skills > 50) || (maxW.tools_practices === 5);

        const coreMax = maxW.core_skills || (isInternRubric ? 60 : 50);
        const expMax = maxW.experience_or_projects || maxW.experience || (isInternRubric ? 20 : 25);
        const eduMax = maxW.education || 15;
        const toolsMax = maxW.tools_practices || (isInternRubric ? 5 : 10);

        const expVal = sb.experience_or_projects !== undefined ? sb.experience_or_projects : (sb.experience ?? 0);
        const expLabel = isInternRubric ? "Projects & Portfolio" : "Experience";
        const rubricBadge = isInternRubric 
          ? `<span style="background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-left: auto;">🎓 Intern / Entry-Level Adapted Rubric</span>`
          : `<span style="background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-left: auto;">💼 Professional Rubric</span>`;

        const breakdownHtml = (sb.core_skills !== undefined) ? `
          <div class="score-breakdown-box" style="margin-bottom: 14px; padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">
            <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>Match Score Calculation Breakdown (100% Total):</span>
              ${rubricBadge}
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap; font-size: 12px; margin-bottom: 8px;">
              <span style="background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 12px; font-weight: 500;">Core Skills: <strong>${sb.core_skills ?? 0}/${coreMax}</strong></span>
              <span style="background: #f0fdf4; color: #15803d; padding: 3px 8px; border-radius: 12px; font-weight: 500;">${expLabel}: <strong>${expVal}/${expMax}</strong></span>
              <span style="background: #fef3c7; color: #b45309; padding: 3px 8px; border-radius: 12px; font-weight: 500;">Education: <strong>${sb.education ?? 0}/${eduMax}</strong></span>
              <span style="background: #ede9fe; color: #6d28d9; padding: 3px 8px; border-radius: 12px; font-weight: 500;">Tools & Practices: <strong>${sb.tools_practices ?? 0}/${toolsMax}</strong></span>
            </div>
            ${job.score_explanation ? `<p style="font-size: 12.5px; color: #475569; margin: 0; line-height: 1.4;"><strong>Why this score?</strong> ${job.score_explanation}</p>` : ""}
          </div>
        ` : "";

        // Generate matching skills tags
        const matchedSkillsHtml = (job.matched_skills && job.matched_skills.length > 0)
          ? job.matched_skills.map(s => `<span class="inline-skill-tag valid">${s} ✓</span>`).join("")
          : "<span style='font-size:13px; color:#94a3b8;'>No exact skill matches identified.</span>";

        // Generate missing skills tags with priority badges
        let missingSkillsHtml = "";
        if (!job.missing_skills || job.missing_skills.length === 0) {
          missingSkillsHtml = "<p style='font-size:13px; color:#10b981; font-weight:500;'>You meet all core requirements for this role!</p>";
        } else {
          missingSkillsHtml = job.missing_skills.map(skill => {
            const priority = (skill.priority || "medium").toLowerCase();
            const badgeClass = priority === "high" ? "high" : (priority === "medium" ? "medium" : "low");
            const priorityLabel = priority.charAt(0).toUpperCase() + priority.slice(1);
            return `
              <div class="gap-item">
                <span class="gap-skill-name">${skill.name}</span>
                <span class="gap-status-badge ${badgeClass}">${priorityLabel} Priority</span>
              </div>
            `;
          }).join("");
        }

        expandedContent.innerHTML = `
          <div class="inline-gap-wrapper">
            ${job.role_description ? `<p class="inline-job-desc">${job.role_description}</p>` : ""}
            
            ${breakdownHtml}

            <h3 class="inline-section-title">Your matching skills:</h3>
            <div class="inline-skills-cloud">${matchedSkillsHtml}</div>

            <h3 class="inline-section-title">Skill Gap Analysis (Missing Skills):</h3>
            <div class="gap-items-container">${missingSkillsHtml}</div>
            
            <button class="inline-apply-btn" onclick="navigateToFindJobs('${job.job_title}')">Find Jobs</button>
          </div>
        `;
    });

    container.appendChild(card);
  });
}

function navigateToFindJobs(jobTitle) {
  if (window.JobMakerJobs && typeof window.JobMakerJobs.filterJobsByRole === "function") {
    window.JobMakerJobs.filterJobsByRole(jobTitle);
  } else {
    const jobrolesTab = document.getElementById("jobroles-tab");
    if (jobrolesTab) jobrolesTab.click();
  }
}


async function initAnalysis() {
  // Wire "Update your resume" button
  const updateResumeBtn = document.getElementById("analysis-update-resume");
  if (updateResumeBtn) {
    updateResumeBtn.addEventListener("click", () => {
      const profileTab = document.getElementById("profile-tab");
      if (profileTab) profileTab.click();
      setTimeout(() => {
        const dropZone = document.getElementById("cv-drop-zone");
        if (dropZone) {
          dropZone.scrollIntoView({ behavior: "smooth", block: "center" });
          dropZone.style.border = "2px dashed #0284c7";
          setTimeout(() => dropZone.style.border = "", 1500);
        }
      }, 100);
    });
  }

  // Load cached analysis data from backend
  const data = await API.getAnalysis();
  if (data) {
    latestAnalysisData = data;

    // Experience Years & Focus
    const expEl = document.getElementById("experience-years");
    if (expEl) {
      if (data.experience_years !== undefined && data.experience_years > 0) {
        const isIntern = (data.career_stage === "intern_fresher") || (data.experience_years <= 2.5);
        expEl.textContent = isIntern ? "Student / Intern" : `${data.experience_years} Years`;
      } else {
        expEl.textContent = "--";
      }
    }

    const expFocusEl = document.getElementById("experience-focus");
    if (expFocusEl) {
      if (data.experience_summary && data.experience_summary.trim()) {
        let focusText = data.experience_summary
          .replace(/^over\s+\d+(\.\d+)?\s+years\s+(of\s+)?(experience\s+)?(in\s+)?/i, "")
          .replace(/^hands-on\s+experience\s+(in|with)\s+/i, "")
          .replace(/^experience\s+(in|with)\s+/i, "")
          .trim();
        if (focusText) {
          focusText = focusText.charAt(0).toUpperCase() + focusText.slice(1);
        }
        expFocusEl.textContent = focusText || data.experience_summary;
        expFocusEl.title = "Click to view full experience details";
      } else {
        expFocusEl.textContent = "No experience data yet. Upload your CV to calculate experience.";
        expFocusEl.title = "";
      }
    }

    // Wire experience focus box click to open modal
    const expBox = document.getElementById("experience-focus-box");
    if (expBox) {
      expBox.addEventListener("click", () => {
        showExperienceDetailModal(latestAnalysisData || data);
      });
    }

    // Education
    renderEducation(data.education);

    // Skills Cloud
    renderSkillsCloud(data.skills || []);

    // Job Roles & Gap Analyses
    renderAnalysisRoles(data.job_analyses || []);
  }

  // Modal close handlers (Top 'X' button & backdrop click)
  const closeBtn = document.getElementById("close-exp-modal-btn");
  const modalEl = document.getElementById("experience-detail-modal");

  if (closeBtn) closeBtn.addEventListener("click", hideExperienceDetailModal);
  if (modalEl) {
    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) hideExperienceDetailModal();
    });
  }

  // Close on Escape key press
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modalEl && modalEl.style.display === "flex") {
      hideExperienceDetailModal();
    }
  });
}

let latestAnalysisData = null;

function showExperienceDetailModal(data) {
  const modal = document.getElementById("experience-detail-modal");
  if (!modal || !data) return;

  // Full experience & practical projects summary only
  const summaryEl = document.getElementById("exp-modal-full-summary");
  if (summaryEl) {
    if (data.experience_summary && data.experience_summary.trim()) {
      summaryEl.textContent = data.experience_summary.trim();
    } else {
      summaryEl.innerHTML = "<span style='color: #94a3b8; font-style: italic;'>No detailed work experience listed. Evaluated on demonstrated coursework, academic projects, and technical skills.</span>";
    }
  }

  // Display modal
  modal.style.display = "flex";
  document.body.style.overflow = "hidden";
}

function hideExperienceDetailModal() {
  const modal = document.getElementById("experience-detail-modal");
  if (modal) {
    modal.style.display = "none";
    document.body.style.overflow = "";
  }
}
