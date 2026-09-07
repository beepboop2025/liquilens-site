// Only a finite link label crosses the analytics boundary. No visitor identity.
export const SOURCES = Object.freeze([
  "instagram", "facebook", "linkedin", "youtube", "reddit", "telegram",
  "x", "shared", "unknown",
]);
const tasks = ["bank", "funding", "exit"];
export const TELEGRAM_DESKS = Object.freeze({
  bank: {bot: "LiquiLens_bot", label: "Follow LiquiLens on Telegram", note: "Press Start to subscribe to the daily institution briefing and occasional sourced news. /stop ends both."},
  funding: {bot: "seiche_desk_bot", label: "Follow Seiche on Telegram", note: "Press Start to subscribe to the daily funding letter, state-change and cross-desk alerts, and occasional sourced news. /stop ends these updates."},
  exit: {bot: "undertow_LiquiLens_bot", label: "Open Undertow on Telegram", note: "Start opens the desk. Choose /watch separately for recurring updates; /stop ends that watcher stream."},
});

export function acquisitionSource(search) {
  const values = new URLSearchParams(search).getAll("utm_source");
  // Ambiguous or arbitrary query values cannot become log fields.
  return values.length === 1 && SOURCES.includes(values[0]) ? values[0] : "unknown";
}

export function questionLink(task, source = "shared", size) {
  if (!tasks.includes(task) || !SOURCES.includes(source)) throw new Error("Unknown research link.");
  const url = new URL("https://liquilens.in/start/");
  url.searchParams.set("task", task);
  url.searchParams.set("utm_source", source);
  if (task === "exit" && [1000, 10000, 100000, 1000000].includes(Number(size))) url.searchParams.set("size", String(Number(size)));
  return url.href;
}

export function telegramLink(task, source) {
  if (!tasks.includes(task) || !SOURCES.includes(source)) throw new Error("Unknown Telegram link.");
  const bot = TELEGRAM_DESKS[task].bot;
  return `https://t.me/${bot}?start=social_${source}_${task}`;
}
