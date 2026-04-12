const fs = require("node:fs");
const path = require("node:path");

loadEnvFiles();

function loadEnvFiles() {
  [path.resolve(__dirname, "../.env"), path.resolve(__dirname, ".env")].forEach(function (filePath) {
    if (!fs.existsSync(filePath)) {
      return;
    }

    var content = fs.readFileSync(filePath, "utf8");

    content.split(/\r?\n/).forEach(function (line) {
      var trimmed = line.trim();

      if (!trimmed || trimmed.charAt(0) === "#") {
        return;
      }

      var separatorIndex = trimmed.indexOf("=");

      if (separatorIndex === -1) {
        return;
      }

      var key = trimmed.slice(0, separatorIndex).trim();
      var value = trimmed.slice(separatorIndex + 1).trim();

      if (
        value.length >= 2 &&
        ((value.charAt(0) === '"' && value.charAt(value.length - 1) === '"') ||
          (value.charAt(0) === "'" && value.charAt(value.length - 1) === "'"))
      ) {
        value = value.slice(1, -1);
      }

      if (!process.env[key]) {
        process.env[key] = value;
      }
    });
  });
}

function parseBoolean(value, fallbackValue) {
  if (typeof value !== "string") {
    return fallbackValue;
  }

  var normalized = value.trim().toLowerCase();

  if (normalized === "true" || normalized === "1" || normalized === "yes") {
    return true;
  }

  if (normalized === "false" || normalized === "0" || normalized === "no") {
    return false;
  }

  return fallbackValue;
}

function parsePositiveInteger(value, fallbackValue) {
  var parsed = Number.parseInt(value, 10);

  if (Number.isFinite(parsed) && parsed > 0) {
    return parsed;
  }

  return fallbackValue;
}

function parseSecret(value) {
  if (typeof value !== "string") {
    return "";
  }

  var trimmed = value.trim();

  if (
    !trimmed ||
    trimmed === "your_openai_api_key_here" ||
    trimmed === "replace_me"
  ) {
    return "";
  }

  return trimmed;
}

function getAppConfig() {
  return {
    port: parsePositiveInteger(process.env.PORT, 4500),
    corsOrigin: process.env.CORS_ORIGIN || "*",
    openAiApiKey: parseSecret(process.env.OPENAI_API_KEY),
    openAiModel: process.env.OPENAI_MODEL || "gpt-4o",
    hiringAssistantUrl:
      process.env.HIRING_ASSISTANT_URL || "http://localhost:8080",
    requestTimeoutMs: parsePositiveInteger(process.env.REQUEST_TIMEOUT_MS, 30000),
    exposeInternalErrors: parseBoolean(process.env.EXPOSE_INTERNAL_ERRORS, false)
  };
}

module.exports = {
  getAppConfig
};
