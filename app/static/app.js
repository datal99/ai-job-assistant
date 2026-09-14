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
let pdfSupported = false;

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

document.addEventListener("click", (event) => {
  const unavailablePdfLink = event.target.closest("a.unavailable");
  if (!unavailablePdfLink) return;

  event.preventDefault();
  masterMessage.hidden = false;
  masterMessage.className = "inline-message error";
  masterMessage.textContent =
    "PDF export needs a LaTeX engine. Install Tectonic or another supported engine, then restart the app.";
});

jobPosting.addEventListener("input", () => {
  const count = jobPosting.value.length;
  characterCount.textContent = `${count.toLocaleString()} ${count === 1 ? "character" : "characters"}`;
});

const generationStages = [
  ["reading_job_posting", "Reading the job posting"],
  ["tailoring_resume", "Tailoring resume content"],
  ["rendering_resume", "Rendering and saving the resume"],
];

function showWorkingStatus(stage, elapsedSeconds) {
  let timer = statusPanel.querySelector("[data-working-timer]");
  if (!timer) {
    statusPanel.replaceChildren();
    timer = document.createElement("strong");
    timer.dataset.workingTimer = "";

    const steps = document.createElement("ol");
    steps.className = "generation-steps";
    generationStages.forEach(([stageName, label]) => {
      const item = document.createElement("li");
      item.dataset.stage = stageName;
      item.textContent = label;
      steps.append(item);
    });
    statusPanel.append(timer, steps);
  }

  timer.textContent = `Working for ${elapsedSeconds} ${elapsedSeconds === 1 ? "second" : "seconds"}...`;
  const activeIndex = generationStages.findIndex(([stageName]) => stageName === stage);
  statusPanel.querySelectorAll(".generation-steps li").forEach((item, index) => {
    item.classList.toggle("complete", stage === "complete" || index < activeIndex);
    item.classList.toggle("active", index === activeIndex);
  });
}

async function waitForGeneration(jobId, startedAt, onProgress) {
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
    showWorkingStatus(job.stage, elapsed);

    if (job.status === "completed") return { ...job, elapsed };
    if (job.status === "failed") {
      throw new Error(job.error || "The resume could not be generated.");
    }

    await new Promise((resolve) => setTimeout(resolve, 750));
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  generateButton.disabled = true;
  generateButton.textContent = "Tailoring resume...";
  statusPanel.hidden = false;
  statusPanel.className = "status loading";
  const startedAt = Date.now();
  let currentStage = "queued";
  showWorkingStatus(currentStage, 0);
  const timer = window.setInterval(() => {
    showWorkingStatus(
      currentStage,
      Math.floor((Date.now() - startedAt) / 1000),
    );
  }, 1000);

  try {
    const response = await fetch("/resumes/tailor/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_posting: jobPosting.value.trim() }),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "The resume could not be generated. Please try again.");
    }
    const job = await waitForGeneration(
      result.job_id,
      startedAt,
      (stage) => { currentStage = stage; },
    );
    currentStage = job.stage;
    const generatedResume = job.result;
    const downloadUrl = `/resumes/generated/${encodeURIComponent(generatedResume.filename)}`;
    statusPanel.className = "status success";
    statusPanel.replaceChildren();

    const heading = document.createElement("strong");
    heading.textContent = `Completed in ${job.elapsed} ${job.elapsed === 1 ? "second" : "seconds"}.`;
    const detail = document.createElement("span");
    detail.textContent = `${generatedResume.job_title} at ${generatedResume.company} is ready.`;
    const actions = document.createElement("div");
    actions.className = "file-actions result-actions";
    const links = [
      ["View LaTeX", `${downloadUrl}/latex`, true],
      ["Download LaTeX", `${downloadUrl}/latex?download=true`, false],
      ["View PDF", `${downloadUrl}/pdf`, true],
      ["Download PDF", `${downloadUrl}/pdf?download=true`, false],
    ];

    links.forEach(([label, href, newTab]) => {
      const link = document.createElement("a");
      link.href = href;
      link.textContent = label;
      if (newTab) link.target = "_blank";
      if (label.includes("PDF") && !pdfSupported) {
        link.classList.add("unavailable");
        link.title = "Install a LaTeX engine to enable PDF export.";
      }
      actions.append(link);
    });

    statusPanel.append(heading, detail, actions);
  } catch (error) {
    statusPanel.className = "status error";
    statusPanel.textContent = error.message;
  } finally {
    window.clearInterval(timer);
    generateButton.disabled = false;
    generateButton.textContent = "Generate tailored resume";
  }
});

loadMasterStatus();
