"use strict";
const examples = {
  counterparty: {title: "Review a bank counterparty", steps: ["resolve the bank and inspect its dated public disclosures, changes and gaps.", "add the relevant funding environment without treating system stress as a verdict on the bank.", "examine market exit evidence when the exposure has a relevant market position."], outcome: "Export the review with source dates and unanswered questions intact."},
  market: {title: "Review a market exposure", steps: ["inspect institution evidence when a named bank or lender is relevant to the exposure.", "check the funding conditions surrounding the market and keep observation clocks attached.", "state a supported position size and inspect dated exit estimates, coverage and assumptions."], outcome: "Keep a market estimate separate from a counterparty judgment or an executable quote."},
  agent: {title: "Build an institution-monitoring agent", steps: ["resolve the institution and retrieve its source-linked review packet through MCP.", "request the funding context relevant to that review, without blending the products’ scores.", "request supported market-liquidity context only when the monitored exposure needs it."], outcome: "Carry sources, dates, missing fields and authority limits into the exported brief. Agent output does not grant execution."}
};
const detail = document.getElementById("workflow-detail");
for (const button of document.querySelectorAll("[data-workflow]")) {
  button.addEventListener("click", () => {
    const example = examples[button.dataset.workflow];
    if (!example || !detail) return;
    for (const other of document.querySelectorAll("[data-workflow]")) other.setAttribute("aria-pressed", String(other === button));
    const title = document.createElement("h3"); title.textContent = example.title;
    const steps = document.createElement("ol");
    example.steps.forEach((text, index) => {const item = document.createElement("li"); const label = document.createElement("strong"); label.textContent = ["LiquiLens", "Seiche", "Undertow"][index] + ": "; item.append(label, document.createTextNode(text)); steps.append(item);});
    const outcome = document.createElement("p"); outcome.textContent = example.outcome;
    detail.replaceChildren(title, steps, outcome);
  });
}
