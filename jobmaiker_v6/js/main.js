// JobMaker Main Application Entry Point

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Sidebar Tab Navigation System
  const tabs = document.querySelectorAll(".sidebar-tab");
  const sections = document.querySelectorAll(".page-section");

  function showSection(targetId) {
    sections.forEach(section => {
      section.classList.toggle("active", section.id === targetId);
    });

    tabs.forEach(tab => {
      tab.classList.toggle("active-tab", tab.dataset.target === targetId);
    });

    history.replaceState(null, "", `#${targetId}`);
  }

  tabs.forEach(tab => {
    tab.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = tab.dataset.target;
      showSection(targetId);

      if (targetId === "jobroles-content") {
        if (window.JobMakerJobs) window.JobMakerJobs.applyFindJobsFilters();
      } else if (targetId === "bookmark-content") {
        if (window.JobMakerJobs) window.JobMakerJobs.applyBookmarksFilters();
      } else if (targetId === "analysis-content") {
        if (typeof initAnalysis === "function") {
          initAnalysis().catch(err => console.error("Analysis refresh error:", err));
        }
      }
    });
  });

  const initial = window.location.hash.replace("#", "") || "analysis-content";
  showSection(initial);

  // 2. Initialize Profile & Analysis Modules independently
  if (typeof initProfile === "function") {
    initProfile().catch(err => console.error("Profile initialization error:", err));
  }
  if (typeof initAnalysis === "function") {
    initAnalysis().catch(err => console.error("Analysis initialization error:", err));
  }

  // 3. Initialize Jobs & Bookmarks Module
  if (window.JobMakerJobs && typeof window.JobMakerJobs.init === "function") {
    window.JobMakerJobs.init().catch(err => console.error("Jobs initialization error:", err));
  }
});
