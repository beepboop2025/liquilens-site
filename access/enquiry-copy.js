(function () {
  "use strict";

  const button = document.querySelector("[data-copy-enquiry]");
  const template = document.getElementById("enquiry-template");
  const status = document.getElementById("enquiry-copy-status");
  if (!button || !template || !status) return;

  button.hidden = false;
  button.addEventListener("click", async function () {
    try {
      await navigator.clipboard.writeText(template.value);
      status.textContent = "Template copied. Paste it into your email app and fill it in before sending.";
    } catch (_) {
      template.focus();
      template.select();
      status.textContent = "Automatic copying is unavailable. The template is selected; use your device's Copy command, then paste it into your email app.";
    }
  });
}());
