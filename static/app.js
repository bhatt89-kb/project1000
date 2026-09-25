"use strict";

/**
 * Legal Document Assistant - Client-side Application
 * Handles document upload, analysis rendering, Q&A interactions, and comparison
 */

const SUMMARY_LABELS = {
  type: "Document type",
  pages: "Pages",
  duration: "Duration",
  monthly_rent: "Monthly rent",
  security_deposit: "Security deposit",
  notice_period: "Notice period",
};

let documentId = null;
let secondDocumentId = null;

// === Utility Functions ===

function el(tag, text = "") {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}

function clauseLabel(clause, page) {
  return `${clause ? `Clause ${clause}` : "Unnumbered section"}, page ${page}`;
}

async function requestJSON(url, options) {
  const response = await fetch(url, options);
  let data = {};
  try {
    data = await response.json();
  } catch {
    // Non-JSON error pages fall through to the generic message below.
  }
  if (!response.ok) {
    throw new Error(data.error || `Request failed (status ${response.status}).`);
  }
  return data;
}

// === Progress Management ===

function showProgress(label, percentage) {
  const container = document.getElementById("progress-container");
  const labelEl = document.getElementById("progress-label");
  const bar = document.getElementById("progress-bar");
  const percentEl = document.getElementById("progress-percentage");
  
  container.classList.add("active");
  labelEl.textContent = label;
  bar.style.width = percentage + "%";
  percentEl.textContent = percentage + "%";
}

function hideProgress() {
  const container = document.getElementById("progress-container");
  container.classList.remove("active");
}

// === Error Management ===

function showError(title, message, showActions = true) {
  const container = document.getElementById("error-container");
  const titleEl = document.getElementById("error-title");
  const messageEl = document.getElementById("error-message");
  
  titleEl.textContent = title;
  messageEl.textContent = message;
  container.classList.add("active");
  
  // Hide after 10 seconds
  setTimeout(() => {
    container.classList.remove("active");
  }, 10000);
}

function hideError() {
  const container = document.getElementById("error-container");
  container.classList.remove("active");
}

// === Tab Management ===

function initTabs() {
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Remove active class from all tabs
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      
      // Hide all tab contents
      document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
      });
      
      // Activate clicked tab
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      
      // Show corresponding content
      const tabId = tab.getAttribute('data-tab');
      const content = document.getElementById(`tab-${tabId}`);
      if (content) {
        content.classList.add('active');
      }
    });
  });
}

function renderSummary(summary) {
  const list = document.getElementById("summary");
  list.replaceChildren();
  for (const [key, label] of Object.entries(SUMMARY_LABELS)) {
    list.append(el("dt", label), el("dd", String(summary[key])));
  }
}

function renderFindings(findings) {
  const list = document.getElementById("findings");
  list.replaceChildren();
  
  if (findings.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.innerHTML = `
      <div class="empty-state-icon">🎉</div>
      <div class="empty-state-title">No Issues Found</div>
      <div class="empty-state-description">
        Great news! No clauses matched our review categories. 
        However, always read the entire document carefully.
      </div>
    `;
    list.append(emptyState);
    return;
  }
  
  for (const finding of findings) {
    const item = el("li");
    const priorityBadge = document.createElement("span");
    priorityBadge.className = finding.risk_score >= 8 ? "risk-badge risk-high" : 
                             finding.risk_score >= 6 ? "risk-badge risk-medium" : 
                             "risk-badge risk-low";
    priorityBadge.textContent = `${finding.label} (Risk: ${finding.risk_score}/10)`;
    
    item.append(
      priorityBadge,
      el("strong", finding.category.charAt(0).toUpperCase() + finding.category.slice(1)),
      el("p", finding.explanation),
      el("p", clauseLabel(finding.clause, finding.page)),
      el("blockquote", finding.excerpt),
    );
    list.append(item);
  }
}

function renderChecklist(items) {
  const list = document.getElementById("checklist");
  list.replaceChildren();
  for (const text of items) {
    const item = el("li");
    const label = el("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    label.append(box, document.createTextNode(` ${text}`));
    item.append(label);
    list.append(item);
  }
}

function renderAnswer(data) {
  const box = document.getElementById("answer");
  box.replaceChildren();
  
  if (data.matches.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.innerHTML = `
      <div class="empty-state-icon">🔍</div>
      <div class="empty-state-title">No Match Found</div>
      <div class="empty-state-description">
        ${data.message}<br>
        Try rephrasing your question or using different keywords.
      </div>
    `;
    box.append(emptyState);
    return;
  }
  
  const successBanner = document.createElement("div");
  successBanner.className = "success-banner";
  successBanner.innerHTML = `
    <span class="success-icon">✅</span>
    <span>Found ${data.matches.length} relevant passage(s) from your document:</span>
  `;
  box.append(successBanner);
  
  for (const match of data.matches) {
    const metaEl = el("p", clauseLabel(match.clause, match.page));
    metaEl.className = "answer-meta";
    box.append(metaEl, el("blockquote", match.text));
  }
}

document.getElementById("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  const button = event.target.querySelector('button');
  const buttonText = button.querySelector('.button-text');
  
  // Show loading state
  status.textContent = "🔄 Analyzing your document...";
  status.className = "loading";
  button.disabled = true;
  buttonText.innerHTML = '<span class="loading-spinner"></span>Analyzing...';
  
  try {
    const data = await requestJSON("/api/upload", { method: "POST", body: new FormData(event.target) });
    documentId = data.id;
    renderSummary(data.summary);
    renderFindings(data.findings);
    renderChecklist(data.checklist);
    results.hidden = false;
    status.textContent = "✅ Analysis complete! Review the results below.";
    status.className = "success";
    results.focus();
  } catch (error) {
    status.textContent = "❌ " + error.message;
    status.className = "error";
  } finally {
    button.disabled = false;
    buttonText.textContent = "Analyze Document";
  }
});

document.getElementById("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = document.getElementById("question").value.trim();
  const button = event.target.querySelector('button');
  const buttonText = button.querySelector('.button-text');
  const answerBox = document.getElementById("answer");
  
  if (!question) {
    answerBox.innerHTML = '<p style="color: var(--danger);">⚠️ Please enter a question.</p>';
    return;
  }
  
  // Show loading state
  button.disabled = true;
  buttonText.innerHTML = '<span class="loading-spinner"></span>Searching...';
  answerBox.innerHTML = '<p style="color: var(--text-muted);">🔍 Searching your document...</p>';
  
  try {
    const data = await requestJSON("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: documentId, question }),
    });
    renderAnswer(data);
  } catch (error) {
    answerBox.replaceChildren(el("p", "❌ " + error.message));
  } finally {
    button.disabled = false;
    buttonText.textContent = "Get Answer";
  }
});

// New rendering functions for Phase 1 enhancements

function renderRiskAssessment(risk) {
  const container = document.getElementById("risk-assessment");
  container.replaceChildren();
  
  const levelClass = `risk-${risk.level.toLowerCase()}`;
  const badge = document.createElement("span");
  badge.className = `risk-badge ${levelClass}`;
  badge.textContent = `${risk.level} Risk`;
  
  container.append(badge);
  
  const stats = document.createElement("div");
  stats.className = "risk-stats";
  
  const scoreCard = document.createElement("div");
  scoreCard.className = "risk-stat";
  scoreCard.innerHTML = `<div class="risk-stat-value">${risk.score}</div><div class="risk-stat-label">Risk Score</div>`;
  
  const issuesCard = document.createElement("div");
  issuesCard.className = "risk-stat";
  issuesCard.innerHTML = `<div class="risk-stat-value">${risk.total_issues}</div><div class="risk-stat-label">Issues Found</div>`;
  
  const priorityCard = document.createElement("div");
  priorityCard.className = "risk-stat";
  priorityCard.innerHTML = `<div class="risk-stat-value">${risk.high_priority}</div><div class="risk-stat-label">High Priority</div>`;
  
  stats.append(scoreCard, issuesCard, priorityCard);
  container.append(stats);
}

function renderEntities(entities) {
  const container = document.getElementById("entities");
  container.replaceChildren();
  
  const grid = document.createElement("div");
  grid.className = "entity-grid";
  
  // Render each entity type
  const entityTypes = [
    { key: "dates", title: "📅 Important Dates", icon: "📅" },
    { key: "amounts", title: "💰 Financial Amounts", icon: "💰" },
    { key: "parties", title: "👥 Parties Mentioned", icon: "👥" },
    { key: "obligations", title: "📝 Key Obligations", icon: "📝" }
  ];
  
  for (const { key, title } of entityTypes) {
    const section = document.createElement("div");
    section.className = "entity-section";
    
    const titleEl = el("div", title);
    titleEl.className = "entity-title";
    section.append(titleEl);
    
    const list = document.createElement("ul");
    list.className = "entity-list";
    
    const items = entities[key] || [];
    if (items.length === 0) {
      const empty = el("li", "None found");
      empty.className = "entity-item";
      empty.style.color = "var(--text-muted)";
      list.append(empty);
    } else {
      for (const item of items) {
        const li = el("li", item);
        li.className = "entity-item";
        list.append(li);
      }
    }
    
    section.append(list);
    grid.append(section);
  }
  
  container.append(grid);
}

function renderComparison(comparison) {
  const container = document.getElementById("comparison-result");
  container.replaceChildren();
  
  // Summary comparison
  const summarySection = document.createElement("div");
  summarySection.innerHTML = "<h3 style='margin: 1.5rem 0 1rem; color: var(--primary);'>📊 Summary Comparison</h3>";
  
  const summaryGrid = document.createElement("div");
  summaryGrid.className = "comparison-grid";
  
  for (const [key, comp] of Object.entries(comparison.summary_comparison)) {
    const item1 = document.createElement("div");
    item1.className = comp.different ? "comparison-item comparison-different" : "comparison-item comparison-same";
    item1.innerHTML = `
      <div class="comparison-label">Document 1: ${key.replace(/_/g, " ")}</div>
      <div class="comparison-value">${comp.document1}</div>
    `;
    
    const item2 = document.createElement("div");
    item2.className = comp.different ? "comparison-item comparison-different" : "comparison-item comparison-same";
    item2.innerHTML = `
      <div class="comparison-label">Document 2: ${key.replace(/_/g, " ")}</div>
      <div class="comparison-value">${comp.document2}</div>
    `;
    
    summaryGrid.append(item1, item2);
  }
  
  summarySection.append(summaryGrid);
  container.append(summarySection);
  
  // Risk comparison
  const riskSection = document.createElement("div");
  riskSection.innerHTML = "<h3 style='margin: 1.5rem 0 1rem; color: var(--primary);'>⚠️ Risk Comparison</h3>";
  
  const riskGrid = document.createElement("div");
  riskGrid.className = "comparison-grid";
  
  const risk1 = document.createElement("div");
  risk1.className = "comparison-item";
  risk1.innerHTML = `
    <div class="comparison-label">Document 1</div>
    <div class="comparison-value">
      <span class="risk-badge risk-${comparison.risk_comparison.document1.level.toLowerCase()}">
        ${comparison.risk_comparison.document1.level} Risk
      </span><br>
      Score: ${comparison.risk_comparison.document1.score} | Issues: ${comparison.risk_comparison.document1.issues}
    </div>
  `;
  
  const risk2 = document.createElement("div");
  risk2.className = "comparison-item";
  risk2.innerHTML = `
    <div class="comparison-label">Document 2</div>
    <div class="comparison-value">
      <span class="risk-badge risk-${comparison.risk_comparison.document2.level.toLowerCase()}">
        ${comparison.risk_comparison.document2.level} Risk
      </span><br>
      Score: ${comparison.risk_comparison.document2.score} | Issues: ${comparison.risk_comparison.document2.issues}
    </div>
  `;
  
  riskGrid.append(risk1, risk2);
  riskSection.append(riskGrid);
  container.append(riskSection);
  
  // Differences
  if (comparison.differences.length > 0) {
    const diffSection = document.createElement("div");
    diffSection.innerHTML = "<h3 style='margin: 1.5rem 0 1rem; color: var(--warning);'>⚡ Key Differences</h3>";
    
    const diffList = document.createElement("ul");
    diffList.style.listStyle = "none";
    diffList.style.padding = "0";
    
    for (const diff of comparison.differences) {
      const li = document.createElement("li");
      li.style.background = "var(--bg-secondary)";
      li.style.padding = "1rem";
      li.style.borderRadius = "var(--radius)";
      li.style.marginBottom = "0.5rem";
      li.style.borderLeft = "4px solid var(--warning)";
      li.innerHTML = `<strong>${diff.description}</strong>`;
      diffList.append(li);
    }
    
    diffSection.append(diffList);
    container.append(diffSection);
  }
}

// Update main upload handler to render new sections with progress
document.getElementById("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  const button = event.target.querySelector('button');
  const buttonText = button.querySelector('.button-text');
  
  hideError();
  status.textContent = "🔄 Uploading document...";
  status.className = "loading";
  button.disabled = true;
  buttonText.innerHTML = '<span class="loading-spinner"></span>Analyzing...';
  
  // Simulate progress
  showProgress("Uploading document...", 0);
  setTimeout(() => showProgress("Extracting text...", 30), 300);
  setTimeout(() => showProgress("Analyzing clauses...", 60), 600);
  setTimeout(() => showProgress("Extracting entities...", 90), 900);
  
  try {
    const data = await requestJSON("/api/upload", { method: "POST", body: new FormData(event.target) });
    documentId = data.id;
    
    showProgress("Complete!", 100);
    
    // Render all sections
    if (data.risk_assessment) renderRiskAssessment(data.risk_assessment);
    renderSummary(data.summary);
    if (data.entities) renderEntities(data.entities);
    renderFindings(data.findings);
    renderChecklist(data.checklist);
    
    // Initialize tabs after content is loaded
    initTabs();
    
    results.hidden = false;
    status.textContent = "✅ Analysis complete! Review the results below.";
    status.className = "success";
    
    setTimeout(hideProgress, 1000);
    results.focus();
  } catch (error) {
    hideProgress();
    status.textContent = "❌ " + error.message;
    status.className = "error";
    showError("Upload Failed", error.message);
  } finally {
    button.disabled = false;
    buttonText.textContent = "Analyze Document";
  }
});

// Comparison upload handler
document.getElementById("compare-upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.target.querySelector('button');
  const buttonText = button.querySelector('.button-text');
  
  button.disabled = true;
  buttonText.innerHTML = '<span class="loading-spinner"></span>Comparing...';
  
  try {
    // Upload second document
    const uploadData = await requestJSON("/api/upload", { 
      method: "POST", 
      body: new FormData(event.target) 
    });
    secondDocumentId = uploadData.id;
    
    // Compare with first document
    const comparisonData = await requestJSON("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id1: documentId, id2: secondDocumentId }),
    });
    
    renderComparison(comparisonData);
  } catch (error) {
    const container = document.getElementById("comparison-result");
    container.innerHTML = `<p style="color: var(--danger);">❌ ${error.message}</p>`;
  } finally {
    button.disabled = false;
    buttonText.textContent = "Upload & Compare";
  }
});


// === Export Functionality ===

function exportReport() {
  if (!documentId) {
    showError("No Document", "Please upload a document first before exporting.");
    return;
  }
  
  // Open report in new window for printing/saving
  const reportUrl = `/api/export/${documentId}`;
  window.open(reportUrl, '_blank');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
});
