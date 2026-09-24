// JobMaker API Client
const API_BASE = window.location.origin.includes(":5000") 
  ? "" 
  : "http://127.0.0.1:5000";

const API = {
  // Fetch user profile, resume summary, and skills
  async getProfile() {
    try {
      const res = await fetch(`${API_BASE}/api/profile`, {
        credentials: "include"
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("Could not fetch profile from backend, using cached state", err);
      return null;
    }
  },

  // Save profile updates
  async updateProfile(profileData) {
    const res = await fetch(`${API_BASE}/api/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(profileData)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },

  // Fetch cached analysis: experience, education, skills cloud, and all job gap analyses
  async getAnalysis() {
    try {
      const res = await fetch(`${API_BASE}/api/analysis`, {
        credentials: "include"
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("Could not fetch analysis from backend, using cached state", err);
      return null;
    }
  },

  // Step 1: Parse resume without saving to DB (for review & approval)
  async parseResume(file) {
    const formData = new FormData();
    formData.append("resume", file);

    const res = await fetch(`${API_BASE}/api/resume/parse`, {
      method: "POST",
      credentials: "include",
      body: formData
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      let msg = errJson.error || `Parsing failed with HTTP ${res.status}`;
      msg = msg.replace(/AIza[0-9A-Za-z-_]{20,}/g, "[REDACTED]").replace(/key=[a-zA-Z0-9_\-]+/gi, "key=[REDACTED]");
      throw new Error(msg);
    }

    return await res.json();
  },

  // Step 2: Confirm and save approved resume data to MySQL
  async confirmResume(stagedFilename, analysis, rawText = "") {
    const res = await fetch(`${API_BASE}/api/resume/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        staged_filename: stagedFilename,
        analysis: analysis,
        raw_text: rawText
      })
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      let msg = errJson.error || `Confirmation failed with HTTP ${res.status}`;
      msg = msg.replace(/AIza[0-9A-Za-z-_]{20,}/g, "[REDACTED]").replace(/key=[a-zA-Z0-9_\-]+/gi, "key=[REDACTED]");
      throw new Error(msg);
    }

    return await res.json();
  },

  // Discard staged resume if user rejects the parse
  async discardResume(stagedFilename) {
    try {
      const res = await fetch(`${API_BASE}/api/resume/discard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ staged_filename: stagedFilename })
      });
      return await res.json();
    } catch (e) {
      console.warn("Discard call failed:", e);
      return { success: true };
    }
  },

  // Direct upload and commit (backward compatibility)
  async uploadResume(file) {
    const formData = new FormData();
    formData.append("resume", file);

    const res = await fetch(`${API_BASE}/api/resume/upload`, {
      method: "POST",
      credentials: "include",
      body: formData
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      let msg = errJson.error || `Upload failed with HTTP ${res.status}`;
      msg = msg.replace(/AIza[0-9A-Za-z-_]{20,}/g, "[REDACTED]").replace(/key=[a-zA-Z0-9_\-]+/gi, "key=[REDACTED]");
      throw new Error(msg);
    }

    return await res.json();
  },

  // Fetch live or curated job postings
  async getJobs(filters = {}) {
    try {
      const params = new URLSearchParams();
      if (filters.role) params.append("role", filters.role);
      if (filters.location) params.append("location", filters.location);
      if (filters.job_type) params.append("job_type", filters.job_type);
      if (filters.experience) params.append("experience", filters.experience);
      if (filters.sort) params.append("sort", filters.sort);

      const qs = params.toString() ? `?${params.toString()}` : "";
      const res = await fetch(`${API_BASE}/api/jobs${qs}`, {
        credentials: "include"
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("Could not fetch jobs from backend, fallback active", err);
      return { jobs: [], user_roles: [] };
    }
  },

  // Fetch bookmarks
  async getBookmarks() {
    try {
      const res = await fetch(`${API_BASE}/api/bookmarks`, {
        credentials: "include"
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("Could not fetch bookmarks from backend", err);
      return [];
    }
  },

  // Save a job to bookmarks
  async saveBookmark(jobData) {
    const res = await fetch(`${API_BASE}/api/bookmarks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(jobData)
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.error || `Failed to save bookmark (HTTP ${res.status})`);
    }
    return await res.json();
  },

  // Remove a job from bookmarks
  async removeBookmark(bmId) {
    const res = await fetch(`${API_BASE}/api/bookmarks/${bmId}`, {
      method: "DELETE",
      credentials: "include"
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.error || `Failed to delete bookmark (HTTP ${res.status})`);
    }
    return await res.json();
  }

};
