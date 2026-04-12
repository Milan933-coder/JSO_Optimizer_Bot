(function () {
  "use strict";

  var dashboardData = createEmptyData();
  var config = Object.assign(
    {
      apiBaseUrl: "http://localhost:4500",
      requestTimeoutMs: 30000,
      assistantUrl: "http://localhost:8080"
    },
    window.USER_ANALYTICS_CONFIG || {}
  );
  var runtimeState = {
    assistantUrl: config.assistantUrl
  };
  var chartInstance = null;
  var pdfWorkerUrl =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

  var elements = {
    heroSummary: document.getElementById("hero-summary"),
    candidateName: document.getElementById("candidate-name"),
    candidateRole: document.getElementById("candidate-role"),
    dnaHealthScore: document.getElementById("dna-health-score"),
    cvScore: document.getElementById("cv-score"),
    githubScore: document.getElementById("github-score"),
    completenessScore: document.getElementById("completeness-score"),
    dnaHelix: document.getElementById("dna-helix"),
    chartCanvas: document.getElementById("career-chart"),
    chartFallback: document.getElementById("chart-fallback"),
    fallbackDonut: document.getElementById("fallback-donut"),
    chartLegend: document.getElementById("chart-legend"),
    strengthList: document.getElementById("strength-list"),
    gapList: document.getElementById("gap-list"),
    recruiterList: document.getElementById("recruiter-list"),
    trajectoryPrimaryRole: document.getElementById("trajectory-primary-role"),
    trajectorySummary: document.getElementById("trajectory-summary"),
    trajectoryStructureStatus: document.getElementById("trajectory-structure-status"),
    trajectoryStructureNote: document.getElementById("trajectory-structure-note"),
    trajectoryCareerStage: document.getElementById("trajectory-career-stage"),
    trajectoryRoleWindow: document.getElementById("trajectory-role-window"),
    trajectoryRoleChips: document.getElementById("trajectory-role-chips"),
    trajectoryEvidenceList: document.getElementById("trajectory-evidence-list"),
    trajectoryFocusList: document.getElementById("trajectory-focus-list"),
    projectAdvisorSummary: document.getElementById("project-advisor-summary"),
    projectAdvisorGrid: document.getElementById("project-advisor-grid"),
    projectRecommendationList: document.getElementById("project-recommendation-list"),
    recommendationStack: document.getElementById("recommendation-stack"),
    languageChips: document.getElementById("language-chips"),
    upcomingList: document.getElementById("upcoming-list"),
    completedList: document.getElementById("completed-list"),
    viewButtons: Array.prototype.slice.call(
      document.querySelectorAll("[data-view-target]")
    ),
    viewScreens: Array.prototype.slice.call(
      document.querySelectorAll(".view-screen")
    ),
    cvInput: document.getElementById("cv-input"),
    cvFileInput: document.getElementById("cv-file-input"),
    analyzeCvButton: document.getElementById("analyze-cv-button"),
    aiAssistantButton: document.getElementById("ai-assistant-button"),
    cvStatus: document.getElementById("cv-status")
  };

  initializeViewSwitcher();
  initializePdfSupport();
  initializeCvActions();
  applyDashboardData(dashboardData);
  setCvStatus(
    (dashboardData.meta && dashboardData.meta.message) ||
      "Paste a CV and click Analyze CV to get started.",
    "pending"
  );
  loadUiConfig();

  function createEmptyData() {
    return {
      meta: {
        source: "empty",
        usingFallback: true,
        message: "Paste a CV to generate analytics with the configured AI backend.",
        lastUpdated: null
      },
      profile: {
        candidateName: "Waiting for CV",
        targetRole: "Target role pending",
        targetLocation: "Location pending",
        profileCompleteness: 0,
        readinessLabel: "Paste a CV to generate a readiness snapshot."
      },
      metrics: [],
      cvInsights: {
        score: 0,
        strengths: [],
        gaps: [],
        recommendations: []
      },
      githubInsights: {
        score: 0,
        commitsLast30Days: 0,
        pullRequests: 0,
        reviewComments: 0,
        topLanguages: [],
        highlights: [],
        recommendations: []
      },
      expectedTrajectory: {
        primaryRole: "",
        alternativeRoles: [],
        careerStage: "",
        nextRoleWindow: "",
        trajectorySummary: "",
        evidence: [],
        focusAreas: [],
        cvStructure: {
          status: "",
          rationale: ""
        }
      },
      projectAdvisor: {
        summary: "",
        recommendations: [],
        projects: []
      },
      projectRecommendations: [],
      actionPlan: [],
      visualAnalytics: {
        barInsights: [],
        pieCharts: []
      },
      recruiterHighlights: [],
      interviewJourney: {
        upcoming: [],
        completed: []
      }
    };
  }

  function cloneData(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function initializeViewSwitcher() {
    elements.viewButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        setActiveView(button.getAttribute("data-view-target"));
      });
    });
  }

  function initializePdfSupport() {
    if (
      window.pdfjsLib &&
      window.pdfjsLib.GlobalWorkerOptions &&
      !window.pdfjsLib.GlobalWorkerOptions.workerSrc
    ) {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;
    }
  }

  function initializeCvActions() {
    if (elements.analyzeCvButton) {
      elements.analyzeCvButton.addEventListener("click", handleAnalyzeCv);
    }

    if (elements.aiAssistantButton) {
      elements.aiAssistantButton.addEventListener("click", function () {
        if (!runtimeState.assistantUrl) {
          setCvStatus("The Hiring Assistant URL is not configured yet.", "error");
          return;
        }

        window.open(runtimeState.assistantUrl, "_blank", "noopener,noreferrer");
      });
    }

    if (elements.cvFileInput) {
      elements.cvFileInput.addEventListener("change", handleCvFileLoad);
    }
  }

  function setActiveView(targetId) {
    elements.viewButtons.forEach(function (button) {
      var isActive = button.getAttribute("data-view-target") === targetId;
      button.classList.toggle("is-active", isActive);
    });

    elements.viewScreens.forEach(function (screen) {
      screen.classList.toggle("is-active", screen.id === targetId);
    });
  }

  async function loadUiConfig() {
    try {
      var response = await fetchWithTimeout(
        trimTrailingSlash(config.apiBaseUrl) + "/api/ui-config",
        config.requestTimeoutMs
      );

      if (!response.ok) {
        return;
      }

      var payload = await response.json();

      if (payload && payload.hiringAssistantUrl) {
        runtimeState.assistantUrl = payload.hiringAssistantUrl;
      }
    } catch (error) {
      runtimeState.assistantUrl = config.assistantUrl;
    }
  }

  async function handleAnalyzeCv() {
    var cvText = elements.cvInput ? elements.cvInput.value.trim() : "";

    if (!cvText) {
      setCvStatus("Paste the CV text first so the dashboard has real data to analyze.", "error");
      if (elements.cvInput) {
        elements.cvInput.focus();
      }
      return;
    }

    if (typeof fetch !== "function") {
      setCvStatus("This browser cannot send the CV to the backend.", "error");
      return;
    }

    setAnalyzeLoading(true);
    setCvStatus("Analyzing the CV with the configured AI model. This may take a few seconds.", "pending");

    try {
      var response = await fetchWithTimeout(
        trimTrailingSlash(config.apiBaseUrl) + "/api/analytics/from-cv",
        config.requestTimeoutMs,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            cvText: cvText
          })
        }
      );
      var payload = await readJsonResponse(response);

      if (!response.ok) {
        throw new Error(
          (payload && payload.error) ||
            "The backend could not complete the CV analysis."
        );
      }

      applyDashboardData(payload);
      setActiveView("dashboard-view");
      setCvStatus(
        (payload.meta && payload.meta.message) ||
          "CV analysis complete. The dashboard has been updated.",
        "success"
      );
    } catch (error) {
      setCvStatus(normalizeFetchError(error), "error");
    } finally {
      setAnalyzeLoading(false);
    }
  }

  async function handleCvFileLoad(event) {
    var input = event.target;
    var file = input && input.files ? input.files[0] : null;

    if (!file) {
      return;
    }

    setCvStatus('Loading "' + file.name + '"...', "pending");

    try {
      var fileText = isPdfFile(file)
        ? await extractTextFromPdf(file)
        : await readTextFile(file);
      var normalizedText = String(fileText || "").trim();

      if (!normalizedText) {
        throw new Error(
          "No readable text was found in that file. If it is a scanned PDF, paste the CV text manually."
        );
      }

      if (elements.cvInput) {
        elements.cvInput.value = normalizedText;
      }

      setCvStatus(
        'Loaded "' + file.name + '". Review the extracted text and click Analyze CV.',
        "success"
      );
    } catch (error) {
      setCvStatus(
        error && error.message
          ? error.message
          : "That file could not be read. Paste the CV text manually instead.",
        "error"
      );
    } finally {
      if (input) {
        input.value = "";
      }
    }
  }

  function isPdfFile(file) {
    var fileType = String((file && file.type) || "").toLowerCase();
    var fileName = String((file && file.name) || "");

    return fileType === "application/pdf" || /\.pdf$/i.test(fileName);
  }

  function readTextFile(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();

      reader.onload = function () {
        resolve(String(reader.result || ""));
      };

      reader.onerror = function () {
        reject(
          new Error("That file could not be read. Paste the CV text manually instead.")
        );
      };

      reader.readAsText(file);
    });
  }

  function readFileAsArrayBuffer(file) {
    if (file && typeof file.arrayBuffer === "function") {
      return file.arrayBuffer();
    }

    return new Promise(function (resolve, reject) {
      var reader = new FileReader();

      reader.onload = function () {
        resolve(reader.result);
      };

      reader.onerror = function () {
        reject(new Error("That PDF could not be read."));
      };

      reader.readAsArrayBuffer(file);
    });
  }

  async function extractTextFromPdf(file) {
    if (!window.pdfjsLib || typeof window.pdfjsLib.getDocument !== "function") {
      throw new Error("PDF support did not load. Refresh the page and try the PDF again.");
    }

    initializePdfSupport();

    var pdfData = await readFileAsArrayBuffer(file);
    var loadingTask = window.pdfjsLib.getDocument({
      data: new Uint8Array(pdfData)
    });
    var pdfDocument = await loadingTask.promise;
    var pages = [];

    for (var pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
      var page = await pdfDocument.getPage(pageNumber);
      var textContent = await page.getTextContent();
      var pageText = textContent.items
        .map(function (item) {
          return item && item.str ? item.str : "";
        })
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();

      if (pageText) {
        pages.push(pageText);
      }
    }

    if (!pages.length) {
      throw new Error(
        "This PDF does not contain selectable text. If it is a scanned PDF, paste the CV text manually."
      );
    }

    return pages.join("\n\n");
  }

  function setAnalyzeLoading(isLoading) {
    if (!elements.analyzeCvButton) {
      return;
    }

    elements.analyzeCvButton.disabled = isLoading;
    elements.analyzeCvButton.textContent = isLoading ? "Analyzing..." : "Analyze CV";
  }

  function setCvStatus(message, tone) {
    if (!elements.cvStatus) {
      return;
    }

    elements.cvStatus.textContent = message;
    elements.cvStatus.className = "status-copy is-" + (tone || "pending");
  }

  function normalizeFetchError(error) {
    var message = error && error.message ? error.message : "";

    if (
      message === "Failed to fetch" ||
      message.indexOf("NetworkError") !== -1 ||
      message.indexOf("aborted") !== -1
    ) {
      return "Cannot reach the analytics backend. Start node backend/server.js and try again.";
    }

    return message || "The CV analysis request failed.";
  }

  function applyDashboardData(data) {
    dashboardData = cloneData(data || createEmptyData());

    var dnaNodes = buildDnaNodes(dashboardData);
    var statusDistribution = buildStatusDistribution(
      dnaNodes,
      hasGeneratedAnalytics(dashboardData)
    );
    var journeyData = dashboardData.interviewJourney || {};

    renderHero(dashboardData, dnaNodes);
    renderDnaHelix(dnaNodes);
    renderChartLegend(statusDistribution);
    renderExpectedTrajectory(dashboardData);
    renderProjectAdvisor(dashboardData);
    renderInsightLists(dashboardData);
    renderRecommendations(dashboardData);
    renderLanguageChips(dashboardData);
    renderSignalChart(statusDistribution);
    renderUpcomingList(journeyData.upcoming || []);
    renderCompletedList(journeyData.completed || []);
  }

  function hasGeneratedAnalytics(data) {
    return Boolean(data && data.meta && data.meta.source && data.meta.source !== "empty");
  }

  function getMetricById(metrics, id) {
    return (metrics || []).find(function (metric) {
      return metric.id === id;
    });
  }

  function buildDnaNodes(data) {
    var cvMetric = getMetricById(data.metrics, "cv-score");
    var atsMetric = getMetricById(data.metrics, "ats-score");
    var githubMetric = getMetricById(data.metrics, "github-score");
    var pending = !hasGeneratedAnalytics(data);

    return [
      createNode(
        "Skills",
        getSafeScore(atsMetric && atsMetric.percent, 0),
        "Skills are judged by keyword clarity and stack relevance.",
        data.cvInsights.gaps && data.cvInsights.gaps[1],
        data.cvInsights.recommendations &&
          data.cvInsights.recommendations[2] &&
          data.cvInsights.recommendations[2].detail,
        0,
        pending
      ),
      createNode(
        "Projects",
        getSafeScore(cvMetric && cvMetric.percent, data.cvInsights.score),
        "Projects create the clearest proof of execution inside the CV.",
        data.cvInsights.strengths && data.cvInsights.strengths[0],
        data.cvInsights.recommendations &&
          data.cvInsights.recommendations[0] &&
          data.cvInsights.recommendations[0].detail,
        1,
        pending
      ),
      createNode(
        "GitHub Signal",
        getSafeScore(githubMetric && githubMetric.percent, data.githubInsights.score),
        "GitHub evidence helps validate consistency, proof of work, and technical depth.",
        data.githubInsights.highlights && data.githubInsights.highlights[0],
        data.githubInsights.recommendations && data.githubInsights.recommendations[0],
        2,
        pending
      ),
      createNode(
        "CV Strength",
        getSafeScore(data.cvInsights.score, 0),
        "CV strength reflects clarity, impact, and how quickly value is understood.",
        data.cvInsights.strengths && data.cvInsights.strengths[2],
        data.cvInsights.recommendations &&
          data.cvInsights.recommendations[1] &&
          data.cvInsights.recommendations[1].detail,
        3,
        pending
      )
    ];
  }

  function createNode(label, score, intro, evidence, suggestion, index, pending) {
    var status = pending ? { tone: "blue", label: "Awaiting CV" } : resolveStatus(score);

    return {
      label: label,
      score: score,
      intro: pending
        ? "Paste a CV to score this category with real hiring signals."
        : intro || "Signal details are not available yet.",
      evidence: pending
        ? "No CV has been analyzed yet for this category."
        : evidence || "No supporting note available yet.",
      suggestion: pending
        ? "Submit a CV to generate suggestions for this category."
        : suggestion || "Review and refine this category with a stronger proof point.",
      tone: status.tone,
      statusLabel: status.label,
      align: index % 2 === 0 ? "left" : "right",
      delay: 0.12 + index * 0.08
    };
  }

  function resolveStatus(score) {
    if (score >= 80) {
      return { tone: "green", label: "Strong" };
    }

    if (score >= 70) {
      return { tone: "purple", label: "Improving" };
    }

    return { tone: "red", label: "Weak" };
  }

  function getSafeScore(primaryValue, fallbackValue) {
    var score = Number(primaryValue);

    if (!Number.isFinite(score)) {
      score = Number(fallbackValue);
    }

    if (!Number.isFinite(score)) {
      score = 0;
    }

    return Math.max(0, Math.min(100, Math.round(score)));
  }

  function buildStatusDistribution(nodes, hasGeneratedData) {
    if (!hasGeneratedData) {
      return [
        {
          label: "Strong",
          value: 0,
          color: "#4be39d"
        },
        {
          label: "Improving",
          value: 0,
          color: "#9f7bff"
        },
        {
          label: "Weak",
          value: 0,
          color: "#ff6b81"
        }
      ];
    }

    return [
      {
        label: "Strong",
        value: countNodesByTone(nodes, "green"),
        color: "#4be39d"
      },
      {
        label: "Improving",
        value: countNodesByTone(nodes, "purple"),
        color: "#9f7bff"
      },
      {
        label: "Weak",
        value: countNodesByTone(nodes, "red"),
        color: "#ff6b81"
      }
    ];
  }

  function countNodesByTone(nodes, tone) {
    return nodes.filter(function (node) {
      return node.tone === tone;
    }).length;
  }

  function renderHero(data, nodes) {
    var profile = data.profile || {};
    var hasGeneratedData = hasGeneratedAnalytics(data);
    var avgScore = hasGeneratedData
      ? Math.round(
          nodes.reduce(function (sum, node) {
            return sum + node.score;
          }, 0) / (nodes.length || 1)
        )
      : 0;
    var roleSummary = [profile.targetRole, profile.targetLocation]
      .filter(Boolean)
      .join(" | ");

    elements.heroSummary.textContent =
      (data.meta && data.meta.message) ||
      "Paste a CV below to generate a personalized dashboard.";
    elements.candidateName.textContent = profile.candidateName || "Waiting for CV";
    elements.candidateRole.textContent =
      roleSummary || "Paste a CV to fill the role and location";
    elements.dnaHealthScore.textContent = String(avgScore);
    elements.cvScore.textContent = String(getSafeScore(data.cvInsights.score, 0));
    elements.githubScore.textContent = String(
      getSafeScore(data.githubInsights.score, 0)
    );
    elements.completenessScore.textContent =
      String(profile.profileCompleteness || 0) + "%";
  }

  function renderDnaHelix(nodes) {
    clearContainer(elements.dnaHelix);

    nodes.forEach(function (node) {
      var row = document.createElement("div");
      row.className = "dna-row align-" + node.align;
      row.style.setProperty("--delay", node.delay + "s");

      var summary = document.createElement("article");
      summary.className = "dna-summary";

      var summaryTitle = document.createElement("strong");
      summaryTitle.textContent = node.label;

      var summaryText = document.createElement("p");
      summaryText.textContent = node.intro;

      var core = document.createElement("div");
      core.className = "dna-core";

      var button = document.createElement("button");
      button.type = "button";
      button.className = "dna-node";
      button.setAttribute("aria-label", node.label + " score " + node.score);
      button.style.setProperty("--node-gradient", buildNodeGradient(node.tone));
      button.style.setProperty("--node-glow", buildNodeGlow(node.tone));

      var score = document.createElement("span");
      score.className = "dna-node-score";
      score.textContent = String(node.score);

      var tooltip = document.createElement("article");
      tooltip.className = "dna-tooltip";

      var tooltipLabel = document.createElement("p");
      tooltipLabel.className = "dna-tooltip-label";
      tooltipLabel.textContent = node.statusLabel;

      var tooltipTitle = document.createElement("h3");
      tooltipTitle.textContent = node.label + " | " + node.score + "/100";

      var tooltipIntro = document.createElement("p");
      tooltipIntro.textContent = node.evidence;

      var statusBadge = document.createElement("span");
      statusBadge.className = "dna-status tone-" + node.tone;
      statusBadge.textContent = node.statusLabel;

      var tooltipList = document.createElement("ul");
      tooltipList.appendChild(createListItem("Insight: " + node.intro));
      tooltipList.appendChild(createListItem("Suggestion: " + node.suggestion));

      button.appendChild(score);
      tooltip.appendChild(tooltipLabel);
      tooltip.appendChild(tooltipTitle);
      tooltip.appendChild(tooltipIntro);
      tooltip.appendChild(statusBadge);
      tooltip.appendChild(tooltipList);

      summary.appendChild(summaryTitle);
      summary.appendChild(summaryText);
      core.appendChild(button);
      core.appendChild(tooltip);
      row.appendChild(summary);
      row.appendChild(core);
      elements.dnaHelix.appendChild(row);
    });
  }

  function buildNodeGradient(tone) {
    if (tone === "green") {
      return "linear-gradient(135deg, #4be39d, #39c980)";
    }

    if (tone === "red") {
      return "linear-gradient(135deg, #ff6b81, #ff8f66)";
    }

    if (tone === "blue") {
      return "linear-gradient(135deg, #39c4ff, #5f8bff)";
    }

    return "linear-gradient(135deg, #9f7bff, #5f8bff)";
  }

  function buildNodeGlow(tone) {
    if (tone === "green") {
      return "rgba(75, 227, 157, 0.42)";
    }

    if (tone === "red") {
      return "rgba(255, 107, 129, 0.4)";
    }

    if (tone === "blue") {
      return "rgba(58, 203, 255, 0.42)";
    }

    return "rgba(159, 123, 255, 0.4)";
  }

  function renderSignalChart(dataset) {
    renderFallbackChart(dataset);

    if (!elements.chartCanvas || !elements.chartFallback) {
      return;
    }

    if (typeof window.Chart !== "function") {
      elements.chartCanvas.style.display = "none";
      elements.chartFallback.classList.remove("is-hidden");
      return;
    }

    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }

    elements.chartCanvas.style.display = "block";
    elements.chartFallback.classList.add("is-hidden");

    chartInstance = new window.Chart(elements.chartCanvas, {
      type: "doughnut",
      data: {
        labels: dataset.map(function (item) {
          return item.label;
        }),
        datasets: [
          {
            data: dataset.map(function (item) {
              return item.value;
            }),
            backgroundColor: dataset.map(function (item) {
              return item.color;
            }),
            borderColor: "rgba(7, 14, 28, 0.9)",
            borderWidth: 3,
            hoverOffset: 10
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "64%",
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: "rgba(10, 18, 34, 0.96)",
            titleColor: "#eef4ff",
            bodyColor: "#a9b8d7",
            borderColor: "rgba(132, 163, 234, 0.2)",
            borderWidth: 1,
            padding: 12
          }
        }
      }
    });
  }

  function renderFallbackChart(dataset) {
    var total = dataset.reduce(function (sum, item) {
      return sum + item.value;
    }, 0);

    if (!total) {
      elements.fallbackDonut.style.background =
        "conic-gradient(#243a6e 0deg 360deg)";
      return;
    }

    var currentAngle = 0;
    var stops = dataset.map(function (item) {
      var start = currentAngle;
      var sweep = (item.value / total) * 360;
      currentAngle += sweep;
      return item.color + " " + start + "deg " + currentAngle + "deg";
    });

    elements.fallbackDonut.style.background =
      "conic-gradient(" + stops.join(", ") + ")";
  }

  function renderChartLegend(dataset) {
    clearContainer(elements.chartLegend);

    dataset.forEach(function (item) {
      var entry = document.createElement("div");
      entry.className = "chart-legend-item";

      var left = document.createElement("div");
      left.className = "chart-legend-left";

      var dot = document.createElement("span");
      dot.className = "chart-legend-dot";
      dot.style.backgroundColor = item.color;
      dot.style.color = item.color;

      var label = document.createElement("span");
      label.textContent = item.label;

      var value = document.createElement("strong");
      value.textContent = String(item.value);

      left.appendChild(dot);
      left.appendChild(label);
      entry.appendChild(left);
      entry.appendChild(value);
      elements.chartLegend.appendChild(entry);
    });
  }

  function renderInsightLists(data) {
    renderList(
      elements.strengthList,
      data.cvInsights.strengths || [],
      "AI strengths will appear here after CV analysis."
    );
    renderList(
      elements.gapList,
      data.cvInsights.gaps || [],
      "AI gaps will appear here after CV analysis."
    );
    renderList(
      elements.recruiterList,
      data.recruiterHighlights || [],
      "Recruiter-facing highlights will appear here after CV analysis."
    );
    renderList(
      elements.projectRecommendationList,
      data.projectRecommendations || [],
      "Small project suggestions will appear here after CV analysis."
    );
  }

  function renderExpectedTrajectory(data) {
    var trajectory = data.expectedTrajectory || {};
    var cvStructure = trajectory.cvStructure || {};
    var hasGeneratedData = hasGeneratedAnalytics(data);

    elements.trajectoryPrimaryRole.textContent =
      trajectory.primaryRole ||
      (hasGeneratedData ? "Role fit not clearly detected" : "Awaiting CV analysis");
    elements.trajectorySummary.textContent =
      trajectory.trajectorySummary ||
      (hasGeneratedData
        ? "The model could not infer a confident trajectory summary from the current CV."
        : "Analyze a CV to estimate the user's likely hiring direction and growth path.");
    elements.trajectoryStructureStatus.textContent =
      cvStructure.status || (hasGeneratedData ? "Not classified" : "Pending");
    elements.trajectoryStructureNote.textContent =
      cvStructure.rationale ||
      (hasGeneratedData
        ? "The model did not provide a structure note for this CV."
        : "The dashboard will classify whether the CV looks structured or unstructured after analysis.");
    elements.trajectoryCareerStage.textContent =
      trajectory.careerStage || (hasGeneratedData ? "Not detected" : "Pending");
    elements.trajectoryRoleWindow.textContent =
      trajectory.nextRoleWindow ||
      (hasGeneratedData
        ? "A likely next-step role window was not identified from the CV."
        : "The likely next role window will appear here after CV analysis.");

    renderChipList(
      elements.trajectoryRoleChips,
      trajectory.alternativeRoles || [],
      "Alternative role matches will appear here after CV analysis."
    );
    renderList(
      elements.trajectoryEvidenceList,
      trajectory.evidence || [],
      "Evidence for the expected trajectory will appear here after CV analysis."
    );
    renderList(
      elements.trajectoryFocusList,
      trajectory.focusAreas || [],
      "Next-step focus areas will appear here after CV analysis."
    );
  }

  function renderProjectAdvisor(data) {
    var projectAdvisor = data.projectAdvisor || {};
    var hasGeneratedData = hasGeneratedAnalytics(data);
    var projects = Array.isArray(projectAdvisor.projects) ? projectAdvisor.projects : [];

    elements.projectAdvisorSummary.textContent =
      projectAdvisor.summary ||
      (hasGeneratedData
        ? "The separate project advisor did not return a project summary for this CV."
        : "Analyze a CV to let the project advisor identify projects to improve and what to add in the CV.");

    clearContainer(elements.projectAdvisorGrid);

    if (!projects.length) {
      elements.projectAdvisorGrid.appendChild(
        createEmptyCard(
          "No project advisor output yet.",
          "Per-project enhancement advice will appear here after CV analysis."
        )
      );
      return;
    }

    projects.forEach(function (project) {
      elements.projectAdvisorGrid.appendChild(createProjectAdvisorCard(project));
    });
  }

  function renderRecommendations(data) {
    clearContainer(elements.recommendationStack);

    if (!data.cvInsights.recommendations || !data.cvInsights.recommendations.length) {
      elements.recommendationStack.appendChild(
        createEmptyCard(
          "Analyze a CV to generate recommendations.",
          "High-priority rewrite suggestions will appear here."
        )
      );
      return;
    }

    data.cvInsights.recommendations.forEach(function (item) {
      var card = document.createElement("article");
      card.className = "recommendation-card";

      var meta = document.createElement("div");
      meta.className = "recommendation-meta";
      meta.textContent = (item.priority || "Info") + " Priority";

      var title = document.createElement("h3");
      title.textContent = item.title || "Recommendation";

      var copy = document.createElement("p");
      copy.className = "recommendation-copy";
      copy.textContent = item.detail || "";

      card.appendChild(meta);
      card.appendChild(title);
      card.appendChild(copy);
      elements.recommendationStack.appendChild(card);
    });
  }

  function renderLanguageChips(data) {
    clearContainer(elements.languageChips);

    if (!data.githubInsights.topLanguages || !data.githubInsights.topLanguages.length) {
      elements.languageChips.appendChild(
        createInlineEmptyState("No languages extracted yet.")
      );
      return;
    }

    data.githubInsights.topLanguages.forEach(function (language) {
      var chip = document.createElement("span");
      chip.className = "language-chip";
      chip.textContent = language;
      elements.languageChips.appendChild(chip);
    });
  }

  function renderChipList(container, items, emptyText) {
    clearContainer(container);

    if (!items.length) {
      container.appendChild(createInlineEmptyState(emptyText));
      return;
    }

    items.forEach(function (item) {
      var chip = document.createElement("span");
      chip.className = "language-chip trajectory-chip";
      chip.textContent = item;
      container.appendChild(chip);
    });
  }

  function renderUpcomingList(items) {
    clearContainer(elements.upcomingList);

    if (!items.length) {
      elements.upcomingList.appendChild(
        createTimelineEmptyState(
          "No upcoming interview records yet.",
          "This view no longer uses mock interviews."
        )
      );
      return;
    }

    items.forEach(function (item) {
      var card = document.createElement("article");
      card.className = "timeline-card";

      var top = document.createElement("div");
      top.className = "timeline-top";

      var titleGroup = document.createElement("div");
      titleGroup.className = "timeline-title-group";

      var title = document.createElement("h3");
      title.textContent = item.role + " | " + item.company;

      var meta = document.createElement("p");
      meta.className = "timeline-meta";
      meta.textContent = "HR: " + item.hrName + " | Schedule: " + item.schedule;

      var pill = document.createElement("span");
      pill.className = "timeline-pill upcoming";
      pill.textContent = item.mode;

      var infoGrid = document.createElement("div");
      infoGrid.className = "timeline-gridline";
      infoGrid.appendChild(createTimelineChip("Company", item.company));
      infoGrid.appendChild(createTimelineChip("HR Name", item.hrName));
      infoGrid.appendChild(createTimelineChip("Location", item.location));

      var note = document.createElement("p");
      note.className = "timeline-note";
      note.textContent = item.note;

      titleGroup.appendChild(title);
      titleGroup.appendChild(meta);
      top.appendChild(titleGroup);
      top.appendChild(pill);
      card.appendChild(top);
      card.appendChild(infoGrid);
      card.appendChild(note);
      elements.upcomingList.appendChild(card);
    });
  }

  function renderCompletedList(items) {
    clearContainer(elements.completedList);

    if (!items.length) {
      elements.completedList.appendChild(
        createTimelineEmptyState(
          "No completed interview records yet.",
          "This view no longer uses mock completed rounds."
        )
      );
      return;
    }

    items.forEach(function (item) {
      var card = document.createElement("article");
      card.className = "timeline-card";

      var top = document.createElement("div");
      top.className = "timeline-top";

      var titleGroup = document.createElement("div");
      titleGroup.className = "timeline-title-group";

      var title = document.createElement("h3");
      title.textContent = item.role + " | " + item.company;

      var meta = document.createElement("p");
      meta.className = "timeline-meta";
      meta.textContent = "Final result recorded for this application track.";

      var pill = document.createElement("span");
      pill.className = "timeline-pill " + resolveOutcomeTone(item.outcome);
      pill.textContent = item.outcome;

      var stages = document.createElement("ul");
      stages.className = "timeline-stage-list";
      item.stageSummary.forEach(function (stage) {
        stages.appendChild(createListItem(stage));
      });

      var note = document.createElement("p");
      note.className = "timeline-note";
      note.textContent = item.note;

      titleGroup.appendChild(title);
      titleGroup.appendChild(meta);
      top.appendChild(titleGroup);
      top.appendChild(pill);
      card.appendChild(top);
      card.appendChild(stages);
      card.appendChild(note);
      elements.completedList.appendChild(card);
    });
  }

  function createTimelineChip(label, value) {
    var chip = document.createElement("div");
    chip.className = "timeline-chip";
    chip.textContent = label + ": " + value;
    return chip;
  }

  function createTimelineEmptyState(title, copy) {
    var card = document.createElement("article");
    card.className = "timeline-card empty-card";

    var heading = document.createElement("h3");
    heading.textContent = title;

    var text = document.createElement("p");
    text.className = "timeline-note";
    text.textContent = copy;

    card.appendChild(heading);
    card.appendChild(text);
    return card;
  }

  function createEmptyCard(title, copy) {
    var card = document.createElement("article");
    card.className = "recommendation-card empty-card";

    var heading = document.createElement("h3");
    heading.textContent = title;

    var text = document.createElement("p");
    text.className = "recommendation-copy";
    text.textContent = copy;

    card.appendChild(heading);
    card.appendChild(text);
    return card;
  }

  function createProjectAdvisorCard(project) {
    var card = document.createElement("article");
    card.className = "project-advisor-card";

    var top = document.createElement("div");
    top.className = "project-advisor-top";

    var titleGroup = document.createElement("div");

    var title = document.createElement("h3");
    title.textContent = project.projectName || "Project opportunity";

    var reason = document.createElement("p");
    reason.className = "project-advisor-copy";
    reason.textContent = project.fitReason || "";

    var typePill = document.createElement("span");
    typePill.className = "timeline-pill " + resolveProjectTypeTone(project.projectType);
    typePill.textContent = project.projectType || "Suggested";

    titleGroup.appendChild(title);
    titleGroup.appendChild(reason);
    top.appendChild(titleGroup);
    top.appendChild(typePill);
    card.appendChild(top);

    card.appendChild(
      createProjectAdvisorSection(
        "Enhance next",
        project.enhancements || [],
        "The advisor will list specific improvements here."
      )
    );
    card.appendChild(
      createProjectAdvisorSection(
        "Add in the CV",
        project.cvAdditions || [],
        "The advisor will suggest the strongest CV bullet additions here."
      )
    );

    return card;
  }

  function createProjectAdvisorSection(title, items, emptyText) {
    var section = document.createElement("section");
    section.className = "project-advisor-section";

    var heading = document.createElement("p");
    heading.className = "project-advisor-subhead";
    heading.textContent = title;

    var list = document.createElement("ul");
    list.className = "insight-list";

    renderList(list, items, emptyText);

    section.appendChild(heading);
    section.appendChild(list);
    return section;
  }

  function createInlineEmptyState(text) {
    var note = document.createElement("p");
    note.className = "empty-copy compact";
    note.textContent = text;
    return note;
  }

  function resolveOutcomeTone(outcome) {
    var normalized = String(outcome || "").toLowerCase();

    if (normalized.indexOf("selected") !== -1) {
      return "selected";
    }

    if (normalized.indexOf("declined") !== -1) {
      return "declined";
    }

    return "rejected";
  }

  function resolveProjectTypeTone(projectType) {
    var normalized = String(projectType || "").toLowerCase();

    if (normalized.indexOf("existing") !== -1) {
      return "selected";
    }

    return "upcoming";
  }

  function renderList(container, items, emptyText) {
    clearContainer(container);

    if (!items.length) {
      var emptyItem = createListItem(emptyText);
      emptyItem.className = "empty-list-item";
      container.appendChild(emptyItem);
      return;
    }

    items.forEach(function (item) {
      container.appendChild(createListItem(item));
    });
  }

  function createListItem(text) {
    var item = document.createElement("li");
    item.textContent = text;
    return item;
  }

  function clearContainer(container) {
    while (container && container.firstChild) {
      container.removeChild(container.firstChild);
    }
  }

  function readJsonResponse(response) {
    return response.text().then(function (text) {
      if (!text) {
        return {};
      }

      try {
        return JSON.parse(text);
      } catch (error) {
        throw new Error("The backend returned invalid JSON.");
      }
    });
  }

  function fetchWithTimeout(url, timeoutMs, options) {
    if (typeof AbortController !== "function") {
      return fetch(url, options);
    }

    var controller = new AbortController();
    var timeoutHandle = setTimeout(function () {
      controller.abort();
    }, timeoutMs);
    var requestOptions = Object.assign({}, options || {}, {
      signal: controller.signal
    });

    return fetch(url, requestOptions).finally(function () {
      clearTimeout(timeoutHandle);
    });
  }

  function trimTrailingSlash(value) {
    return String(value || "").replace(/\/+$/, "");
  }
})();
