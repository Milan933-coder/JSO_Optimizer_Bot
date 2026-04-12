const https = require("node:https");
const { mockAnalyticsSummary } = require("../data/mockAnalytics");

let latestAnalyticsPayload = cloneData(mockAnalyticsSummary);

function cloneData(value) {
  if (value === undefined) {
    return undefined;
  }

  return JSON.parse(JSON.stringify(value));
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function deepMerge(baseValue, overrideValue) {
  if (overrideValue === undefined) {
    return cloneData(baseValue);
  }

  if (Array.isArray(overrideValue)) {
    return cloneData(overrideValue);
  }

  if (isPlainObject(baseValue) && isPlainObject(overrideValue)) {
    const merged = {};
    const keys = new Set(
      Object.keys(baseValue || {}).concat(Object.keys(overrideValue || {}))
    );

    keys.forEach(function (key) {
      if (overrideValue[key] === undefined) {
        merged[key] = cloneData(baseValue[key]);
        return;
      }

      if (baseValue[key] === undefined) {
        merged[key] = cloneData(overrideValue[key]);
        return;
      }

      merged[key] = deepMerge(baseValue[key], overrideValue[key]);
    });

    return merged;
  }

  return cloneData(overrideValue);
}

function validateAnalyticsPayload(payload) {
  if (!isPlainObject(payload)) {
    return false;
  }

  if (!isPlainObject(payload.profile)) {
    return false;
  }

  if (!Array.isArray(payload.metrics) || !Array.isArray(payload.actionPlan)) {
    return false;
  }

  if (!isPlainObject(payload.cvInsights) || !isPlainObject(payload.githubInsights)) {
    return false;
  }

  if (!isPlainObject(payload.expectedTrajectory)) {
    return false;
  }

  return true;
}

function requestJson(urlString, method, headers, body, timeoutMs) {
  return new Promise(function (resolve, reject) {
    const targetUrl = new URL(urlString);
    const request = https.request(
      targetUrl,
      {
        method: method,
        headers: headers
      },
      function (response) {
        let responseBody = "";

        response.setEncoding("utf8");

        response.on("data", function (chunk) {
          responseBody += chunk;
        });

        response.on("end", function () {
          if (response.statusCode < 200 || response.statusCode >= 300) {
            reject(
              new Error("OpenAI request returned status " + response.statusCode)
            );
            return;
          }

          try {
            resolve(JSON.parse(responseBody));
          } catch (error) {
            reject(new Error("OpenAI did not return valid JSON."));
          }
        });
      }
    );

    request.setTimeout(timeoutMs, function () {
      request.destroy(new Error("OpenAI request timed out."));
    });

    request.on("error", reject);

    if (body) {
      request.write(body);
    }

    request.end();
  });
}

function clampScore(value) {
  const score = Number(value);

  if (!Number.isFinite(score)) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round(score)));
}

function cleanTextArray(values, limit) {
  if (!Array.isArray(values)) {
    return [];
  }

  const cleaned = [];

  values.forEach(function (value) {
    const text = String(value || "").trim();

    if (!text || cleaned.length >= limit) {
      return;
    }

    cleaned.push(text);
  });

  return cleaned;
}

function resolveMetricTone(score) {
  if (score >= 80) {
    return "good";
  }

  if (score >= 60) {
    return "steady";
  }

  return "alert";
}

function getMetricPercent(metrics, id) {
  const entry = (metrics || []).find(function (metric) {
    return metric && metric.id === id;
  });

  return entry ? entry.percent : 0;
}

function buildFallbackMetrics(payload) {
  const cvScore = clampScore(payload.cvInsights && payload.cvInsights.score);
  const githubScore = clampScore(payload.githubInsights && payload.githubInsights.score);
  const atsScore = clampScore(getMetricPercent(payload.metrics, "ats-score"));
  const replyScore = clampScore(getMetricPercent(payload.metrics, "response-rate"));

  return [
    {
      id: "cv-score",
      label: "CV Strength",
      value: String(cvScore) + "/100",
      percent: cvScore,
      trend: cvScore ? "Generated from the submitted CV" : "Awaiting CV analysis",
      tone: resolveMetricTone(cvScore),
      description: "CV strength based on clarity, relevance, and impact evidence."
    },
    {
      id: "github-score",
      label: "GitHub Signal",
      value: String(githubScore) + "/100",
      percent: githubScore,
      trend: githubScore
        ? "Generated from GitHub evidence inside the CV"
        : "No GitHub proof found in the CV",
      tone: resolveMetricTone(githubScore),
      description: "Reflects how much public proof of work is visible from the CV."
    },
    {
      id: "ats-score",
      label: "ATS Match",
      value: String(atsScore) + "%",
      percent: atsScore,
      trend: atsScore ? "Keyword alignment estimated from the CV" : "Awaiting analysis",
      tone: resolveMetricTone(atsScore),
      description: "Estimated ATS alignment based on role clarity and keyword coverage."
    },
    {
      id: "response-rate",
      label: "Reply Potential",
      value: replyScore ? String(Math.max(1, Math.round(replyScore / 20))) + "x" : "0x",
      percent: replyScore,
      trend: replyScore ? "Estimated recruiter response strength" : "Awaiting analysis",
      tone: resolveMetricTone(replyScore),
      description: "Estimated recruiter interest based on positioning and impact."
    }
  ];
}

function ensureRequiredMetrics(metrics, payload) {
  const fallbackMetrics = buildFallbackMetrics(payload);
  const metricMap = {};

  (metrics || []).forEach(function (metric) {
    if (metric && metric.id) {
      metricMap[metric.id] = metric;
    }
  });

  fallbackMetrics.forEach(function (fallbackMetric) {
    if (!metricMap[fallbackMetric.id]) {
      metricMap[fallbackMetric.id] = fallbackMetric;
    }
  });

  return fallbackMetrics.map(function (fallbackMetric) {
    return metricMap[fallbackMetric.id];
  });
}

function extractTextFromResponse(responsePayload) {
  if (typeof responsePayload.output_text === "string" && responsePayload.output_text.trim()) {
    return responsePayload.output_text.trim();
  }

  if (!Array.isArray(responsePayload.output)) {
    return "";
  }

  return responsePayload.output
    .filter(function (item) {
      return item && item.type === "message" && Array.isArray(item.content);
    })
    .map(function (item) {
      return item.content
        .filter(function (contentItem) {
          return contentItem && contentItem.type === "output_text";
        })
        .map(function (contentItem) {
          return contentItem.text || "";
        })
        .join("");
    })
    .join("\n")
    .trim();
}

function parseModelJson(text) {
  const candidates = [text];
  const fencedMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const bracesMatch = text.match(/\{[\s\S]*\}/);

  if (fencedMatch && fencedMatch[1]) {
    candidates.push(fencedMatch[1]);
  }

  if (bracesMatch) {
    candidates.push(bracesMatch[0]);
  }

  for (let index = 0; index < candidates.length; index += 1) {
    try {
      return JSON.parse(candidates[index]);
    } catch (error) {
      continue;
    }
  }

  throw new Error("The model response did not contain valid JSON.");
}

function normalizeAnalyticsPayload(rawPayload) {
  const fallbackPayload = cloneData(mockAnalyticsSummary);
  const mergedPayload = deepMerge(fallbackPayload, rawPayload || {});

  mergedPayload.profile = mergedPayload.profile || {};
  mergedPayload.cvInsights = mergedPayload.cvInsights || {};
  mergedPayload.githubInsights = mergedPayload.githubInsights || {};
  mergedPayload.expectedTrajectory = deepMerge(
    fallbackPayload.expectedTrajectory || {},
    mergedPayload.expectedTrajectory || {}
  );
  mergedPayload.projectAdvisor = deepMerge(
    fallbackPayload.projectAdvisor || {},
    mergedPayload.projectAdvisor || {}
  );
  mergedPayload.interviewJourney = deepMerge(
    fallbackPayload.interviewJourney || {},
    mergedPayload.interviewJourney || {}
  );
  mergedPayload.meta = deepMerge(fallbackPayload.meta || {}, mergedPayload.meta || {});
  mergedPayload.meta.source = "openai";
  mergedPayload.meta.usingFallback = false;
  mergedPayload.meta.lastUpdated = new Date().toISOString();
  mergedPayload.meta.message =
    mergedPayload.meta.message ||
    "Analytics generated from the submitted CV using the configured OpenAI model.";

  mergedPayload.profile.candidateName =
    mergedPayload.profile.candidateName || "Candidate";
  mergedPayload.profile.targetRole =
    mergedPayload.profile.targetRole || "Role not detected";
  mergedPayload.profile.targetLocation =
    mergedPayload.profile.targetLocation || "Location not detected";
  mergedPayload.profile.profileCompleteness = clampScore(
    mergedPayload.profile.profileCompleteness
  );
  mergedPayload.profile.readinessLabel =
    mergedPayload.profile.readinessLabel || "Generated from the submitted CV.";

  mergedPayload.cvInsights.score = clampScore(mergedPayload.cvInsights.score);
  mergedPayload.githubInsights.score = clampScore(mergedPayload.githubInsights.score);
  mergedPayload.githubInsights.commitsLast30Days =
    Number(mergedPayload.githubInsights.commitsLast30Days) || 0;
  mergedPayload.githubInsights.pullRequests =
    Number(mergedPayload.githubInsights.pullRequests) || 0;
  mergedPayload.githubInsights.reviewComments =
    Number(mergedPayload.githubInsights.reviewComments) || 0;
  mergedPayload.expectedTrajectory.primaryRole =
    String(mergedPayload.expectedTrajectory.primaryRole || "").trim();
  mergedPayload.expectedTrajectory.careerStage =
    String(mergedPayload.expectedTrajectory.careerStage || "").trim();
  mergedPayload.expectedTrajectory.nextRoleWindow =
    String(mergedPayload.expectedTrajectory.nextRoleWindow || "").trim();
  mergedPayload.expectedTrajectory.trajectorySummary =
    String(mergedPayload.expectedTrajectory.trajectorySummary || "").trim();
  mergedPayload.expectedTrajectory.cvStructure = deepMerge(
    fallbackPayload.expectedTrajectory.cvStructure || {},
    mergedPayload.expectedTrajectory.cvStructure || {}
  );
  mergedPayload.expectedTrajectory.cvStructure.status =
    String(mergedPayload.expectedTrajectory.cvStructure.status || "").trim();
  mergedPayload.expectedTrajectory.cvStructure.rationale =
    String(mergedPayload.expectedTrajectory.cvStructure.rationale || "").trim();
  mergedPayload.projectAdvisor.summary =
    String(mergedPayload.projectAdvisor.summary || "").trim();

  if (!Array.isArray(mergedPayload.metrics) || !mergedPayload.metrics.length) {
    mergedPayload.metrics = buildFallbackMetrics(mergedPayload);
  } else {
    mergedPayload.metrics = mergedPayload.metrics.map(function (metric, index) {
      const percent = clampScore(metric.percent);

      return {
        id: metric.id || "metric-" + String(index + 1),
        label: metric.label || "Metric",
        value: metric.value || String(percent) + "%",
        percent: percent,
        trend: metric.trend || "Generated from the submitted CV",
        tone: metric.tone || resolveMetricTone(percent),
        description: metric.description || ""
      };
    });
  }

  mergedPayload.metrics = ensureRequiredMetrics(mergedPayload.metrics, mergedPayload);

  if (!Array.isArray(mergedPayload.cvInsights.strengths)) {
    mergedPayload.cvInsights.strengths = [];
  }

  if (!Array.isArray(mergedPayload.cvInsights.gaps)) {
    mergedPayload.cvInsights.gaps = [];
  }

  if (!Array.isArray(mergedPayload.cvInsights.recommendations)) {
    mergedPayload.cvInsights.recommendations = [];
  }

  if (!Array.isArray(mergedPayload.githubInsights.topLanguages)) {
    mergedPayload.githubInsights.topLanguages = [];
  }

  if (!Array.isArray(mergedPayload.githubInsights.highlights)) {
    mergedPayload.githubInsights.highlights = [];
  }

  if (!Array.isArray(mergedPayload.githubInsights.recommendations)) {
    mergedPayload.githubInsights.recommendations = [];
  }

  if (!Array.isArray(mergedPayload.expectedTrajectory.alternativeRoles)) {
    mergedPayload.expectedTrajectory.alternativeRoles = [];
  }

  if (!Array.isArray(mergedPayload.expectedTrajectory.evidence)) {
    mergedPayload.expectedTrajectory.evidence = [];
  }

  if (!Array.isArray(mergedPayload.expectedTrajectory.focusAreas)) {
    mergedPayload.expectedTrajectory.focusAreas = [];
  }

  if (!Array.isArray(mergedPayload.projectAdvisor.recommendations)) {
    mergedPayload.projectAdvisor.recommendations = [];
  }

  if (!Array.isArray(mergedPayload.projectAdvisor.projects)) {
    mergedPayload.projectAdvisor.projects = [];
  }

  if (!Array.isArray(mergedPayload.projectRecommendations)) {
    mergedPayload.projectRecommendations = [];
  }

  if (!Array.isArray(mergedPayload.recruiterHighlights)) {
    mergedPayload.recruiterHighlights = [];
  }

  if (!Array.isArray(mergedPayload.actionPlan)) {
    mergedPayload.actionPlan = [];
  }

  if (!mergedPayload.visualAnalytics || typeof mergedPayload.visualAnalytics !== "object") {
    mergedPayload.visualAnalytics = { barInsights: [], pieCharts: [] };
  }

  if (!Array.isArray(mergedPayload.visualAnalytics.barInsights)) {
    mergedPayload.visualAnalytics.barInsights = [];
  }

  if (!Array.isArray(mergedPayload.visualAnalytics.pieCharts)) {
    mergedPayload.visualAnalytics.pieCharts = [];
  }

  if (!Array.isArray(mergedPayload.interviewJourney.upcoming)) {
    mergedPayload.interviewJourney.upcoming = [];
  }

  if (!Array.isArray(mergedPayload.interviewJourney.completed)) {
    mergedPayload.interviewJourney.completed = [];
  }

  if (!validateAnalyticsPayload(mergedPayload)) {
    throw new Error("Generated analytics response is incomplete.");
  }

  return mergedPayload;
}

function buildPrompt(cvText) {
  return [
    "You are a hiring analytics assistant.",
    "Analyze the provided CV text and return only valid JSON.",
    "Do not wrap the JSON in markdown.",
    "Do not invent facts that are not reasonably supported by the CV.",
    "If GitHub activity is not clearly present, keep GitHub counts at 0 and explain the gap instead of making them up.",
    "Keep scores as integers from 0 to 100.",
    "Prefer concise, hiring-focused language.",
    "Infer the most suitable job role trajectory from the CV and classify whether the CV is structured, partially structured, or unstructured.",
    "Add 2-4 short project suggestions the candidate should build next to improve fit for the inferred role.",
    "Use this JSON shape:",
    JSON.stringify(
      {
        meta: {
          message: "Short one-sentence summary of the generated analysis."
        },
        profile: {
          candidateName: "string",
          targetRole: "string",
          targetLocation: "string",
          profileCompleteness: 0,
          readinessLabel: "string"
        },
        metrics: [
          {
            id: "cv-score",
            label: "CV Strength",
            value: "0/100",
            percent: 0,
            trend: "string",
            tone: "good|steady|alert",
            description: "string"
          },
          {
            id: "github-score",
            label: "GitHub Signal",
            value: "0/100",
            percent: 0,
            trend: "string",
            tone: "good|steady|alert",
            description: "string"
          },
          {
            id: "ats-score",
            label: "ATS Match",
            value: "0%",
            percent: 0,
            trend: "string",
            tone: "good|steady|alert",
            description: "string"
          },
          {
            id: "response-rate",
            label: "Reply Potential",
            value: "0x",
            percent: 0,
            trend: "string",
            tone: "good|steady|alert",
            description: "string"
          }
        ],
        cvInsights: {
          score: 0,
          strengths: ["string", "string", "string"],
          gaps: ["string", "string", "string"],
          recommendations: [
            {
              priority: "High|Medium|Low",
              title: "string",
              detail: "string"
            }
          ]
        },
        githubInsights: {
          score: 0,
          commitsLast30Days: 0,
          pullRequests: 0,
          reviewComments: 0,
          topLanguages: ["string"],
          highlights: ["string", "string"],
          recommendations: ["string", "string"]
        },
        expectedTrajectory: {
          primaryRole: "string",
          alternativeRoles: ["string", "string"],
          careerStage: "string",
          nextRoleWindow: "string",
          trajectorySummary: "string",
          evidence: ["string", "string"],
          focusAreas: ["string", "string"],
          cvStructure: {
            status: "Structured|Partially structured|Unstructured",
            rationale: "string"
          }
        },
        projectRecommendations: ["string", "string", "string"],
        actionPlan: [
          {
            window: "string",
            title: "string",
            detail: "string",
            effort: "string"
          }
        ],
        visualAnalytics: {
          barInsights: [
            {
              label: "string",
              value: 0,
              tone: "blue|green|purple",
              note: "string"
            }
          ],
          pieCharts: [
            {
              id: "string",
              title: "string",
              subtitle: "string",
              totalValue: "string",
              totalUnit: "score|plan",
              insight: "string",
              segments: [
                {
                  label: "string",
                  value: 0,
                  color: "#39c4ff"
                }
              ]
            }
          ]
        },
        recruiterHighlights: ["string", "string", "string"],
        interviewJourney: {
          upcoming: [],
          completed: []
        }
      },
      null,
      2
    ),
    "CV text:",
    cvText
  ].join("\n");
}

function normalizeProjectAdvisorPayload(rawPayload, analyticsPayload) {
  const payload = isPlainObject(rawPayload) ? rawPayload : {};
  const inferredRole =
    analyticsPayload.expectedTrajectory.primaryRole ||
    analyticsPayload.profile.targetRole ||
    "the target role";
  const projects = Array.isArray(payload.projects)
    ? payload.projects
        .map(function (project, index) {
          if (!isPlainObject(project)) {
            return null;
          }

          const projectName =
            String(project.projectName || project.title || "").trim() ||
            "Project opportunity " + String(index + 1);
          const projectType = String(project.projectType || "Suggested").trim() || "Suggested";
          const fitReason = String(project.fitReason || project.reason || "").trim();
          const enhancements = cleanTextArray(project.enhancements, 4);
          const cvAdditions = cleanTextArray(
            project.cvAdditions || project.cvBullets || project.resumeAdditions,
            4
          );

          if (!fitReason && !enhancements.length && !cvAdditions.length) {
            return null;
          }

          return {
            projectName: projectName,
            projectType: projectType,
            fitReason:
              fitReason ||
              "This project would better support the candidate's fit for " + inferredRole + ".",
            enhancements: enhancements,
            cvAdditions: cvAdditions
          };
        })
        .filter(Boolean)
        .slice(0, 4)
    : [];

  const recommendations = cleanTextArray(payload.recommendations, 4);
  const derivedRecommendations = projects
    .map(function (project) {
      if (!project.enhancements.length) {
        return "";
      }

      return project.projectName + ": " + project.enhancements[0];
    })
    .filter(Boolean)
    .slice(0, 4);

  return {
    summary:
      String(payload.summary || "").trim() ||
      "These project upgrades would make the CV more convincing for " + inferredRole + ".",
    recommendations: recommendations.length ? recommendations : derivedRecommendations,
    projects: projects
  };
}

function buildProjectAdvisorPrompt(cvText, analyticsPayload) {
  return [
    "You are the Project Advisor Agent for a hiring analytics dashboard.",
    "Read the CV text plus the already-generated analysis and return only valid JSON.",
    "Do not wrap the JSON in markdown.",
    "Identify 2-4 strong project opportunities for this candidate.",
    "You may use projects already implied by the CV or suggest new projects if the CV lacks proof.",
    "Keep every field short, practical, and recruiter-friendly.",
    "For each project, say what to enhance or build next and what should be added explicitly to the CV.",
    "Use this JSON shape:",
    JSON.stringify(
      {
        summary: "One short summary of how better projects could improve the profile.",
        recommendations: ["short text", "short text", "short text"],
        projects: [
          {
            projectName: "string",
            projectType: "Existing|Suggested",
            fitReason: "string",
            enhancements: ["string", "string"],
            cvAdditions: ["string", "string"]
          }
        ]
      },
      null,
      2
    ),
    "Analytics snapshot:",
    JSON.stringify(
      {
        profile: analyticsPayload.profile,
        expectedTrajectory: analyticsPayload.expectedTrajectory,
        cvInsights: {
          gaps: analyticsPayload.cvInsights.gaps,
          recommendations: analyticsPayload.cvInsights.recommendations
        },
        projectRecommendations: analyticsPayload.projectRecommendations
      },
      null,
      2
    ),
    "CV text:",
    cvText
  ].join("\n");
}

async function requestModelAnalysis(prompt, config, maxOutputTokens) {
  const requestBody = JSON.stringify({
    model: config.openAiModel,
    input: [
      {
        role: "user",
        content: prompt
      }
    ],
    max_output_tokens: maxOutputTokens
  });

  const responsePayload = await requestJson(
    "https://api.openai.com/v1/responses",
    "POST",
    {
      "Content-Type": "application/json",
      Authorization: "Bearer " + config.openAiApiKey
    },
    requestBody,
    config.requestTimeoutMs
  );
  const responseText = extractTextFromResponse(responsePayload);

  return parseModelJson(responseText);
}

async function analyzeCvText(cvText, config) {
  const parsedPayload = await requestModelAnalysis(buildPrompt(cvText), config, 2500);
  const normalizedPayload = normalizeAnalyticsPayload(parsedPayload);

  try {
    const projectAdvisorPayload = await requestModelAnalysis(
      buildProjectAdvisorPrompt(cvText, normalizedPayload),
      config,
      1600
    );
    const normalizedProjectAdvisor = normalizeProjectAdvisorPayload(
      projectAdvisorPayload,
      normalizedPayload
    );

    normalizedPayload.projectAdvisor = normalizedProjectAdvisor;

    if (normalizedProjectAdvisor.recommendations.length) {
      normalizedPayload.projectRecommendations = cloneData(
        normalizedProjectAdvisor.recommendations
      );
    }
  } catch (error) {
    normalizedPayload.projectAdvisor = deepMerge(
      cloneData(mockAnalyticsSummary.projectAdvisor || {}),
      {
        summary:
          "The project advisor agent could not refine project suggestions for this CV yet."
      }
    );
  }

  latestAnalyticsPayload = cloneData(normalizedPayload);
  return normalizedPayload;
}

async function getAnalyticsPayload() {
  return cloneData(latestAnalyticsPayload);
}

module.exports = {
  analyzeCvText,
  getAnalyticsPayload
};
