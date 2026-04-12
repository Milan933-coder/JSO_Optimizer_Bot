(function () {
  var fallbackData = cloneData(window.analyticsFallbackData || {});
  var config = Object.assign(
    {
      apiBaseUrl: "http://localhost:4500",
      preferLiveData: true,
      requestTimeoutMs: 1200
    },
    window.USER_ANALYTICS_CONFIG || {}
  );

  var elements = {
    sourceBadge: document.getElementById("source-badge"),
    sourceMessage: document.getElementById("source-message"),
    candidateName: document.getElementById("candidate-name"),
    candidateTarget: document.getElementById("candidate-target"),
    readinessLabel: document.getElementById("readiness-label"),
    completenessValue: document.getElementById("completeness-value"),
    cvScore: document.getElementById("cv-score"),
    githubScore: document.getElementById("github-score"),
    commitsCount: document.getElementById("commits-count"),
    metricsGrid: document.getElementById("metrics-grid"),
    barSignals: document.getElementById("bar-signals"),
    pieCharts: document.getElementById("pie-charts"),
    cvStrengths: document.getElementById("cv-strengths"),
    cvGaps: document.getElementById("cv-gaps"),
    cvRecommendations: document.getElementById("cv-recommendations"),
    githubHighlights: document.getElementById("github-highlights"),
    githubRecommendations: document.getElementById("github-recommendations"),
    githubLanguages: document.getElementById("github-languages"),
    actionPlan: document.getElementById("action-plan"),
    recruiterHighlights: document.getElementById("recruiter-highlights"),
    footerYear: document.getElementById("footer-year")
  };

  if (elements.footerYear) {
    elements.footerYear.textContent = String(new Date().getFullYear());
  }

  renderDashboard(fallbackData, true);

  loadAnalyticsData()
    .then(function (payload) {
      renderDashboard(payload, false);
    })
    .catch(function () {
      renderDashboard(attachFrontendFallbackMeta(fallbackData), false);
    });

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
      var merged = {};
      var keys = Object.keys(baseValue || {}).concat(Object.keys(overrideValue || {}));

      keys.forEach(function (key) {
        if (Object.prototype.hasOwnProperty.call(merged, key)) {
          return;
        }

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

  function isValidPayload(payload) {
    return (
      isPlainObject(payload) &&
      isPlainObject(payload.profile) &&
      Array.isArray(payload.metrics) &&
      isPlainObject(payload.cvInsights) &&
      isPlainObject(payload.githubInsights) &&
      Array.isArray(payload.actionPlan)
    );
  }

  function attachFrontendFallbackMeta(payload) {
    var cloned = cloneData(payload);
    cloned.meta = deepMerge(cloned.meta || {}, {
      source: "empty",
      usingFallback: true,
      message: "Showing the empty state because no CV analysis has been generated yet."
    });
    return cloned;
  }

  async function loadAnalyticsData() {
    if (!config.preferLiveData || !config.apiBaseUrl || typeof fetch !== "function") {
      return attachFrontendFallbackMeta(fallbackData);
    }

    try {
      var response = await fetchWithTimeout(
        trimTrailingSlash(config.apiBaseUrl) + "/api/analytics/summary",
        config.requestTimeoutMs
      );

      if (!response.ok) {
        throw new Error("Analytics request failed.");
      }

      var livePayload = await response.json();

      if (!isValidPayload(livePayload)) {
        throw new Error("Analytics payload is incomplete.");
      }

      return deepMerge(fallbackData, livePayload);
    } catch (error) {
      return attachFrontendFallbackMeta(fallbackData);
    }
  }

  function fetchWithTimeout(url, timeoutMs) {
    if (typeof AbortController !== "function") {
      return fetch(url);
    }

    var controller = new AbortController();
    var timeoutHandle = setTimeout(function () {
      controller.abort();
    }, timeoutMs);

    return fetch(url, { signal: controller.signal }).finally(function () {
      clearTimeout(timeoutHandle);
    });
  }

  function trimTrailingSlash(value) {
    return value.replace(/\/+$/, "");
  }

  function setText(element, value) {
    if (element) {
      element.textContent = value;
    }
  }

  function setSource(meta, loading) {
    if (!elements.sourceBadge || !elements.sourceMessage) {
      return;
    }

    if (loading) {
      elements.sourceBadge.textContent = "Loading data";
      elements.sourceBadge.className = "status-badge pending";
      elements.sourceMessage.textContent =
        "Preparing the dashboard. If no saved CV analysis is available, the empty state will be used.";
      return;
    }

    var usingFallback = !meta || meta.usingFallback;
    elements.sourceBadge.textContent = usingFallback
      ? "Empty state"
      : "Live backend data";
    elements.sourceBadge.className = usingFallback
      ? "status-badge fallback"
      : "status-badge live";
    elements.sourceMessage.textContent = meta && meta.message ? meta.message : "";
  }

  function renderDashboard(data, loading) {
    var safeData =
      data && Object.keys(data).length ? data : attachFrontendFallbackMeta(fallbackData);
    var profile = safeData.profile || {};
    var cvInsights = safeData.cvInsights || {};
    var githubInsights = safeData.githubInsights || {};
    var visualAnalytics = safeData.visualAnalytics || {};

    setSource(safeData.meta, loading);
    setText(elements.candidateName, profile.candidateName || "Waiting for CV");
    setText(
      elements.candidateTarget,
      [profile.targetRole, profile.targetLocation].filter(Boolean).join(" | ")
    );
    setText(
      elements.readinessLabel,
      profile.readinessLabel || "Paste a CV to generate a readiness snapshot."
    );
    setText(elements.completenessValue, String(profile.profileCompleteness || 0) + "%");
    setText(elements.cvScore, String(cvInsights.score || 0));
    setText(elements.githubScore, String(githubInsights.score || 0));
    setText(elements.commitsCount, String(githubInsights.commitsLast30Days || 0));

    renderMetricCards(safeData.metrics || []);
    renderBarSignals(visualAnalytics.barInsights || []);
    renderPieCharts(visualAnalytics.pieCharts || []);
    renderBulletList(elements.cvStrengths, cvInsights.strengths || []);
    renderBulletList(elements.cvGaps, cvInsights.gaps || []);
    renderRecommendationCards(elements.cvRecommendations, cvInsights.recommendations || []);
    renderBulletList(elements.githubHighlights, githubInsights.highlights || []);
    renderBulletList(elements.githubRecommendations, githubInsights.recommendations || []);
    renderLanguageChips(elements.githubLanguages, githubInsights.topLanguages || []);
    renderActionPlan(elements.actionPlan, safeData.actionPlan || []);
    renderBulletList(elements.recruiterHighlights, safeData.recruiterHighlights || []);
  }

  function renderMetricCards(metrics) {
    clearContainer(elements.metricsGrid);

    metrics.forEach(function (metric) {
      var article = document.createElement("article");
      article.className = "metric-card tone-" + (metric.tone || "steady");

      var header = document.createElement("div");
      header.className = "metric-header";

      var label = document.createElement("p");
      label.className = "eyebrow";
      label.textContent = metric.label || "Metric";

      var value = document.createElement("h3");
      value.className = "metric-value";
      value.textContent = metric.value || "--";

      var trend = document.createElement("p");
      trend.className = "metric-trend";
      trend.textContent = metric.trend || "";

      var description = document.createElement("p");
      description.className = "card-copy";
      description.textContent = metric.description || "";

      var barTrack = document.createElement("div");
      barTrack.className = "metric-bar-track";

      var barFill = document.createElement("span");
      barFill.className = "metric-bar-fill tone-" + (metric.tone || "steady");
      barFill.style.width = String(clampPercent(metric.percent, metric.value)) + "%";

      barTrack.appendChild(barFill);
      header.appendChild(label);
      header.appendChild(value);
      article.appendChild(header);
      article.appendChild(trend);
      article.appendChild(description);
      article.appendChild(barTrack);
      elements.metricsGrid.appendChild(article);
    });
  }

  function renderBarSignals(items) {
    clearContainer(elements.barSignals);

    items.forEach(function (item) {
      var row = document.createElement("div");
      row.className = "signal-row";

      var header = document.createElement("div");
      header.className = "signal-header";

      var name = document.createElement("span");
      name.className = "signal-name";
      name.textContent = item.label || "Signal";

      var value = document.createElement("strong");
      value.textContent = String(clampPercent(item.value)) + "%";

      var note = document.createElement("p");
      note.className = "signal-note";
      note.textContent = item.note || "";

      var track = document.createElement("div");
      track.className = "signal-track";

      var fill = document.createElement("span");
      fill.className = "signal-fill tone-" + (item.tone || "blue");
      fill.style.width = String(clampPercent(item.value)) + "%";

      header.appendChild(name);
      header.appendChild(value);
      track.appendChild(fill);
      row.appendChild(header);
      row.appendChild(track);
      row.appendChild(note);
      elements.barSignals.appendChild(row);
    });
  }

  function renderPieCharts(charts) {
    clearContainer(elements.pieCharts);

    charts.forEach(function (chart) {
      var normalizedSegments = normalizeSegments(chart.segments || []);
      var article = document.createElement("article");
      article.className = "chart-card";

      var header = document.createElement("div");
      header.className = "chart-card-header";

      var title = document.createElement("h3");
      title.textContent = chart.title || "Pie Chart";

      var subtitle = document.createElement("p");
      subtitle.className = "card-copy";
      subtitle.textContent = chart.subtitle || "";

      var visual = document.createElement("div");
      visual.className = "pie-visual";

      var ring = document.createElement("div");
      ring.className = "pie-ring";
      ring.style.backgroundImage = buildPieGradient(normalizedSegments);

      var center = document.createElement("div");
      center.className = "pie-center";

      var total = document.createElement("strong");
      total.className = "pie-total";
      total.textContent = chart.totalValue || String(sumSegmentValues(normalizedSegments));

      var unit = document.createElement("span");
      unit.className = "pie-unit";
      unit.textContent = chart.totalUnit || "total";

      center.appendChild(total);
      center.appendChild(unit);
      ring.appendChild(center);
      visual.appendChild(ring);

      var legend = document.createElement("div");
      legend.className = "legend-list";

      normalizedSegments.forEach(function (segment) {
        var row = document.createElement("div");
        row.className = "legend-row";

        var key = document.createElement("div");
        key.className = "legend-key";

        var swatch = document.createElement("span");
        swatch.className = "legend-swatch";
        swatch.style.backgroundColor = segment.color;
        swatch.style.color = segment.color;

        var label = document.createElement("span");
        label.className = "legend-label";
        label.textContent = segment.label;

        var value = document.createElement("strong");
        value.className = "legend-value";
        value.textContent = String(segment.value) + "%";

        key.appendChild(swatch);
        key.appendChild(label);
        row.appendChild(key);
        row.appendChild(value);
        legend.appendChild(row);
      });

      var insight = document.createElement("p");
      insight.className = "card-copy";
      insight.textContent = chart.insight || "";

      header.appendChild(title);
      header.appendChild(subtitle);
      article.appendChild(header);
      article.appendChild(visual);
      article.appendChild(legend);
      article.appendChild(insight);
      elements.pieCharts.appendChild(article);
    });
  }

  function normalizeSegments(segments) {
    var safeSegments = segments.filter(function (segment) {
      return segment && Number(segment.value) > 0;
    });

    var total = sumSegmentValues(safeSegments);

    if (!total) {
      return [];
    }

    return safeSegments.map(function (segment, index) {
      var value = Number(segment.value);
      var normalizedValue =
        index === safeSegments.length - 1
          ? Math.max(0, 100 - sumSegmentValuesFromIndex(safeSegments, index))
          : Math.round((value / total) * 100);

      return {
        label: segment.label || "Segment",
        value: normalizedValue,
        color: segment.color || fallbackColor(index)
      };
    });
  }

  function sumSegmentValues(segments) {
    return segments.reduce(function (sum, segment) {
      return sum + Number(segment.value || 0);
    }, 0);
  }

  function sumSegmentValuesFromIndex(segments, stopIndexExclusive) {
    return segments.slice(0, stopIndexExclusive).reduce(function (sum, segment) {
      return sum + Math.round((Number(segment.value || 0) / sumSegmentValues(segments)) * 100);
    }, 0);
  }

  function buildPieGradient(segments) {
    if (!segments.length) {
      return "conic-gradient(#22365f 0deg 360deg)";
    }

    var angle = 0;
    var stops = segments.map(function (segment) {
      var start = angle;
      var sweep = (segment.value / 100) * 360;
      angle += sweep;
      return segment.color + " " + start + "deg " + angle + "deg";
    });

    return "conic-gradient(" + stops.join(", ") + ")";
  }

  function fallbackColor(index) {
    var palette = ["#39c4ff", "#47d88f", "#9677ff", "#1f4aa8", "#ff7ad9"];
    return palette[index % palette.length];
  }

  function clampPercent(value, fallbackValue) {
    var numericValue =
      typeof value === "number"
        ? value
        : Number.parseInt(value || fallbackValue || "0", 10);

    if (!Number.isFinite(numericValue)) {
      return 0;
    }

    return Math.max(0, Math.min(100, numericValue));
  }

  function renderBulletList(container, items) {
    clearContainer(container);

    items.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = item;
      container.appendChild(li);
    });
  }

  function renderRecommendationCards(container, items) {
    clearContainer(container);

    items.forEach(function (item) {
      var card = document.createElement("article");
      card.className = "mini-card";

      var priority = document.createElement("span");
      priority.className = "priority-tag";
      priority.textContent = item.priority || "Info";

      var title = document.createElement("h4");
      title.textContent = item.title || "Recommendation";

      var detail = document.createElement("p");
      detail.className = "card-copy";
      detail.textContent = item.detail || "";

      card.appendChild(priority);
      card.appendChild(title);
      card.appendChild(detail);
      container.appendChild(card);
    });
  }

  function renderLanguageChips(container, languages) {
    clearContainer(container);

    languages.forEach(function (language) {
      var chip = document.createElement("span");
      chip.className = "language-chip";
      chip.textContent = language;
      container.appendChild(chip);
    });
  }

  function renderActionPlan(container, items) {
    clearContainer(container);

    items.forEach(function (item) {
      var card = document.createElement("article");
      card.className = "timeline-card";

      var windowLabel = document.createElement("p");
      windowLabel.className = "eyebrow";
      windowLabel.textContent = item.window || "Soon";

      var title = document.createElement("h4");
      title.textContent = item.title || "Action item";

      var detail = document.createElement("p");
      detail.className = "card-copy";
      detail.textContent = item.detail || "";

      var effort = document.createElement("p");
      effort.className = "effort";
      effort.textContent = "Estimated effort: " + (item.effort || "TBD");

      card.appendChild(windowLabel);
      card.appendChild(title);
      card.appendChild(detail);
      card.appendChild(effort);
      container.appendChild(card);
    });
  }

  function clearContainer(container) {
    if (!container) {
      return;
    }

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
  }
})();
