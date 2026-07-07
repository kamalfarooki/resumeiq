(function () {
  const resumeText = document.getElementById("resumeText");
  const jdText = document.getElementById("jdText");
  const rescoreBtn = document.getElementById("rescoreBtn");
  const wordCountEl = document.getElementById("wordCount");
  const scoreValue = document.getElementById("scoreValue");
  const scoreDelta = document.getElementById("scoreDelta");
  const recalcStatus = document.getElementById("recalcStatus");
  const gradeValue = document.getElementById("gradeValue");
  const healthValue = document.getElementById("healthValue");
  const interviewValue = document.getElementById("interviewValue");

  if (!resumeText || !rescoreBtn) return; // not on the results page

  // ---------------------------------------------------------
  // Tab switching (works for both editor tabs and score tabs)
  // ---------------------------------------------------------

  function wireTabs(tabSelector, panelSelector, dataAttr) {
    const tabs = document.querySelectorAll(tabSelector);
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const target = tab.getAttribute(dataAttr);
        document.querySelectorAll(tabSelector).forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        document.querySelectorAll(panelSelector).forEach((p) => {
          p.hidden = p.getAttribute(dataAttr.replace("-tab", "-panel")) !== target;
        });
      });
    });
  }

  wireTabs("[data-editor-tab]", "[data-editor-panel]", "data-editor-tab");
  wireTabs("[data-score-tab]", "[data-score-panel]", "data-score-tab");

  // Track which score tabs people actually use (separate from the tab
  // switching logic above, which just manages active/hidden state).
  document.querySelectorAll(".pane-tab[data-score-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-score-tab");
      if (window.ResumeIQTrack) window.ResumeIQTrack(`tab_click_${target}`);
    });
  });

  // Track PDF downloads and Learning tab link clicks via delegation
  // (learning links are re-rendered by JS on re-score).
  document.addEventListener("click", (e) => {
    if (e.target.closest("#downloadReportLink")) {
      if (window.ResumeIQTrack) window.ResumeIQTrack("download_clicked");
    }
    if (e.target.closest(".learning-link")) {
      if (window.ResumeIQTrack) window.ResumeIQTrack("learning_link_click");
    }
  });

  // Track feedback widget yes/no selection (separate from the actual
  // Formspree submission, which carries the real comment text).
  document.addEventListener("change", (e) => {
    if (e.target.name === "rating") {
      const event = e.target.value === "yes" ? "feedback_yes" : "feedback_no";
      if (window.ResumeIQTrack) window.ResumeIQTrack(event);
    }
  });

  // The recruiter score card is a shortcut into the "Why You'd Get Rejected"
  // tab, but it isn't itself a tab button — clicking it should trigger the
  // real tab button so the active-state highlight lands in the right place.
  document.querySelectorAll("[data-jump-to-tab]").forEach((el) => {
    el.addEventListener("click", () => {
      const target = el.getAttribute("data-jump-to-tab");
      const realTab = document.querySelector(`[data-score-tab="${target}"]`);
      if (realTab) realTab.click();
    });
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        el.click();
      }
    });
  });

  // ---------------------------------------------------------
  // Live word count as you type
  // ---------------------------------------------------------

  function estimateWordCount(text) {
    const trimmed = text.trim();
    return trimmed ? trimmed.split(/\s+/).length : 0;
  }

  resumeText.addEventListener("input", () => {
    if (wordCountEl) wordCountEl.textContent = estimateWordCount(resumeText.value);
  });

  // ---------------------------------------------------------
  // Small render helpers
  // ---------------------------------------------------------

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }

  function renderBreakdown(data) {
    const rows = [
      ["Experience", data.experience_score, 20],
      ["Education", data.education_score, 10],
      ["Certifications", data.certification_score, 10],
      ["Projects", data.project_score, 10],
      ["Contact info", data.contact_score, 5],
      ["Skills", data.skill_score, 35],
      ["Resume length", data.length_score, 10],
      ["Section completeness", data.section_score, 10],
    ];
    return rows.map(([label, value, max]) => `
      <div class="bar-row">
        <div class="bar-row-top"><span>${escapeHtml(label)}</span><span class="bar-value">${value}/${max}</span></div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.round((value / max) * 100)}%"></div></div>
      </div>
    `).join("");
  }

  function renderRecruiterBreakdown(data) {
    const components = (data.recruiter_score && data.recruiter_score.components) || {};
    return Object.keys(components).map((label) => {
      const comp = components[label];
      return `
        <div class="bar-row">
          <div class="bar-row-top"><span>${escapeHtml(label)}</span><span class="bar-value">${comp.value}/${comp.max}</span></div>
          <div class="bar-track"><div class="bar-fill bar-fill-recruiter" style="width:${Math.round((comp.value / comp.max) * 100)}%"></div></div>
        </div>
      `;
    }).join("");
  }

  function renderRejection(data) {
    const reasons = data.rejection_reasons || [];
    let html = `<p class="panel-intro">Framed the way a recruiter skimming for a few seconds would actually think it — not softened.</p>`;
    html += reasons.map((r) => `
      <div class="rec-row">
        <span class="rec-priority priority-${escapeHtml((r.severity || "").toLowerCase())}">${escapeHtml(r.severity)}</span>
        <div class="rec-message">${escapeHtml(r.reason)}</div>
      </div>
    `).join("");
    return html;
  }

  function renderTagRow(items, cls) {
    return items.map((s) => `<span class="tag ${cls}">${escapeHtml(s)}</span>`).join("");
  }

  function renderSkills(data) {
    let html = "";
    const domains = data.categorized_skills || {};
    const domainKeys = Object.keys(domains);
    if (domainKeys.length === 0) {
      html += `<p class="empty-note">No recognized technical skills found yet.</p>`;
    } else {
      domainKeys.forEach((domain) => {
        html += `<div class="domain-block"><div class="domain-label">${escapeHtml(domain)}</div>`;
        const categories = domains[domain];
        Object.keys(categories).forEach((cat) => {
          html += `<div class="skill-group"><h4>${escapeHtml(cat)}</h4><div class="tag-row">${renderTagRow(categories[cat], "tag-skill")}</div></div>`;
        });
        html += `</div>`;
      });
    }
    if (data.missing_core_skills && data.missing_core_skills.length) {
      html += `<div class="skill-group"><h4>Core skills missing for ${escapeHtml(data.detected_role)}</h4><div class="tag-row">${renderTagRow(data.missing_core_skills, "tag-missing")}</div></div>`;
    }
    if (data.recommended_certifications && data.recommended_certifications.length) {
      html += `<div class="skill-group"><h4>Recommended certifications</h4><div class="tag-row">${renderTagRow(data.recommended_certifications, "tag-cert")}</div></div>`;
    }
    return html;
  }

  function renderSections(data) {
    const sections = data.sections || {};
    return Object.keys(sections).map((name) => {
      const present = sections[name];
      return `<li class="${present ? "is-present" : "is-missing"}">
        <span>${escapeHtml(name)}</span>
        <span class="section-status">${present ? "Present" : "Missing"}</span>
      </li>`;
    }).join("");
  }

  function renderCareer(data) {
    const best = data.best_role;
    let html = `<div class="career-best">
      <span class="field-label">Best match</span>
      <div class="career-best-role">${escapeHtml(best ? best.role : data.detected_role)}</div>
      <div class="career-best-coverage">${best ? best.coverage : 0}% skill coverage</div>
    </div>`;
    (data.role_matches || []).forEach((role) => {
      html += `<div class="bar-row">
        <div class="bar-row-top"><span>${escapeHtml(role.role)}</span><span class="bar-value">${role.coverage}%</span></div>
        <div class="bar-track"><div class="bar-fill" style="width:${role.coverage}%"></div></div>
      </div>`;
    });
    return html;
  }

  function renderJd(data) {
    const jd = data.jd_match;
    if (!jd) {
      return `<p class="empty-note">Paste a job description in the "Job description" tab on the left, then hit Re-score, to see a match here.</p>`;
    }
    let html = `<div class="jd-score-row"><span class="jd-score">${jd.match_score}%</span><span>match to the pasted job description</span></div>`;
    if (jd.matched_skills && jd.matched_skills.length) {
      html += `<div class="skill-group"><h4>Matched skills</h4><div class="tag-row">${renderTagRow(jd.matched_skills, "tag-skill")}</div></div>`;
    }
    if (jd.missing_skills && jd.missing_skills.length) {
      html += `<div class="skill-group"><h4>Skills the JD wants that your resume doesn't mention</h4><div class="tag-row">${renderTagRow(jd.missing_skills, "tag-missing")}</div></div>`;
    }
    return html;
  }

  function renderTrending(data) {
    const trending = data.trending_skills || [];
    if (trending.length === 0) {
      return `<p class="empty-note">No trending-skill data for this role yet, or you already have all of them covered.</p>`;
    }
    return `<p class="panel-intro">Skills currently in demand for ${escapeHtml(data.detected_role)} that aren't on your resume yet:</p>
      <div class="tag-row">${renderTagRow(trending, "tag-trending")}</div>`;
  }

  function renderRecruiterTips(data) {
    return (data.recruiter_tips || []).map((item) => `
      <div class="rec-row">
        <span class="rec-priority priority-recruiter">Tip</span>
        <div>
          <div class="rec-title">${escapeHtml(item.title)}</div>
          <div class="rec-message">${escapeHtml(item.message)}</div>
        </div>
      </div>
    `).join("");
  }

  function renderLearning(data) {
    const plan = data.learning_plan || [];
    if (plan.length === 0) {
      return `<p class="empty-note">Nothing to learn right now — your skills and certifications already cover this role well.</p>`;
    }
    let html = `<p class="panel-intro">Where to close your biggest gaps for ${escapeHtml(data.detected_role)}:</p>`;
    plan.forEach((item) => {
      const links = item.resources.map((r) =>
        `<a href="${r.url}" target="_blank" rel="noopener" class="learning-link">${escapeHtml(r.name)} ↗</a>`
      ).join("");
      html += `<div class="learning-item">
        <div class="learning-item-title">${escapeHtml(item.title)}</div>
        <div class="learning-item-reason">${escapeHtml(item.reason)}</div>
        <div class="learning-links">${links}</div>
      </div>`;
    });
    return html;
  }

  function renderWording(data) {
    const issues = data.writing_issues || [];
    if (issues.length === 0) {
      return `<p class="empty-note">No wording issues spotted — no weak openers, first-person pronouns, overlong bullets, or likely typos found.</p>`;
    }
    let html = `<p class="panel-intro">Click a line to jump to it in the editor on the left.</p>`;
    issues.forEach((issue) => {
      html += `<div class="wording-row" data-line="${issue.line_number}">
        <span class="wording-type wording-type-${escapeHtml(issue.type)}">${escapeHtml(issue.title)}</span>
        <div class="wording-body">
          <div class="wording-line">"${escapeHtml(issue.line_text)}"</div>
          <div class="wording-message">${escapeHtml(issue.message)}</div>
        </div>
        <button class="btn btn-ghost btn-small wording-jump" type="button">Edit this line →</button>
      </div>`;
    });
    return html;
  }

  function renderRecommendations(data) {
    return (data.recommendations || []).map((item) => `
      <div class="rec-row">
        <span class="rec-priority priority-${escapeHtml((item.priority || "").toLowerCase())}">${escapeHtml(item.priority)}</span>
        <div>
          <div class="rec-title">${escapeHtml(item.title)}</div>
          <div class="rec-message">${escapeHtml(item.message)}</div>
        </div>
      </div>
    `).join("");
  }

  function applyResult(data) {
    const previousScore = parseInt(scoreValue.textContent, 10) || 0;
    const newScore = data.ats_score;
    const diff = newScore - previousScore;

    scoreValue.textContent = newScore;
    gradeValue.textContent = data.grade;
    healthValue.textContent = `${data.resume_health}%`;
    interviewValue.textContent = data.interview_readiness;
    if (wordCountEl) wordCountEl.textContent = data.word_count;
    const domainEl = document.getElementById("domainValue");
    if (domainEl) domainEl.textContent = `${data.domain} · ${data.detected_role}`;

    const recruiterScoreEl = document.getElementById("recruiterScoreValue");
    const recruiterLabelEl = document.getElementById("recruiterScoreLabel");
    if (recruiterScoreEl && data.recruiter_score) {
      recruiterScoreEl.textContent = data.recruiter_score.score;
      recruiterLabelEl.textContent = data.recruiter_score.label;
    }

    if (diff !== 0) {
      scoreDelta.textContent = diff > 0 ? `+${diff}` : `${diff}`;
      scoreDelta.className = "score-delta " + (diff > 0 ? "is-up" : "is-down");
    } else {
      scoreDelta.textContent = "";
      scoreDelta.className = "score-delta";
    }

    document.getElementById("breakdownList").innerHTML = renderBreakdown(data);
    document.getElementById("recruiterBreakdownList").innerHTML = renderRecruiterBreakdown(data);
    document.getElementById("rejectionContent").innerHTML = renderRejection(data);
    document.getElementById("skillsContent").innerHTML = renderSkills(data);
    document.getElementById("sectionsContent").innerHTML = renderSections(data);
    document.getElementById("careerContent").innerHTML = renderCareer(data);
    document.getElementById("jdContent").innerHTML = renderJd(data);
    document.getElementById("trendingContent").innerHTML = renderTrending(data);
    document.getElementById("learningContent").innerHTML = renderLearning(data);
    document.getElementById("recommendationsContent").innerHTML = renderRecommendations(data);
    document.getElementById("wordingContent").innerHTML = renderWording(data);
    document.getElementById("recruiterContent").innerHTML = renderRecruiterTips(data);
  }

  // ---------------------------------------------------------
  // "Edit this line" — jumps to the flagged line in the resume
  // editor and selects it, so the person can fix it right there.
  // Uses event delegation since wording rows are re-rendered on re-score.
  // ---------------------------------------------------------

  function jumpToLine(lineNumber) {
    const resumeTab = document.querySelector('[data-editor-tab="resume"]');
    if (resumeTab) resumeTab.click();

    const lines = resumeText.value.split("\n");
    let start = 0;
    for (let i = 0; i < lineNumber - 1 && i < lines.length; i++) {
      start += lines[i].length + 1;
    }
    const lineLength = (lines[lineNumber - 1] || "").length;

    resumeText.focus();
    resumeText.setSelectionRange(start, start + lineLength);

    const lineHeight = parseInt(getComputedStyle(resumeText).lineHeight, 10) || 20;
    resumeText.scrollTop = Math.max(0, (lineNumber - 6) * lineHeight);
  }

  document.addEventListener("click", (e) => {
    const row = e.target.closest(".wording-row");
    if (!row) return;
    const lineNumber = parseInt(row.getAttribute("data-line"), 10);
    if (lineNumber) jumpToLine(lineNumber);
  });

  // ---------------------------------------------------------
  // Re-score button
  // ---------------------------------------------------------

  async function rescore() {
    if (window.ResumeIQTrack) window.ResumeIQTrack("rescore_clicked");
    recalcStatus.textContent = "Recalculating…";
    recalcStatus.classList.add("is-recalculating");
    rescoreBtn.disabled = true;
    const originalLabel = rescoreBtn.textContent;
    rescoreBtn.textContent = "Scoring…";

    try {
      const res = await fetch("/rescore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: resumeText.value,
          jd_text: jdText ? jdText.value : "",
        }),
      });

      const payload = await res.json();

      if (!res.ok) {
        throw new Error(payload.error || "Something went wrong while re-scoring.");
      }

      applyResult(payload.data);
      recalcStatus.textContent = "ATS score · updated";
    } catch (err) {
      recalcStatus.textContent = err.message || "Couldn't re-score. Try again.";
    } finally {
      recalcStatus.classList.remove("is-recalculating");
      rescoreBtn.disabled = false;
      rescoreBtn.textContent = originalLabel;
    }
  }

  rescoreBtn.addEventListener("click", rescore);

  // Keyboard shortcut: Cmd/Ctrl+Enter re-scores from either textarea
  [resumeText, jdText].forEach((el) => {
    if (!el) return;
    el.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        rescore();
      }
    });
  });
})();
