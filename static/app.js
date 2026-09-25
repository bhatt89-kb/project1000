"use strict";

/**
 * Legal Document Assistant - Client-side Application
 * Handles document upload, analysis rendering, and Q&A interactions
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

function el(tag, text = "") {
  const node = document.createElement(tag);
  node.textContent = text; // textContent keeps document text from being run as HTML
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
    list.append(el("li", "No clauses matched the review categories."));
    return;
  }
  for (const finding of findings) {
    const item = el("li");
    item.append(
      el("strong", `${finding.label}: ${finding.category}`),
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
    box.append(el("p", data.message));
    return;
  }
  box.append(el("p", "Most relevant passages from your document:"));
  for (const match of data.matches) {
    box.append(el("p", clauseLabel(match.clause, match.page)), el("blockquote", match.text));
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
