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
  ["summary_focus", "Adjust the professional summary"],
  ["experience_emphasis", "Emphasize different experience"],
  ["project_selection", "Reconsider project selection"],
  ["tone_and_clarity", "Improve tone and clarity"],
  ["preserve_source_detail", "Preserve more master-resume detail"],
  ["role_alignment", "Strengthen alignment with the role"],
  ["application_specificity", "Make the application more specific"],
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
  const accordion = document.createElement("section");
  accordion.className = "retry-accordion";
  const heading = document.createElement("h3");
  heading.className = "retry-accordion-heading";
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "retry-accordion-trigger";
  trigger.id = `retry-trigger-${sourceJobId}`;
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-controls", `retry-panel-${sourceJobId}`);
  const triggerLabel = document.createElement("span");
  triggerLabel.textContent = "Try another revision";
  const accordionIcon = document.createElement("span");
  accordionIcon.className = "retry-accordion-icon";
  accordionIcon.setAttribute("aria-hidden", "true");
  trigger.append(triggerLabel, accordionIcon);
  heading.append(trigger);

  const panel = document.createElement("div");
  panel.className = "retry-panel";
  panel.id = `retry-panel-${sourceJobId}`;
  panel.setAttribute("role", "region");
  panel.setAttribute("aria-labelledby", trigger.id);
  panel.hidden = true;
  const help = document.createElement("span");
  help.textContent = "Choose one or more changes for the next version.";

  const selectedReasons = new Set();
  const multiselect = document.createElement("div");
  multiselect.className = "revision-multiselect";
  const selectTrigger = document.createElement("div");
  selectTrigger.className = "revision-select-trigger";
  selectTrigger.setAttribute("role", "combobox");
  selectTrigger.tabIndex = 0;
  selectTrigger.setAttribute("aria-haspopup", "listbox");
  selectTrigger.setAttribute("aria-expanded", "false");
  selectTrigger.setAttribute("aria-controls", `revision-listbox-${sourceJobId}`);
  const selectedLabel = document.createElement("span");
  selectedLabel.textContent = "Select revision reasons";
  const selectIcon = document.createElement("span");
  selectIcon.className = "revision-select-icon";
  selectIcon.setAttribute("aria-hidden", "true");
  selectTrigger.append(selectedLabel, selectIcon);

  const listbox = document.createElement("div");
  listbox.className = "revision-listbox";
  listbox.id = `revision-listbox-${sourceJobId}`;
  listbox.setAttribute("role", "listbox");
  listbox.setAttribute("aria-multiselectable", "true");
  listbox.tabIndex = -1;
  listbox.hidden = true;

  function updateSelectedLabel() {
    const labels = revisionReasons
      .filter(([value]) => selectedReasons.has(value))
      .map(([, label]) => label);
    if (!labels.length) {
      selectedLabel.textContent = "Select revision reasons";
    } else if (labels.length === 1) {
      [selectedLabel.textContent] = labels;
    } else {
      selectedLabel.textContent = `${labels[0]} + ${labels.length - 1} more`;
    }
  }

  function toggleOption(option) {
    const value = option.dataset.value;
    const selected = !selectedReasons.has(value);
    if (selected) selectedReasons.add(value);
    else selectedReasons.delete(value);
    option.setAttribute("aria-selected", String(selected));
    updateSelectedLabel();
  }

  revisionReasons.forEach(([value, label], index) => {
    const option = document.createElement("div");
    option.id = `revision-option-${sourceJobId}-${index}`;
    option.className = "revision-option";
    option.dataset.value = value;
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", "false");
    option.tabIndex = index === 0 ? 0 : -1;
    const optionLabel = document.createElement("span");
    optionLabel.textContent = label;
    const check = document.createElement("span");
    check.className = "revision-option-check";
    check.setAttribute("aria-hidden", "true");
    check.textContent = "✓";
    option.append(optionLabel, check);
    option.addEventListener("click", () => toggleOption(option));
    listbox.append(option);
  });

  function setListboxOpen(open, focusOption = false) {
    selectTrigger.setAttribute("aria-expanded", String(open));
    listbox.hidden = !open;
    if (open && focusOption) {
      listbox.querySelector('[role="option"]')?.focus();
    }
  }

  selectTrigger.addEventListener("click", () => {
    setListboxOpen(selectTrigger.getAttribute("aria-expanded") !== "true", true);
  });
  selectTrigger.addEventListener("keydown", (event) => {
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      setListboxOpen(true, true);
    }
  });
  listbox.addEventListener("keydown", (event) => {
    const options = Array.from(listbox.querySelectorAll('[role="option"]'));
    const currentIndex = options.indexOf(document.activeElement);
    let nextIndex = currentIndex;
    if (event.key === "ArrowDown") nextIndex = Math.min(options.length - 1, currentIndex + 1);
    else if (event.key === "ArrowUp") nextIndex = Math.max(0, currentIndex - 1);
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = options.length - 1;
    else if (["Enter", " "].includes(event.key)) {
      event.preventDefault();
      toggleOption(document.activeElement);
      return;
    } else if (event.key === "Escape") {
      event.preventDefault();
      setListboxOpen(false);
      selectTrigger.focus();
      return;
    } else {
      return;
    }
    event.preventDefault();
    options.forEach((option, index) => { option.tabIndex = index === nextIndex ? 0 : -1; });
    options[nextIndex].focus();
  });
  multiselect.append(selectTrigger, listbox);

  const retryMessage = document.createElement("span");
  retryMessage.className = "retry-message";
  retryMessage.hidden = true;
  const retryButton = document.createElement("button");
  retryButton.type = "button";
  retryButton.className = "retry-button";
  retryButton.textContent = "Generate revised version";
  retryButton.addEventListener("click", async () => {
    const selected = Array.from(selectedReasons);
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

  trigger.addEventListener("click", () => {
    const expanded = trigger.getAttribute("aria-expanded") !== "true";
    trigger.setAttribute("aria-expanded", String(expanded));
    panel.hidden = !expanded;
    if (!expanded) setListboxOpen(false);
  });

  panel.append(help, multiselect, retryMessage, retryButton);
  accordion.append(heading, panel);
  statusPanel.append(accordion);
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
