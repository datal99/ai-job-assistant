const form = document.querySelector("#resume-form");
const jobPosting = document.querySelector("#job-posting");
const characterCount = document.querySelector("#character-count");
const generateButton = document.querySelector("#generate-button");
const statusPanel = document.querySelector("#status");
const masterStatus = document.querySelector("#master-status");
const masterFileActions = document.querySelector("#master-file-actions");
const masterResumeFile = document.querySelector("#master-resume-file");
const uploadLabel = document.querySelector("#upload-label");
const masterMessage = document.querySelector("#master-message");
const coverLetterStatus = document.querySelector("#cover-letter-status");
const coverLetterFileActions = document.querySelector("#cover-letter-file-actions");
const masterCoverLetterFile = document.querySelector("#master-cover-letter-file");
const coverLetterUploadLabel = document.querySelector("#cover-letter-upload-label");
const coverLetterMessage = document.querySelector("#cover-letter-message");
const includeCoverLetter = document.querySelector("#include-cover-letter");
const coverLetterOptionNote = document.querySelector("#cover-letter-option-note");
let pdfSupported = false;
let coverLetterReady = false;

function updateGenerateButtonLabel() {
  generateButton.textContent = includeCoverLetter.checked
    ? "Generate resume + cover letter"
    : "Generate tailored resume";
}

async function loadMasterStatus() {
  try {
    const response = await fetch("/resumes/master");
    if (!response.ok) throw new Error("Could not check the master resume.");

    const result = await response.json();
    pdfSupported = result.pdf_supported;
    masterFileActions.hidden = !result.exists;
    uploadLabel.textContent = result.exists ? "Replace master resume" : "Upload master resume";
    const resumeStatus = result.exists
      ? `${result.filename} is ready to use.`
      : "Upload your LaTeX master resume before generating tailored versions.";
    masterStatus.textContent = pdfSupported
      ? resumeStatus
      : `${resumeStatus} Install a LaTeX engine to enable PDF viewing and downloads.`;

    document.querySelectorAll(".pdf-action").forEach((link) => {
      link.classList.toggle("unavailable", !pdfSupported);
      link.title = pdfSupported
        ? ""
        : "Install a LaTeX distribution to enable PDF export.";
    });
  } catch (error) {
    masterStatus.textContent = error.message;
  }
}

async function loadCoverLetterStatus() {
  try {
    const response = await fetch("/cover-letters/master");
    if (!response.ok) throw new Error("Could not check the cover letter template.");

    const result = await response.json();
    coverLetterReady = result.exists;
    pdfSupported = result.pdf_supported;
    coverLetterFileActions.hidden = !result.exists;
    coverLetterUploadLabel.textContent = result.exists
      ? "Replace master cover letter"
      : "Upload master cover letter";
    coverLetterStatus.textContent = result.exists
      ? `${result.filename} is ready to use.`
      : "Upload a self-contained LaTeX cover letter template to enable generation.";
    includeCoverLetter.disabled = !result.exists;
    if (!result.exists) includeCoverLetter.checked = false;
    coverLetterOptionNote.textContent = result.exists
      ? "Uses the same job posting and master resume."
      : "Requires a master cover letter template.";
    updateGenerateButtonLabel();

    document.querySelectorAll(".pdf-action").forEach((link) => {
      link.classList.toggle("unavailable", !pdfSupported);
      link.title = pdfSupported
        ? ""
        : "Install a LaTeX distribution to enable PDF export.";
    });
  } catch (error) {
    coverLetterStatus.textContent = error.message;
    includeCoverLetter.disabled = true;
  }
}

masterResumeFile.addEventListener("change", async () => {
  const [file] = masterResumeFile.files;
  if (!file) return;

  masterMessage.hidden = false;
  masterMessage.className = "inline-message loading";
  masterMessage.textContent = "Validating and saving the master resume...";
  masterResumeFile.disabled = true;

  try {
    const response = await fetch("/resumes/master", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, content: await file.text() }),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "The master resume could not be uploaded.");
    }

    masterMessage.className = "inline-message success";
    masterMessage.textContent = "Master resume saved and tailoring template refreshed.";
    await loadMasterStatus();
  } catch (error) {
    masterMessage.className = "inline-message error";
    masterMessage.textContent = error.message;
  } finally {
    masterResumeFile.disabled = false;
    masterResumeFile.value = "";
  }
});

masterCoverLetterFile.addEventListener("change", async () => {
  const [file] = masterCoverLetterFile.files;
  if (!file) return;

  coverLetterMessage.hidden = false;
  coverLetterMessage.className = "inline-message loading";
  coverLetterMessage.textContent = "Validating and saving the master cover letter...";
  masterCoverLetterFile.disabled = true;

  try {
    const response = await fetch("/cover-letters/master", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, content: await file.text() }),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "The master cover letter could not be uploaded.");
    }

    coverLetterMessage.className = "inline-message success";
    coverLetterMessage.textContent = "Master cover letter saved and ready to tailor.";
    await loadCoverLetterStatus();
  } catch (error) {
    coverLetterMessage.className = "inline-message error";
    coverLetterMessage.textContent = error.message;
  } finally {
    masterCoverLetterFile.disabled = false;
    masterCoverLetterFile.value = "";
  }
});

includeCoverLetter.addEventListener("change", updateGenerateButtonLabel);

document.addEventListener("click", (event) => {
  const unavailablePdfLink = event.target.closest("a.unavailable");
  if (!unavailablePdfLink) return;

  event.preventDefault();
  const messagePanel = unavailablePdfLink.closest(".master-panel")
    ?.querySelector(".inline-message") || statusPanel;
  messagePanel.hidden = false;
  messagePanel.className = messagePanel === statusPanel
    ? "status error"
    : "inline-message error";
  messagePanel.textContent =
    "PDF export needs a LaTeX engine. Install Tectonic or another supported engine, then restart the app.";
});

jobPosting.addEventListener("input", () => {
  const count = jobPosting.value.length;
  characterCount.textContent = `${count.toLocaleString()} ${count === 1 ? "character" : "characters"}`;
});

const generationStages = [
  ["reading_job_posting", "Reading the job posting"],
  ["tailoring_resume", "Tailoring resume content"],
  ["validating_resume", "Checking experience against the master resume"],
  ["rendering_resume", "Rendering and saving the resume"],
  ["tailoring_cover_letter", "Writing the cover letter"],
  ["rendering_cover_letter", "Rendering and saving the cover letter"],
];

function showWorkingStatus(stage, elapsedSeconds, withCoverLetter) {
  const visibleStages = withCoverLetter
    ? generationStages
    : generationStages.slice(0, 4);
  let timer = statusPanel.querySelector("[data-working-timer]");
  if (!timer) {
    statusPanel.replaceChildren();
    timer = document.createElement("strong");
    timer.dataset.workingTimer = "";

    const steps = document.createElement("ol");
    steps.className = "generation-steps";
    visibleStages.forEach(([stageName, label]) => {
      const item = document.createElement("li");
      item.dataset.stage = stageName;
      item.textContent = label;
      steps.append(item);
    });
    statusPanel.append(timer, steps);
  }

  timer.textContent = `Working for ${elapsedSeconds} ${elapsedSeconds === 1 ? "second" : "seconds"}...`;
  const activeIndex = visibleStages.findIndex(([stageName]) => stageName === stage);
  statusPanel.querySelectorAll(".generation-steps li").forEach((item, index) => {
    item.classList.toggle("complete", stage === "complete" || index < activeIndex);
    item.classList.toggle("active", index === activeIndex);
  });
}

async function waitForGeneration(
  jobId,
  startedAt,
  withCoverLetter,
  onProgress,
) {
  while (true) {
    const response = await fetch(`/resumes/tailor/jobs/${jobId}`);
    const job = await response.json();
    if (!response.ok) {
      throw new Error(job.detail || "The generation status could not be loaded.");
    }

    const elapsed = Math.max(
      job.elapsed_seconds,
      Math.floor((Date.now() - startedAt) / 1000),
    );
    onProgress(job.stage);
    showWorkingStatus(job.stage, elapsed, withCoverLetter);

    if (job.status === "completed") return { ...job, elapsed };
    if (job.status === "failed") {
      throw new Error(job.error || "The resume could not be generated.");
    }

    await new Promise((resolve) => setTimeout(resolve, 750));
  }
}

const revisionReasons = [
  ["summary_focus", "Refocus the professional summary"],
  ["emphasize_programming", "Emphasize programming work"],
  ["project_selection", "Choose more relevant projects"],
  ["reduce_keyword_density", "Make the writing less keyword-heavy"],
  ["preserve_source_detail", "Preserve more master-resume detail"],
  ["strengthen_ai_relevance", "Highlight relevant AI work"],
  ["cover_letter_specificity", "Make the cover letter more specific"],
];

function addResultFile(label, baseUrl) {
  const group = document.createElement("div");
  group.className = "result-file";
  const fileLabel = document.createElement("span");
  fileLabel.textContent = label;
  const actions = document.createElement("div");
  actions.className = "file-actions result-actions";
  [
    ["View LaTeX", `${baseUrl}/latex`, true],
    ["Download LaTeX", `${baseUrl}/latex?download=true`, false],
    ["View PDF", `${baseUrl}/pdf`, true],
    ["Download PDF", `${baseUrl}/pdf?download=true`, false],
  ].forEach(([linkLabel, href, newTab]) => {
    const link = document.createElement("a");
    link.href = href;
    link.textContent = linkLabel;
    if (newTab) link.target = "_blank";
    if (linkLabel.includes("PDF") && !pdfSupported) {
      link.classList.add("unavailable");
      link.title = "Install a LaTeX engine to enable PDF export.";
    }
    actions.append(link);
  });
  group.append(fileLabel, actions);
  statusPanel.append(group);
}

function addRetryControls(sourceJobId, withCoverLetter) {
  const panel = document.createElement("div");
  panel.className = "retry-panel";
  const heading = document.createElement("strong");
  heading.textContent = "Try another revision";
  const help = document.createElement("span");
  help.textContent = "Choose one or more changes for the next version.";
  const choices = document.createElement("div");
  choices.className = "revision-options";

  revisionReasons.forEach(([value, label]) => {
    const choice = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = value;
    const text = document.createElement("span");
    text.textContent = label;
    choice.append(input, text);
    choices.append(choice);
  });

  const retryMessage = document.createElement("span");
  retryMessage.className = "retry-message";
  retryMessage.hidden = true;
  const retryButton = document.createElement("button");
  retryButton.type = "button";
  retryButton.className = "retry-button";
  retryButton.textContent = "Generate revised version";
  retryButton.addEventListener("click", async () => {
    const selected = Array.from(
      choices.querySelectorAll("input:checked"),
      (input) => input.value,
    );
    if (!selected.length) {
      retryMessage.hidden = false;
      retryMessage.textContent = "Select at least one revision reason.";
      return;
    }

    retryButton.disabled = true;
    retryMessage.hidden = true;
    try {
      const response = await fetch(`/resumes/tailor/jobs/${sourceJobId}/retry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision_reasons: selected }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "The revised version could not be started.");
      }
      await monitorGeneration(result.job_id, withCoverLetter);
    } catch (error) {
      retryButton.disabled = false;
      retryMessage.hidden = false;
      retryMessage.textContent = error.message;
    }
  });

  panel.append(heading, help, choices, retryMessage, retryButton);
  statusPanel.append(panel);
}

function renderCompletedGeneration(job, sourceJobId, withCoverLetter) {
  const generatedResume = job.result;
  statusPanel.className = "status success";
  statusPanel.replaceChildren();
  const heading = document.createElement("strong");
  heading.textContent = `Completed in ${job.elapsed} ${job.elapsed === 1 ? "second" : "seconds"}.`;
  const detail = document.createElement("span");
  detail.textContent = `${generatedResume.job_title} at ${generatedResume.company} is ready.`;
  statusPanel.append(heading, detail);
  addResultFile(
    "Tailored resume",
    `/resumes/generated/${encodeURIComponent(generatedResume.filename)}`,
  );
  if (generatedResume.cover_letter_filename) {
    addResultFile(
      "Cover letter",
      `/cover-letters/generated/${encodeURIComponent(generatedResume.cover_letter_filename)}`,
    );
  }
  addRetryControls(sourceJobId, withCoverLetter);
}

function renderFailedGeneration(message, sourceJobId, withCoverLetter) {
  statusPanel.className = "status error";
  statusPanel.replaceChildren();
  const errorMessage = document.createElement("span");
  errorMessage.textContent = message;
  statusPanel.append(errorMessage);
  addRetryControls(sourceJobId, withCoverLetter);
}

async function monitorGeneration(jobId, withCoverLetter) {
  statusPanel.hidden = false;
  statusPanel.className = "status loading";
  const startedAt = Date.now();
  let currentStage = "queued";
  showWorkingStatus(currentStage, 0, withCoverLetter);
  const timer = window.setInterval(() => {
    showWorkingStatus(
      currentStage,
      Math.floor((Date.now() - startedAt) / 1000),
      withCoverLetter,
    );
  }, 1000);

  try {
    const job = await waitForGeneration(
      jobId,
      startedAt,
      withCoverLetter,
      (stage) => { currentStage = stage; },
    );
    renderCompletedGeneration(job, jobId, withCoverLetter);
  } catch (error) {
    renderFailedGeneration(error.message, jobId, withCoverLetter);
  } finally {
    window.clearInterval(timer);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const withCoverLetter = includeCoverLetter.checked && coverLetterReady;
  generateButton.disabled = true;
  generateButton.textContent = withCoverLetter
    ? "Preparing application..."
    : "Tailoring resume...";

  try {
    const response = await fetch("/resumes/tailor/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_posting: jobPosting.value.trim(),
        include_cover_letter: withCoverLetter,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "The resume could not be generated. Please try again.");
    }
    await monitorGeneration(result.job_id, withCoverLetter);
  } catch (error) {
    statusPanel.hidden = false;
    statusPanel.className = "status error";
    statusPanel.textContent = error.message;
  } finally {
    generateButton.disabled = false;
    updateGenerateButtonLabel();
  }
});

loadMasterStatus();
loadCoverLetterStatus();
updateGenerateButtonLabel();
