// JobMaker Profile Management & CV Upload Module

function updateProfileUI(userData, resumeData) {
  if (userData) {
    const displayName = document.getElementById("prof-display-name");
    const displayRole = document.getElementById("prof-display-role");
    const displayLocation = document.getElementById("prof-display-location");
    const displayEmail = document.getElementById("prof-display-email");
    const displayPhone = document.getElementById("prof-display-phone");

    if (displayName) displayName.textContent = userData.full_name || userData.username || "User";
    if (displayRole) displayRole.textContent = userData.role || "No title set";
    if (displayLocation) displayLocation.textContent = userData.location || "Not specified";
    if (displayEmail) displayEmail.textContent = userData.email || "Not specified";
    if (displayPhone) displayPhone.textContent = userData.phone || "Not specified";

    // Social Links
    const setLink = (linkId, textId, url) => {
      const linkEl = document.getElementById(linkId);
      const textEl = document.getElementById(textId);
      if (!url) {
        if (textEl) textEl.textContent = "Not connected";
        if (linkEl) linkEl.removeAttribute("href");
        return;
      }
      const cleanUrl = url.replace(/^https?:\/\//, "");
      if (linkEl) linkEl.href = url.startsWith("http") ? url : `https://${url}`;
      if (textEl) textEl.textContent = cleanUrl;
    };

    setLink("prof-link-linkedin", "prof-text-linkedin", userData.linkedin);
    setLink("prof-link-github", "prof-text-github", userData.github);
    setLink("prof-link-web", "prof-text-web", userData.portfolio);

    // Profile Score Ring
    const scoreVal = (userData.profile_score !== undefined && userData.profile_score !== null) ? userData.profile_score : 0;
    const scoreText = document.querySelector(".completion-ring-chart .percentage");
    const circlePath = document.querySelector(".completion-ring-chart .circle");
    if (scoreText) scoreText.textContent = `${scoreVal}%`;
    if (circlePath) circlePath.setAttribute("stroke-dasharray", `${scoreVal}, 100`);

    // Edit form inputs initial values
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val || "";
    };
    setVal("input-name", userData.full_name || "");
    setVal("input-role", userData.role || "");
    setVal("input-location", userData.location || "");
    setVal("input-email", userData.email || "");
    setVal("input-phone", userData.phone || "");
    setVal("input-linkedin", userData.linkedin || "");
    setVal("input-github", userData.github || "");
    setVal("input-web", userData.portfolio || "");
  }

  if (resumeData && resumeData.summary) {
    const summarySection = document.getElementById("cv-summary-section");
    const summaryContent = document.getElementById("cv-summary-content");
    const fileNameEl = document.getElementById("cv-file-name");
    const uploadStatusEl = document.getElementById("cv-upload-status");

    if (summarySection) summarySection.style.display = "block";
    if (summaryContent) summaryContent.textContent = resumeData.summary;
    if (fileNameEl && resumeData.file_name && resumeData.file_name !== "None") {
      fileNameEl.textContent = resumeData.file_name;
    }
    if (uploadStatusEl) {
      uploadStatusEl.textContent = "Parsed with Gemini AI";
      uploadStatusEl.style.color = "#10b981";
    }
  } else {
    const summarySection = document.getElementById("cv-summary-section");
    if (summarySection) summarySection.style.display = "none";
  }
}

async function initProfile() {
  // 1. Initial Load from Backend
  const profileData = await API.getProfile();
  if (profileData) {
    updateProfileUI(profileData.user, profileData.resume);
  }

  // 2. Edit Profile Form Toggle
  const toggleEditBtn = document.getElementById("toggle-edit-btn");
  const editSection = document.getElementById("profile-edit-section");
  const editBtnText = document.getElementById("edit-btn-text");
  const cancelBtn = document.getElementById("cancel-profile-btn");
  const saveBtn = document.getElementById("save-profile-btn");

  if (toggleEditBtn && editSection) {
    toggleEditBtn.addEventListener("click", () => {
      const isHidden = editSection.style.display === "none";
      editSection.style.display = isHidden ? "block" : "none";
      editBtnText.textContent = isHidden ? "Close Edit" : "Edit Profile";
    });
  }

  if (cancelBtn && editSection) {
    cancelBtn.addEventListener("click", () => {
      editSection.style.display = "none";
      editBtnText.textContent = "Edit Profile";
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : "";
      };

      const payload = {
        name: getVal("input-name"),
        role: getVal("input-role"),
        location: getVal("input-location"),
        email: getVal("input-email"),
        phone: getVal("input-phone"),
        linkedin: getVal("input-linkedin"),
        github: getVal("input-github"),
        portfolio: getVal("input-web")
      };

      saveBtn.textContent = "Saving...";
      saveBtn.disabled = true;

      try {
        await API.updateProfile(payload);
        const refreshed = await API.getProfile();
        if (refreshed) {
          updateProfileUI(refreshed.user, refreshed.resume);
        }
        editSection.style.display = "none";
        editBtnText.textContent = "Edit Profile";
      } catch (err) {
        alert("Failed to save profile: " + err.message);
      } finally {
        saveBtn.textContent = "Save Changes";
        saveBtn.disabled = false;
      }
    });
  }

  // 3. Avatar Change Preview
  const avatarInput = document.getElementById("avatar-file-input");
  const profileAvatarImg = document.getElementById("profile-avatar-img");
  const sidebarProfileIcon = document.getElementById("sidebar-profile-icon");

  if (avatarInput) {
    avatarInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function(evt) {
          if (profileAvatarImg) profileAvatarImg.src = evt.target.result;
          if (sidebarProfileIcon) sidebarProfileIcon.src = evt.target.result;
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // 4. CV Upload Drag & Drop and File Input
  const dropZone = document.getElementById("cv-drop-zone");
  const fileInput = document.getElementById("cv-file-input");
  const summarySection = document.getElementById("cv-summary-section");
  const summaryContent = document.getElementById("cv-summary-content");
  const fileNameEl = document.getElementById("cv-file-name");
  const dropIconContainer = document.getElementById("cv-drop-icon-container");
  const mainDropText = document.getElementById("cv-main-drop-text");
  const subDropText = document.getElementById("cv-sub-drop-text");
  const uploadStatusEl = document.getElementById("cv-upload-status");

  if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        handleCVUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleCVUpload(e.target.files[0]);
      }
    });
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

  function formatUserFriendlyError(err) {
    if (!err) return "Unable to analyze CV. Please try again.";
    let msg = typeof err === "string" ? err : (err.message || "");
    // Redact any accidental API key patterns
    msg = msg.replace(/AIza[0-9A-Za-z-_]{20,}/g, "");
    msg = msg.replace(/key=[a-zA-Z0-9_\-]+/gi, "");
    msg = msg.replace(/\[REDACTED_API_KEY\]/gi, "");
    msg = msg.replace(/\[REDACTED\]/gi, "");

    const technicalPatterns = [
      /generativelanguage/i,
      /connectionpool/i,
      /requestexception/i,
      /max retries exceeded/i,
      /x-goog-api-key/i,
      /traceback/i,
      /internal server error/i,
      /http\s*500/i
    ];
    if (technicalPatterns.some(p => p.test(msg)) || msg.length > 150) {
      return "AI resume analysis service is temporarily unavailable. Please try again shortly.";
    }
    return msg.trim() || "Unable to analyze CV. Please verify your document and try again.";
  }

  async function handleCVUpload(file) {
    if (fileNameEl) fileNameEl.textContent = file.name;
    if (summarySection) summarySection.style.display = "block";
    if (summaryContent) {
      summaryContent.innerHTML = `
        <div class="gemini-buffering-box">
          <div class="gemini-buffering-spinner"></div>
          <div class="gemini-buffering-info">
            <div class="buffering-title">Gemini AI is Parsing & Evaluating Your CV...</div>
            <div class="buffering-desc">Extracting skills, experience, education, and performing multi-role match & gap analysis.</div>
            <div class="buffering-steps">
              <span class="step-pill">1. Document Parsing</span>
              <span class="step-pill">2. Skill Extraction</span>
              <span class="step-pill">3. Role Matchmaking</span>
            </div>
          </div>
        </div>
      `;
    }

    if (uploadStatusEl) {
      uploadStatusEl.textContent = "Analyzing with Gemini...";
      uploadStatusEl.style.color = "#0284c7";
    }

    if (dropIconContainer) {
      dropIconContainer.innerHTML = `<div class="gemini-drop-spinner"></div>`;
    }
    if (mainDropText) mainDropText.innerHTML = `<span style="color: #0284c7; font-weight: 600;">Analyzing ${file.name}...</span>`;
    if (subDropText) subDropText.textContent = "Please wait while Gemini evaluates skills and job roles.";

    let stageIndex = 0;
    const stages = [
      "Analyzing with Gemini AI...",
      "Extracting skills & qualifications...",
      "Matching against target job roles...",
      "Finalizing career evaluation..."
    ];
    const stageInterval = setInterval(() => {
      stageIndex = (stageIndex + 1) % stages.length;
      if (uploadStatusEl) uploadStatusEl.textContent = stages[stageIndex];
      if (subDropText) subDropText.textContent = stages[stageIndex];
    }, 2500);

    try {
      // Step 1: Parse resume without saving to DB yet
      const parseResponse = await API.parseResume(file);
      clearInterval(stageInterval);
      const analysis = parseResponse.analysis;
      const stagedFilename = parseResponse.staged_filename;
      const rawText = parseResponse.raw_text;

      // Reset dropzone text to awaiting confirmation
      if (dropIconContainer) {
        dropIconContainer.innerHTML = `
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        `;
      }
      if (mainDropText) mainDropText.innerHTML = `<span style="color: #0284c7; font-weight: 600;">Parsed! Awaiting Your Review</span>`;
      if (subDropText) subDropText.textContent = "Review extracted details in the popup window";
      if (uploadStatusEl) {
        uploadStatusEl.textContent = "Awaiting Approval";
        uploadStatusEl.style.color = "#0284c7";
      }

      // Step 2: Show Review Modal
      showCVReviewModal({
        file: file,
        stagedFilename: stagedFilename,
        analysis: analysis,
        rawText: rawText
      });

    } catch (err) {
      clearInterval(stageInterval);
      console.error("Upload error:", err);
      const friendlyMsg = formatUserFriendlyError(err);
      if (summaryContent) {
        summaryContent.innerHTML = `<span style="color: #ef4444; font-weight: 500;">Error analyzing CV: ${escapeHtml(friendlyMsg)}</span>`;
      }
      if (uploadStatusEl) {
        uploadStatusEl.textContent = "Analysis Failed";
        uploadStatusEl.style.color = "#ef4444";
      }
      if (mainDropText) mainDropText.innerHTML = `<span style="color: #ef4444; font-weight: 600;">Upload Failed</span>`;
      if (subDropText) subDropText.textContent = friendlyMsg;
    }
  }

  // Helper: Live client-side standardizer for degree titles
  function clientStandardizeDegree(val) {
    if (!val) return "";
    let s = val.trim();
    s = s.replace(/\bbachelor\s+of\s+science\b/gi, "B.Sc.");
    s = s.replace(/\bb\.?s\.?c\b\.?/gi, "B.Sc.");
    s = s.replace(/\bbsc\b\.?/gi, "B.Sc.");
    s = s.replace(/\bb\.?s\b(?!\s+(?:in\s+)?(?:engineering|developer))/gi, "B.Sc.");
    s = s.replace(/\bbachelor\s+of\s+technology\b/gi, "B.Tech.");
    s = s.replace(/\bb\.?tech\b\.?/gi, "B.Tech.");
    s = s.replace(/\bbachelor\s+of\s+engineering\b/gi, "B.Eng.");
    s = s.replace(/\bb\.?eng\b\.?/gi, "B.Eng.");
    s = s.replace(/\bb\.?e\b\.?/gi, "B.E.");
    s = s.replace(/\bmaster\s+of\s+science\b/gi, "M.Sc.");
    s = s.replace(/\bm\.?s\.?c\b\.?/gi, "M.Sc.");
    s = s.replace(/\bmsc\b\.?/gi, "M.Sc.");
    s = s.replace(/\.{2,}/g, ".");
    s = s.replace(/\(?\bhons\.?\b\)?/gi, "(Hons)");
    s = s.replace(/\(\s*(?!Hons\b)(?:in\s+)?([A-Za-z\s]+)\s*\)/g, "in $1");

    const lowercaseWords = ["in", "of", "and", "with", "for", "at", "on"];
    const tokens = s.split(" ").filter(Boolean);
    const formatted = tokens.map((tok, i) => {
      if (tok.includes(".") || ["(Hons)", "IT", "AI", "ML", "CS", "SE", "B.Sc.", "B.Tech.", "B.Eng.", "M.Sc.", "M.Tech."].includes(tok)) {
        return tok;
      }
      if (lowercaseWords.includes(tok.toLowerCase()) && i !== 0) {
        return tok.toLowerCase();
      }
      return tok.split("-").map(p => p.charAt(0).toUpperCase() + p.slice(1)).join("-");
    });
    let result = formatted.join(" ").trim();
    result = result.replace(/(B\.Sc\.|B\.Tech\.|B\.Eng\.|M\.Sc\.|M\.Tech\.)\s+in\s+\(Hons\)/g, "$1 (Hons)");
    result = result.replace(/^(B\.Sc\.|B\.Tech\.|B\.Eng\.|M\.Sc\.|M\.Tech\.)\s+(?!in\b|\(Hons\))/g, "$1 in ");
    result = result.replace(/\(Hons\)\s+(?!in\b)/g, "(Hons) in ");
    result = result.replace(/\s+in\s+in\b/gi, " in");
    return result.replace(/\s+/g, " ").trim();
  }

  // --- REVIEW & APPROVAL MODAL CONTROLLER ---
  function showCVReviewModal(data) {
    const modal = document.getElementById("cv-review-modal");
    if (!modal) return;

    const analysis = data.analysis || {};
    const personal = analysis.personal_info || {};
    const education = analysis.education || {};
    const jobAnalyses = analysis.all_job_analyses || [];
    const isIntern = analysis.candidate_level === "intern_fresher";

    let currentSkills = [...((analysis.skills) || [])];

    // Form inputs
    const nameInput = document.getElementById("review-name");
    const roleInput = document.getElementById("review-role");
    const emailInput = document.getElementById("review-email");
    const phoneInput = document.getElementById("review-phone");
    const locInput = document.getElementById("review-location");
    const degInput = document.getElementById("review-degree");
    const instInput = document.getElementById("review-institute");
    const durInput = document.getElementById("review-duration");
    const summaryInput = document.getElementById("review-summary");
    const careerSelect = document.getElementById("review-career-select");

    if (nameInput) nameInput.value = personal.name || "";
    if (roleInput) roleInput.value = personal.role || "";
    if (emailInput) emailInput.value = personal.email || "";
    if (phoneInput) phoneInput.value = personal.phone || "";
    if (locInput) locInput.value = personal.location || "";

    // Standardize initial degree and wire live auto-standardize on blur
    const initialDeg = clientStandardizeDegree(education.degree || "");
    if (degInput) {
      degInput.value = initialDeg;
      degInput.onblur = function() {
        if (degInput.value) {
          degInput.value = clientStandardizeDegree(degInput.value);
        }
      };
    }

    if (instInput) instInput.value = education.institute || "";
    if (durInput) {
      const durText = [education.duration, education.graduation_year].filter(Boolean).join(" • ");
      durInput.value = durText || "";
    }
    if (summaryInput) summaryInput.value = analysis.summary || "";
    if (careerSelect) {
      careerSelect.value = isIntern ? "intern_fresher" : "experienced";
    }

    // Interactive skills tag manager
    function renderReviewSkills() {
      const skillsCloudEl = document.getElementById("review-skills-cloud");
      if (!skillsCloudEl) return;
      if (currentSkills.length === 0) {
        skillsCloudEl.innerHTML = `<span style="color: #94a3b8; font-size: 12.5px;">No skills added yet. Use the field below to add skills.</span>`;
        return;
      }
      skillsCloudEl.innerHTML = currentSkills.map((s, idx) => `
        <span class="review-skill-chip-interactive">
          <span>${s}</span>
          <button type="button" class="remove-skill-btn" data-skill-idx="${idx}" title="Remove skill">×</button>
        </span>
      `).join("");

      skillsCloudEl.querySelectorAll(".remove-skill-btn").forEach(btn => {
        btn.onclick = function(e) {
          e.stopPropagation();
          const idx = parseInt(this.getAttribute("data-skill-idx"), 10);
          currentSkills.splice(idx, 1);
          renderReviewSkills();
        };
      });
    }

    renderReviewSkills();

    // Wire Add Skill
    const addSkillInput = document.getElementById("review-add-skill-input");
    const addSkillBtn = document.getElementById("review-add-skill-btn");

    function addCustomSkill() {
      if (!addSkillInput) return;
      const val = addSkillInput.value.trim();
      if (val && !currentSkills.some(s => s.toLowerCase() === val.toLowerCase())) {
        currentSkills.push(val);
        renderReviewSkills();
        addSkillInput.value = "";
      }
    }

    if (addSkillBtn) addSkillBtn.onclick = addCustomSkill;
    if (addSkillInput) {
      addSkillInput.onkeydown = function(e) {
        if (e.key === "Enter") {
          e.preventDefault();
          addCustomSkill();
        }
      };
    }

    // Rubric indicator
    const rubricEl = document.getElementById("review-rubric-badge");
    if (rubricEl) {
      rubricEl.textContent = isIntern ? "Intern / Fresher Adapted Rubric (Projects 20% • Skills 60%)" : "Experienced Rubric (Tenure 25% • Skills 50%)";
    }

    // Job matches preview list
    const matchesListEl = document.getElementById("review-job-matches-list");
    if (matchesListEl) {
      matchesListEl.innerHTML = jobAnalyses.map(j => `
        <div class="review-match-card">
          <div class="review-match-header">
            <span class="review-match-title">${j.job_title}</span>
            <span class="review-match-score">${j.match_percentage}%</span>
          </div>
          <p class="review-match-summary">${j.compatibility_summary || j.score_explanation || ""}</p>
        </div>
      `).join("");
    }

    // Open modal
    modal.style.display = "flex";

    // Wire Approve Button
    const btnApprove = document.getElementById("btn-approve-cv");
    const btnDiscard = document.getElementById("btn-discard-cv");

    // Clean old event listeners by cloning
    const newBtnApprove = btnApprove.cloneNode(true);
    const newBtnDiscard = btnDiscard.cloneNode(true);
    btnApprove.parentNode.replaceChild(newBtnApprove, btnApprove);
    btnDiscard.parentNode.replaceChild(newBtnDiscard, btnDiscard);

    newBtnApprove.addEventListener("click", async () => {
      newBtnApprove.disabled = true;
      newBtnApprove.innerHTML = `<span class="btn-spinner"></span> Saving to Profile...`;

      try {
        // Collect edited values from the modal inputs
        data.analysis.personal_info = data.analysis.personal_info || {};
        data.analysis.personal_info.name = nameInput ? nameInput.value.trim() : (personal.name || "");
        data.analysis.personal_info.role = roleInput ? roleInput.value.trim() : (personal.role || "");
        data.analysis.personal_info.email = emailInput ? emailInput.value.trim() : (personal.email || "");
        data.analysis.personal_info.phone = phoneInput ? phoneInput.value.trim() : (personal.phone || "");
        data.analysis.personal_info.location = locInput ? locInput.value.trim() : (personal.location || "");
        data.analysis.personal_info.linkedin = personal.linkedin || "";
        data.analysis.personal_info.github = personal.github || "";
        data.analysis.personal_info.portfolio = personal.portfolio || "";

        data.analysis.education = data.analysis.education || {};
        const cleanedFinalDeg = degInput ? clientStandardizeDegree(degInput.value.trim()) : (education.degree || "");
        data.analysis.education.degree = cleanedFinalDeg;
        data.analysis.education.institute = instInput ? instInput.value.trim() : (education.institute || "");
        data.analysis.education.duration = durInput ? durInput.value.trim() : (education.duration || "");

        data.analysis.summary = summaryInput ? summaryInput.value.trim() : (analysis.summary || "");
        data.analysis.skills = currentSkills;

        if (careerSelect) {
          data.analysis.candidate_level = careerSelect.value;
          data.analysis.candidate_level_label = careerSelect.value === "intern_fresher" ? "Intern / Fresher Applicant" : "Experienced Professional";
        }

        const confirmRes = await API.confirmResume(data.stagedFilename, data.analysis, data.rawText);

        modal.style.display = "none";

        // Update Dropzone to confirmed state
        const dropIconContainer = document.getElementById("cv-drop-icon-container");
        const mainDropText = document.getElementById("cv-main-drop-text");
        const subDropText = document.getElementById("cv-sub-drop-text");
        const uploadStatusEl = document.getElementById("cv-upload-status");
        const summaryContent = document.getElementById("cv-summary-content");

        if (dropIconContainer) {
          dropIconContainer.innerHTML = `
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
          `;
        }
        if (mainDropText) mainDropText.innerHTML = `<span style="color: #10b981; font-weight: 600;">CV Approved & Profile Updated!</span>`;
        if (subDropText) subDropText.textContent = "Your details and multi-role gap analyses are active.";
        if (uploadStatusEl) {
          uploadStatusEl.textContent = "Saved & Active";
          uploadStatusEl.style.color = "#10b981";
        }
        if (summaryContent && confirmRes.summary) {
          summaryContent.textContent = confirmRes.summary;
        }

        // Refresh UI from database
        const refreshed = await API.getProfile();
        if (refreshed) {
          updateProfileUI(refreshed.user, refreshed.resume);
        }
        if (typeof initAnalysis === "function") {
          await initAnalysis();
        }

      } catch (e) {
        console.error("Confirmation error:", e);
        const friendlyConfirmErr = formatUserFriendlyError(e);
        alert("Failed to save confirmed resume: " + friendlyConfirmErr);
        newBtnApprove.disabled = false;
        newBtnApprove.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          Approve & Apply to Profile
        `;
      }
    });

    newBtnDiscard.addEventListener("click", async () => {
      newBtnDiscard.disabled = true;
      modal.style.display = "none";

      await API.discardResume(data.stagedFilename);

      // Revert Dropzone
      const dropIconContainer = document.getElementById("cv-drop-icon-container");
      const mainDropText = document.getElementById("cv-main-drop-text");
      const subDropText = document.getElementById("cv-sub-drop-text");
      const uploadStatusEl = document.getElementById("cv-upload-status");
      const fileInput = document.getElementById("cv-file-input");

      if (fileInput) fileInput.value = "";
      if (dropIconContainer) {
        dropIconContainer.innerHTML = `
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
        `;
      }
      if (mainDropText) mainDropText.innerHTML = `Drag & drop your CV here, or <span style="color: #0284c7; font-weight: 600;">browse</span>`;
      if (subDropText) subDropText.textContent = "Supports PDF, DOCX (Max 5MB)";
      if (uploadStatusEl) {
        uploadStatusEl.textContent = "Discarded (Current Profile Intact)";
        uploadStatusEl.style.color = "#64748b";
      }
    });
  }
}
