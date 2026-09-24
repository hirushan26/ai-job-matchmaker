// JobMaker Jobs & Bookmarks Controller Module

(function (window) {
  "use strict";

  let loadedJobs = [];
  let userBookmarks = [];
  let userMatchedRoles = [];

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Check if a job is in userBookmarks (matching title and company)
  function findBookmark(job) {
    if (!job) return null;
    return userBookmarks.find(b => {
      const sameRole = (b.title || b.job_role || "").trim().toLowerCase() === (job.title || "").trim().toLowerCase();
      const sameCompany = (b.company || b.company_name || "").trim().toLowerCase() === (job.company || "").trim().toLowerCase();
      return sameRole && sameCompany;
    });
  }

  // Populate dynamic Job Roles dropdowns for both Find Jobs & Bookmarks
  function populateJobRoleDropdowns(roles) {
    if (!Array.isArray(roles) || roles.length === 0) return;
    userMatchedRoles = roles;

    const findJobsRoleSelect = document.getElementById("jobrole-filter");
    const bmRoleSelect = document.getElementById("bm-jobrole-filter");

    const buildOptionsHtml = (currentVal = "all") => {
      let html = `<option value="all">All Matched Roles</option>`;
      roles.forEach(role => {
        const isSelected = currentVal === role ? "selected" : "";
        html += `<option value="${escapeHtml(role)}" ${isSelected}>${escapeHtml(role)}</option>`;
      });
      return html;
    };

    if (findJobsRoleSelect) {
      const curVal = findJobsRoleSelect.value || "all";
      findJobsRoleSelect.innerHTML = buildOptionsHtml(curVal);
    }

    if (bmRoleSelect) {
      const curVal = bmRoleSelect.value || "all";
      bmRoleSelect.innerHTML = buildOptionsHtml(curVal);
    }
  }

  // Render a single job card for Find Jobs
  function renderJobCard(job) {
    const bm = findBookmark(job);
    const isSaved = !!bm;
    const saveClass = isSaved ? "job-btn-save bookmarked" : "job-btn-save";
    const saveText = isSaved ? "Saved" : "Save";
    const visitUrl = job.url && job.url !== "#" ? job.url : `https://www.google.com/search?q=${encodeURIComponent(job.company + ' ' + job.title + ' jobs')}`;

    return `
      <div class="job-card" data-id="${escapeHtml(job.id)}" data-role="${escapeHtml(job.title)}" data-company="${escapeHtml(job.company)}">
        <div class="job-card-left">
          <h3 class="job-card-title">${escapeHtml(job.title)}</h3>
          <div class="job-card-company">${escapeHtml(job.company)}</div>
          <div class="job-card-location">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span>${escapeHtml(job.location || "Colombo, Sri Lanka")}</span>
          </div>
          <div class="job-card-salary">${escapeHtml(job.salary || "Salary negotiable")}</div>
        </div>
        <div class="job-card-right">
          <div class="job-match-badge">${job.matchScore || 85}% Match</div>
          <div class="job-card-actions">
            <a href="${escapeHtml(visitUrl)}" target="_blank" rel="noopener noreferrer" class="job-btn-visit">Visit</a>
            <button class="${saveClass}" onclick="window.JobMakerJobs.toggleSaveJob('${escapeHtml(job.id)}', this)">
              <span>${saveText}</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // Render a single bookmark card
  function renderBookmarkCard(bm) {
    const visitUrl = bm.url && bm.url !== "#" ? bm.url : `https://www.google.com/search?q=${encodeURIComponent(bm.company + ' ' + bm.title + ' jobs')}`;

    return `
      <div class="job-card" id="bm-card-${bm.id || bm.bm_id}" data-id="${bm.id || bm.bm_id}" data-role="${escapeHtml(bm.title)}" data-company="${escapeHtml(bm.company)}">
        <div class="job-card-left">
          <h3 class="job-card-title">${escapeHtml(bm.title)}</h3>
          <div class="job-card-company">${escapeHtml(bm.company)}</div>
          <div class="job-card-location">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span>${escapeHtml(bm.location || "Colombo, Sri Lanka")}</span>
          </div>
          <div class="job-card-salary">${escapeHtml(bm.salary || "Salary negotiable")}</div>
        </div>
        <div class="job-card-right">
          <div class="job-match-badge">${bm.matchScore || 90}% Match</div>
          <div class="job-card-actions">
            <a href="${escapeHtml(visitUrl)}" target="_blank" rel="noopener noreferrer" class="job-btn-visit">Visit</a>
            <button class="job-btn-save bookmarked" onclick="window.JobMakerJobs.removeBookmark(${bm.id || bm.bm_id}, this)">
              <span>Saved</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // Render Find Jobs list with current filters
  async function applyFindJobsFilters() {
    const container = document.getElementById("job-roles-list");
    if (!container) return;

    //Safely reads the current value of each dropdown. If a dropdown hasn't rendered yet, it won't crash.
    const roleVal = document.getElementById("jobrole-filter")?.value || "all";
    const locVal = document.getElementById("location-filter")?.value || "all";
    const typeVal = document.getElementById("jobtype-filter")?.value || "all";
    const expVal = document.getElementById("experience-filter")?.value || "all";
    const sortVal = document.getElementById("sort-filter")?.value || "match";

    //Loading animation
    container.innerHTML = `
      <div style="text-align: center; padding: 40px; color: #64748b;">
        <div style="display: inline-block; width: 28px; height: 28px; border: 3px solid #0284c7; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 12px;"></div>
        <p style="font-size: 15px; font-weight: 500;">Searching matching live jobs...</p>
      </div>
    `;

    try {
      const res = await API.getJobs({
        role: roleVal,
        location: locVal,
        job_type: typeVal,
        experience: expVal,
        sort: sortVal
      });

      loadedJobs = res.jobs || [];
      if (res.user_roles && res.user_roles.length > 0 && (!userMatchedRoles || userMatchedRoles.length === 0)) {
        populateJobRoleDropdowns(res.user_roles);
      } else if (!res.user_roles || res.user_roles.length === 0) {
        userMatchedRoles = [];
      }

      if (loadedJobs.length === 0) {
        if (!userMatchedRoles || userMatchedRoles.length === 0 || res.source === "empty_profile") {  //User has not uploaded a CV yet
          container.innerHTML = `
            <div style="text-align:center; padding: 48px 24px; color: #64748b;">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 12px;">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
              </svg>
              <p style="font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 6px;">No jobs available yet</p>
              <p style="font-size: 14px;">Upload your CV in the Profile tab to analyze your skills and discover matching job opportunities.</p>
            </div>
          `;
        } else {  //User has a CV, but the specific filter combination yielded 0 results
          container.innerHTML = `
            <div style="text-align:center; padding: 48px 24px; color: #64748b;">
              <p style="font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 6px;">No jobs found matching your filters</p>
              <p style="font-size: 14px;">Try selecting "All locations", "All types", or a different job role.</p>
            </div>
          `;
        }
        return;
      }

      container.innerHTML = loadedJobs.map(renderJobCard).join(""); //calls renderJobCard on every job object in the array, returning an array of HTML strings.
    } catch (err) { //If the backend server is down, the database fails, or there is a network dropout, it prevents the app from freezing
      console.error("Error loading jobs:", err);
      container.innerHTML = `
        <div style="text-align: center; padding: 40px; color: #e11d48;">
          <p style="font-size: 15px; font-weight: 600;">Failed to load job postings</p>
          <p style="font-size: 13px; color: #64748b;">Please verify your backend connection.</p>
        </div>
      `;
    }
  }

  // Render Bookmarks list with client-side filter parity
  function applyBookmarksFilters() {
    const container = document.getElementById("bookmarks-list");
    if (!container) return;

    //Reads the values of all five dropdowns on the Bookmarks tab.
    const roleVal = (document.getElementById("bm-jobrole-filter")?.value || "all").toLowerCase();
    const locVal = (document.getElementById("bm-location-filter")?.value || "all").toLowerCase();
    const typeVal = (document.getElementById("bm-jobtype-filter")?.value || "all").toLowerCase();
    const expVal = (document.getElementById("bm-experience-filter")?.value || "all").toLowerCase();
    const sortVal = document.getElementById("bm-sort-filter")?.value || "match";

    let filtered = [...userBookmarks];

    // Filter by Role
    if (roleVal !== "all" && roleVal !== "") {
      filtered = filtered.filter(b => {
        const title = (b.title || "").toLowerCase();
        return title.includes(roleVal) || roleVal.includes(title);
      });
    }

    // Filter by Location (Sri Lanka / Remote)
    if (locVal !== "all" && locVal !== "") {
      filtered = filtered.filter(b => {
        const loc = (b.location || "").toLowerCase();
        const city = (b.city || "").toLowerCase();
        const country = (b.country || "").toLowerCase();
        if (locVal.includes("remote")) {
          return loc.includes("remote") || city.includes("remote") || country.includes("global");
        }
        if (locVal.includes("sri lanka")) {
          return loc.includes("sri lanka") || country.includes("sri lanka") || country.includes("lk") ||
                 city.includes("colombo") || loc.includes("colombo") || city.includes("bambalapitiya") ||
                 city.includes("moratuwa") || loc.includes("moratuwa") || city.includes("nugegoda");
        }
        return loc.includes(locVal) || locVal.includes(loc);
      });
    }

    // Filter by Job Type
    if (typeVal !== "all" && typeVal !== "") {
      filtered = filtered.filter(b => {
        const jt = (b.job_type || "").toLowerCase();
        return jt === typeVal;
      });
    }

    // Filter by Experience
    if (expVal !== "all" && expVal !== "") {
      filtered = filtered.filter(b => {
        const exp = (b.experience_level || "").toLowerCase();
        return exp === expVal;
      });
    }

    // Sort
    if (sortVal === "match") {
      filtered.sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0));
    } else if (sortVal === "salary-high") {
      filtered.sort((a, b) => {
        const getSal = (s) => parseInt(String(s.salary || "").replace(/[^0-9]/g, "") || "0");
        return getSal(b) - getSal(a);
      });
    }

    if (filtered.length === 0) {
      if (userBookmarks.length === 0) {  //Checks if the bookmarks are empty
        container.innerHTML = `
          <div style="text-align: center; padding: 48px 24px; color: #64748b;">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 12px;">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
            </svg>
            <p style="font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 6px;">No saved bookmarks yet</p>
            <p style="font-size: 14px;">Browse the Find Jobs tab and click "Save" on jobs you'd like to revisit later.</p>
          </div>
        `;
      } else {  //Checks if there is a matching bookmark
        container.innerHTML = `
          <div style="text-align: center; padding: 40px; color: #64748b;">
            <p style="font-size: 15px; font-weight: 500;">No bookmarked jobs match the selected filters.</p>
          </div>
        `;
      }
      return;
    }

    container.innerHTML = filtered.map(renderBookmarkCard).join("");
  }

  // Toggle bookmark for a job from Find Jobs
  async function toggleSaveJob(jobId, btnEl) {
    const job = loadedJobs.find(j => String(j.id) === String(jobId));
    if (!job) return;

    const existingBm = findBookmark(job);

    if (existingBm) {
      // Remove bookmark
      try {
        btnEl.disabled = true;
        await API.removeBookmark(existingBm.id || existingBm.bm_id);
        userBookmarks = userBookmarks.filter(b => b !== existingBm);
        btnEl.className = "job-btn-save";
        btnEl.innerHTML = "<span>Save</span>";
        applyBookmarksFilters();
      } catch (err) {
        console.error("Failed to remove bookmark:", err);
      } finally {
        btnEl.disabled = false;
      }
    } else {
      // Save bookmark
      try {
        btnEl.disabled = true;
        const res = await API.saveBookmark({
          title: job.title,
          company: job.company,
          location: job.location,
          salary: job.salary,
          matchScore: job.matchScore,
          url: job.url,
          job_type: job.job_type || "Full-time"
        });

        const newBm = {
          id: res.bm_id,
          bm_id: res.bm_id,
          title: job.title,
          company: job.company,
          location: job.location,
          salary: job.salary,
          matchScore: job.matchScore,
          url: job.url,
          job_type: job.job_type || "Full-time"
        };
        userBookmarks.unshift(newBm);

        btnEl.className = "job-btn-save bookmarked";
        btnEl.innerHTML = "<span>Saved</span>";
        applyBookmarksFilters();
      } catch (err) {
        console.error("Failed to save bookmark:", err);
      } finally {
        btnEl.disabled = false;
      }
    }
  }

  // Remove bookmark directly from Bookmarks tab
  async function removeBookmark(bmId, btnEl) {
    const card = document.getElementById(`bm-card-${bmId}`);
    try {
      if (btnEl) btnEl.disabled = true;
      await API.removeBookmark(bmId);
      userBookmarks = userBookmarks.filter(b => (b.id !== bmId && b.bm_id !== bmId));

      if (card) {
        card.style.transition = "opacity 0.3s ease, transform 0.3s ease";
        card.style.opacity = "0";
        card.style.transform = "scale(0.95)";
        setTimeout(() => {
          applyBookmarksFilters();
        }, 300);
      } else {
        applyBookmarksFilters();
      }

      // Update matching card in Find Jobs if currently visible
      const findJobsCards = document.querySelectorAll("#job-roles-list .job-card");
      findJobsCards.forEach(c => {
        const btn = c.querySelector(".job-btn-save");
        if (btn && btn.classList.contains("bookmarked")) {
          const cTitle = c.dataset.role;
          const cComp = c.dataset.company;
          const isStillBookmarked = userBookmarks.some(b => b.title === cTitle && b.company === cComp);
          if (!isStillBookmarked) {
            btn.className = "job-btn-save";
            btn.innerHTML = "<span>Save</span>";
          }
        }
      });

    } catch (err) {
      console.error("Failed to delete bookmark:", err);
      if (btnEl) btnEl.disabled = false;
    }
  }

  // Navigate to Find Jobs and filter specifically by that role
  function filterJobsByRole(jobTitle) {
    // 1. Switch sidebar tab
    const jobrolesTab = document.getElementById("jobroles-tab");
    if (jobrolesTab) jobrolesTab.click();

    // 2. Set dropdown value
    const roleSelect = document.getElementById("jobrole-filter");
    if (roleSelect) {
      // Check if option exists, or add it
      let found = false;
      for (let i = 0; i < roleSelect.options.length; i++) {
        if (roleSelect.options[i].value.toLowerCase() === jobTitle.toLowerCase()) {
          roleSelect.selectedIndex = i;
          found = true;
          break;
        }
      }
      if (!found) {
        const newOpt = document.createElement("option");
        newOpt.value = jobTitle;
        newOpt.textContent = jobTitle;
        newOpt.selected = true;
        roleSelect.appendChild(newOpt);
      }
    }

    // 3. Reset other filters to all for clear view of this role
    const loc = document.getElementById("location-filter");
    if (loc) loc.value = "all";
    const type = document.getElementById("jobtype-filter");
    if (type) type.value = "all";
    const exp = document.getElementById("experience-filter");
    if (exp) exp.value = "all";

    // 4. Trigger filtered search
    applyFindJobsFilters();

    // 5. Scroll container into view smoothly
    setTimeout(() => {
      const container = document.getElementById("job-roles-list");
      if (container) {
        container.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 150);
  }

  // Initialize Jobs Module
  async function initJobsModule() {
    // Fetch bookmarks first
    try {
      userBookmarks = await API.getBookmarks();
    } catch (e) {
      userBookmarks = [];
    }

    // Fetch analysis data to populate matched job roles & detect intern status
    let isCandidateIntern = false;
    try {
      const analysisData = await API.getAnalysis();
      const hasRoles = Boolean(analysisData && analysisData.job_analyses && analysisData.job_analyses.length > 0);
      if (hasRoles) {
        const roles = analysisData.job_analyses.map(j => j.job_title);
        populateJobRoleDropdowns(roles);
        if (analysisData.career_stage === "intern_fresher" || (analysisData.experience_years !== undefined && analysisData.experience_years <= 2.5)) {
          isCandidateIntern = true;
        }
      } else {
        userMatchedRoles = [];
      }
    } catch (e) {
      console.warn("Could not load analysis roles for dropdown:", e);
    }

    // Default Job Type filter to 'Intern' for intern candidates
    const jobTypeFilter = document.getElementById("jobtype-filter");
    if (jobTypeFilter && isCandidateIntern && (!jobTypeFilter.value || jobTypeFilter.value === "all")) {
      jobTypeFilter.value = "Intern";
    }

    // Render initial bookmarks
    applyBookmarksFilters();

    // Render initial jobs (defaults to all matched roles, adapted for intern candidates)
    await applyFindJobsFilters();

    // Attach filter change listeners for Find Jobs
    const findJobFilters = [
      "jobrole-filter",
      "location-filter",
      "jobtype-filter",
      "experience-filter",
      "sort-filter"
    ];
    findJobFilters.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("change", () => {
          applyFindJobsFilters();
        });
      }
    });

    // Attach filter change listeners for Bookmarks
    const bmFilters = [
      "bm-jobrole-filter",
      "bm-location-filter",
      "bm-jobtype-filter",
      "bm-experience-filter",
      "bm-sort-filter"
    ];
    bmFilters.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("change", () => {
          applyBookmarksFilters();
        });
      }
    });
  }

  // Expose public API
  window.JobMakerJobs = {
    init: initJobsModule,
    filterJobsByRole: filterJobsByRole,
    toggleSaveJob: toggleSaveJob,
    removeBookmark: removeBookmark,
    applyFindJobsFilters: applyFindJobsFilters,
    applyBookmarksFilters: applyBookmarksFilters,
    populateJobRoleDropdowns: populateJobRoleDropdowns
  };

})(window);
