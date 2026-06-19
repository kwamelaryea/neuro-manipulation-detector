const DEFAULT_BACKEND = "http://localhost:8000";

async function load() {
  const { backendUrl, enabled } = await chrome.storage.sync.get([
    "backendUrl",
    "enabled",
  ]);
  document.getElementById("backendUrl").value = backendUrl || DEFAULT_BACKEND;
  document.getElementById("enabled").checked = enabled !== false;
}

async function save() {
  const backendUrl =
    document.getElementById("backendUrl").value.trim() || DEFAULT_BACKEND;
  const enabled = document.getElementById("enabled").checked;
  await chrome.storage.sync.set({ backendUrl, enabled });
  const status = document.getElementById("status");
  status.textContent = "Saved.";
  setTimeout(() => (status.textContent = ""), 1500);
}

document.addEventListener("DOMContentLoaded", load);
document.getElementById("save").addEventListener("click", save);
