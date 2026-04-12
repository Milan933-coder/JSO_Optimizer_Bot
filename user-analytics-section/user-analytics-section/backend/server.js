const http = require("node:http");
const { getAppConfig } = require("./config");
const {
  analyzeCvText,
  getAnalyticsPayload
} = require("./services/analyticsService");

const config = getAppConfig();

function applyCors(response) {
  response.setHeader("Access-Control-Allow-Origin", config.corsOrigin);
  response.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function sendJson(response, statusCode, payload) {
  applyCors(response);
  response.writeHead(statusCode, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload, null, 2));
}

function readJsonBody(request) {
  return new Promise(function (resolve, reject) {
    let body = "";

    request.setEncoding("utf8");

    request.on("data", function (chunk) {
      body += chunk;

      if (body.length > 1024 * 1024) {
        reject(new Error("Request body is too large."));
        request.destroy();
      }
    });

    request.on("end", function () {
      if (!body.trim()) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(body));
      } catch (error) {
        reject(new Error("Request body must be valid JSON."));
      }
    });

    request.on("error", reject);
  });
}

const server = http.createServer(async function (request, response) {
  const requestUrl = new URL(request.url || "/", "http://localhost");

  if (request.method === "OPTIONS") {
    applyCors(response);
    response.writeHead(204);
    response.end();
    return;
  }

  if (requestUrl.pathname === "/" && request.method === "GET") {
    sendJson(response, 200, {
      ok: true,
      service: "user-analytics-section",
      message:
        "Backend is running. Open frontend/index.html for the dashboard UI.",
      routes: {
        health: "/api/health",
        latestAnalytics: "/api/analytics/summary",
        analyzeCv: "/api/analytics/from-cv",
        uiConfig: "/api/ui-config"
      }
    });
    return;
  }

  if (requestUrl.pathname === "/api/health" && request.method === "GET") {
    sendJson(response, 200, {
      ok: true,
      service: "user-analytics-section",
      model: config.openAiModel,
      aiConfigured: Boolean(config.openAiApiKey),
      checkedAt: new Date().toISOString()
    });
    return;
  }

  if (requestUrl.pathname === "/api/ui-config" && request.method === "GET") {
    sendJson(response, 200, {
      hiringAssistantUrl: config.hiringAssistantUrl
    });
    return;
  }

  if (requestUrl.pathname === "/api/analytics/summary" && request.method === "GET") {
    try {
      const payload = await getAnalyticsPayload();
      sendJson(response, 200, payload);
    } catch (error) {
      sendJson(response, 500, {
        error: "Unable to load analytics summary.",
        detail: config.exposeInternalErrors ? error.message : undefined
      });
    }
    return;
  }

  if (requestUrl.pathname === "/api/analytics/from-cv" && request.method === "POST") {
    try {
      const body = await readJsonBody(request);
      const cvText = typeof body.cvText === "string" ? body.cvText.trim() : "";

      if (!cvText) {
        sendJson(response, 400, {
          error: "Please provide CV text before requesting analysis."
        });
        return;
      }

      if (!config.openAiApiKey) {
        sendJson(response, 503, {
          error:
            "OPENAI_API_KEY is missing. Add it to the .env file before analyzing a CV."
        });
        return;
      }

      const payload = await analyzeCvText(cvText, config);
      sendJson(response, 200, payload);
    } catch (error) {
      sendJson(response, 500, {
        error: "Unable to analyze the provided CV.",
        detail: config.exposeInternalErrors ? error.message : undefined
      });
    }
    return;
  }

  sendJson(response, 404, {
    error: "Route not found."
  });
});

server.listen(config.port, function () {
  console.log(
    "User analytics backend listening on http://localhost:" + config.port
  );
});
