function showToast(message, ok = true) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.style.borderColor = ok ? "#166534" : "#991b1b";
  window.clearTimeout(showToast._timer);
  showToast._timer = window.setTimeout(() => toast.classList.add("hidden"), 3500);
}

async function postAction(url, body) {
  const options = {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      Accept: "application/json",
    },
  };
  if (body) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_err) {
    const hint = text.trim().startsWith("<!")
      ? "Server returned HTML instead of JSON (login page or crash). Re-login or check Flask logs."
      : `Invalid JSON response (${response.status}).`;
    throw new Error(hint);
  }
  if (!response.ok && !data.message) {
    throw new Error(`Request failed (${response.status})`);
  }
  return data;
}

function updateStatus(status) {
  const domeBadge = document.getElementById("dome-badge");
  const schedulerBadge = document.getElementById("scheduler-badge");
  const telescopeBadge = document.getElementById("telescope-badge");
  if (domeBadge) domeBadge.textContent = `Dome: ${status.dome}`;
  if (schedulerBadge) schedulerBadge.textContent = `Observing: ${status.scheduler}`;
  if (telescopeBadge) telescopeBadge.textContent = `Telescope: ${status.telescope_services || "unknown"}`;

  const stopQuestctl = document.getElementById("stop-questctl-btn");
  if (stopQuestctl) {
    const running = status.telescope_services === "running";
    const domeOpen = status.dome === "open" || status.dome === "opening";
    stopQuestctl.disabled = !running || domeOpen;
    if (!running) {
      stopQuestctl.title = "Start questctl before you can stop it";
    } else if (domeOpen) {
      stopQuestctl.title = "Close the dome (or stow) before stopping questctl";
    } else {
      stopQuestctl.removeAttribute("title");
    }
  }

  const openDome = document.getElementById("open-dome-btn");
  if (openDome) {
    const running = status.telescope_services === "running";
    openDome.disabled = !running;
    if (running) {
      openDome.removeAttribute("title");
    } else {
      openDome.title = "Start questctl first";
    }
  }

  Object.entries(status.pdu_outlets || {}).forEach(([outlet, state]) => {
    const card = document.querySelector(`.pdu-outlet[data-outlet="${outlet}"] .pdu-state`);
    if (card) card.textContent = state;
  });

  const mosaicMeta = document.getElementById("mosaic-meta");
  if (mosaicMeta && status.latest_mosaic) {
    mosaicMeta.textContent = `Latest mosaic: ${status.latest_mosaic}`;
  }
}

function refreshWebcam(camera) {
  const imageIds = {
    oil_pump: "oil-pump-image",
    tcs: "tcs-image",
    flux_meter: "flux-meter-image",
    dome: "dome-image",
    aux: "aux-image",
  };
  const metaIds = {
    oil_pump: "oil-pump-meta",
  };
  const image = document.getElementById(imageIds[camera]);
  if (!image) return Promise.resolve();

  return postAction(`/api/webcam/${camera}`)
    .then((data) => {
      showToast(data.message, data.ok);
      if (data.status) updateStatus(data.status);
      // Reload image after sync so the newest file is shown.
      image.src = `/api/webcam/${camera}/image?ts=${Date.now()}`;
      const meta = document.getElementById(metaIds[camera]);
      if (meta) {
        if (data.image_captured_at) {
          meta.textContent = `Captured: ${data.image_captured_at}`;
        } else {
          meta.textContent = data.ok ? "Captured: unknown" : "Captured: —";
        }
      }
      return data;
    })
    .catch((error) => {
      showToast(error.message || "Webcam refresh failed", false);
      throw error;
    });
}

function refreshMosaicImage() {
  const image = document.getElementById("mosaic-image");
  if (image) {
    image.src = `/api/mosaic/image?ts=${Date.now()}`;
  }
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action], button[data-webcam]");
  if (!button) return;

  try {
    if (button.dataset.webcam) {
      await refreshWebcam(button.dataset.webcam);
      return;
    }

    const action = button.dataset.action;
    const value = button.dataset.value;
    let url;

    if (action === "dome") {
      url = `/api/dome/${value}`;
    } else if (action === "telescope") {
      url = `/api/telescope/${value}`;
    } else if (action === "scheduler") {
      url = `/api/scheduler/${value}`;
    } else if (action === "pdu") {
      url = `/api/pdu/${button.dataset.outlet}/${value}`;
    } else {
      return;
    }

    const data = await postAction(url);
    showToast(data.message, data.ok);
    if (data.status) updateStatus(data.status);
  } catch (error) {
    showToast(error.message || "Action failed", false);
  }
});

document.getElementById("refresh-all-webcams")?.addEventListener("click", async () => {
  await Promise.all([
    refreshWebcam("dome"),
    refreshWebcam("aux"),
    refreshWebcam("flux_meter"),
    refreshWebcam("oil_pump"),
    refreshWebcam("tcs"),
  ]);
});

document.getElementById("mosaic-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prefix = document.getElementById("mosaic-prefix")?.value?.trim();
  if (!prefix) {
    showToast("Exposure prefix is required.", false);
    return;
  }

  try {
    const data = await postAction("/api/mosaic/generate", { prefix });
    showToast(data.message, data.ok);
    if (data.status) updateStatus(data.status);
    if (data.ok) refreshMosaicImage();
  } catch (error) {
    showToast(error.message || "Mosaic generation failed", false);
  }
});

const refreshSeconds = window.LS4_GUI?.refreshSeconds || 30;
window.setInterval(() => {
  refreshWebcam("dome");
  refreshWebcam("aux");
  refreshWebcam("flux_meter");
  refreshWebcam("oil_pump");
  refreshWebcam("tcs");
}, refreshSeconds * 1000);
