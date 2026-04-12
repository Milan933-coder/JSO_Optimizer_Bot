(function (root, factory) {
  var data = factory();

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { analyticsFallbackData: data };
  }

  root.analyticsFallbackData = data;
})(
  typeof globalThis !== "undefined" ? globalThis : this,
  function () {
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
      metrics: [
        {
          id: "cv-score",
          label: "CV Strength",
          value: "0/100",
          percent: 0,
          trend: "Awaiting CV analysis",
          tone: "steady",
          description: "This fills after the CV is analyzed."
        },
        {
          id: "github-score",
          label: "GitHub Signal",
          value: "0/100",
          percent: 0,
          trend: "Only scored when the CV shows GitHub proof",
          tone: "steady",
          description: "This stays neutral if the CV does not mention GitHub activity."
        },
        {
          id: "ats-score",
          label: "ATS Match",
          value: "0%",
          percent: 0,
          trend: "Awaiting role alignment analysis",
          tone: "steady",
          description: "Keywords and alignment are generated after CV analysis."
        },
        {
          id: "response-rate",
          label: "Reply Potential",
          value: "0x",
          percent: 0,
          trend: "Awaiting recruiter-readiness estimate",
          tone: "steady",
          description: "The backend will estimate recruiter response strength from the CV."
        }
      ],
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
);
