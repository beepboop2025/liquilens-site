import manifest from "./profiles.mjs";

export const topicProfiles = manifest.profiles;
export const defaultProfile = manifest.default;

export function selectConfiguration(client, profileId = defaultProfile) {
  if (!Object.hasOwn(topicProfiles, profileId) || !Object.hasOwn(manifest.filtering, client)) {
    throw new Error("Choose a supported research topic and client.");
  }
  const profile = topicProfiles[profileId];
  return {
    configuration: profile.configurations[client],
    download: profile.downloads[client],
    prompt: profile.prompt,
    description: profile.description,
    scope: manifest.filtering[client] === "selected-tools"
      ? "This configuration selects the listed tools. Merge it with your existing settings and review the resulting tool list."
      : "This configuration connects the relevant servers. This client format does not apply a tool allowlist; review the discovered tools and use the topic prompt.",
  };
}
