(function () {
  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("resumeInput");
  const title = document.getElementById("dropzoneTitle");
  const jdInput = document.getElementById("jdInput");
  const jdCount = document.getElementById("jdCharCount");
  const form = document.getElementById("analyzeForm");
  const analyzeBtn = document.getElementById("analyzeBtn");

  if (!dropzone) return; // not on this page

  function showFileName() {
    if (input.files && input.files.length > 0) {
      title.textContent = input.files[0].name;
    } else {
      title.textContent = "Drop your resume here";
    }
  }

  input.addEventListener("change", showFileName);

  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      input.files = files;
      showFileName();
    }
  });

  if (jdInput && jdCount) {
    const updateCount = () => { jdCount.textContent = jdInput.value.length; };
    jdInput.addEventListener("input", updateCount);
    updateCount();
  }

  if (form && analyzeBtn) {
    form.addEventListener("submit", () => {
      if (window.ResumeIQTrack) window.ResumeIQTrack("analyze_submitted");
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = "Analyzing…";
    });
  }
})();
