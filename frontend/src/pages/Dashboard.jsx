/**
 * SkillSpark AI — Dashboard Page
 * Main results page showing gap analysis + pathway.
 * Combines all 5 UI components in one view.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import GapBarChart from "../components/GapBarChart";
import PriorityList from "../components/PriorityList";
import PathwayGraph from "../components/PathwayGraph";
import TracePanel from "../components/TracePanel";
import HoursSaved from "../components/HoursSaved";
import { useReroute } from "../hooks/useReroute";

const Dashboard = ({ pathwayHook }) => {
  const navigate  = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedModule, setSelectedModule] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  const {
    gaps, gapSummary, strongSkills,
    modules, pathwaySummary, estimatedImpact,
    totalHours, hoursSaved, usedFallback,
    jobTitle, domain, domainResult,
    loading, error,
    generate, reset,
  } = pathwayHook;

  const reroute = useReroute(modules);

  // Sync reroute when modules change
  useEffect(() => {
    if (modules.length) {
      reroute.syncModules(modules);
    }
  }, [modules]);

  // Auto-generate pathway on mount
  useEffect(() => {
    if (gaps.length && !generated && !generating) {
      handleGenerate();
    }
  }, [gaps]);

  // ── Generate pathway ────────────────────────────────────────────
  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generate();
      setGenerated(true);
    } catch (err) {
      console.error("Generation failed:", err);
    }
    setGenerating(false);
  };

  // ── Skip skill ──────────────────────────────────────────────────
  const handleSkip = async (skillId) => {
    try {
      await reroute.skipSkill(skillId);
    } catch (err) {
      console.error("Skip failed:", err);
    }
  };

  // ── Complete skill ──────────────────────────────────────────────
  const handleComplete = async (skillId) => {
    try {
      await reroute.markComplete(skillId);
    } catch (err) {
      console.error("Complete failed:", err);
    }
  };

  // ── If no gaps loaded redirect to upload ───────────────────────
  if (!gaps.length && !loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center
                      justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">
            No analysis data found.
          </p>
          <button
            onClick={() => navigate("/")}
            className="bg-blue-600 text-white px-6 py-3
                       rounded-xl font-medium hover:bg-blue-700"
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: "overview",  label: "Overview"        },
    { id: "pathway",   label: "Pathway Graph"   },
    { id: "trace",     label: "Reasoning Trace" },
    { id: "progress",  label: "My Progress"     },
  ];

  const displayModules = reroute.modules.length
    ? reroute.modules
    : modules;

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">

            {/* Left — logo + title */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg
                              flex items-center justify-center">
                <span className="text-white text-sm font-bold">S</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-800">
                  SkillSpark AI
                </h1>
                <p className="text-xs text-gray-400">
                  {jobTitle} · {domainResult?.label || domain}
                </p>
              </div>
            </div>

            {/* Right — stats + new analysis */}
            <div className="flex items-center gap-4">
              {gapSummary && (
                <div className="hidden md:flex items-center gap-4
                                text-sm">
                  <div className="text-center">
                    <p className="font-bold text-red-600">
                      {gapSummary.missing_skills}
                    </p>
                    <p className="text-gray-400 text-xs">Missing</p>
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-amber-600">
                      {gapSummary.weak_skills}
                    </p>
                    <p className="text-gray-400 text-xs">Weak</p>
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-green-600">
                      {strongSkills.length}
                    </p>
                    <p className="text-gray-400 text-xs">Strong</p>
                  </div>
                </div>
              )}
              <button
                onClick={() => { reset(); navigate("/"); }}
                className="text-sm text-gray-500 hover:text-gray-700
                           border border-gray-200 px-4 py-2
                           rounded-xl hover:bg-gray-50 transition"
              >
                New Analysis
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium
                  transition-all
                  ${activeTab === tab.id
                    ? "bg-blue-600 text-white"
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading overlay */}
      {(loading || generating) && (
        <div className="fixed inset-0 bg-black bg-opacity-30
                        flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 shadow-2xl
                          text-center max-w-sm mx-4">
            <div className="w-12 h-12 border-4 border-blue-600
                            border-t-transparent rounded-full
                            animate-spin mx-auto mb-4"/>
            <p className="text-gray-700 font-semibold">
              Generating your pathway...
            </p>
            <p className="text-gray-400 text-sm mt-1">
              Analysing gaps and building your roadmap
            </p>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Fallback notice */}
        {usedFallback && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200
                          rounded-xl text-amber-700 text-sm">
            Running in offline mode — pathway generated using
            rule-based engine. Connect an API key for richer
            descriptions.
          </div>
        )}

        {/* Error notice */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200
                          rounded-xl text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* ── TAB: Overview ─────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div className="space-y-6">

            {/* Summary cards */}
            {pathwaySummary && (
              <div className="bg-white rounded-2xl shadow-sm
                              border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-800 mb-2">
                  Your Learning Journey
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {pathwaySummary}
                </p>
                {estimatedImpact && (
                  <p className="text-blue-600 font-medium mt-3 text-sm">
                    {estimatedImpact}
                  </p>
                )}
              </div>
            )}

            {/* Gap bar chart */}
            <GapBarChart gaps={gaps} />

            {/* Priority list */}
            <PriorityList
              gaps={gaps}
              onSkip={handleSkip}
            />
          </div>
        )}

        {/* ── TAB: Pathway Graph ────────────────────────────────── */}
        {activeTab === "pathway" && (
          <div className="space-y-6">
            <PathwayGraph
              modules={displayModules}
              onSelectModule={setSelectedModule}
            />

            {/* Selected module detail */}
            {selectedModule && (
              <div className="bg-white rounded-2xl shadow-sm
                              border border-gray-100 p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-bold text-gray-800">
                    {selectedModule.display_name}
                  </h3>
                  <button
                    onClick={() => setSelectedModule(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {selectedModule.reasoning_trace}
                </p>
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={() => {
                      handleSkip(selectedModule.skill_id);
                      setSelectedModule(null);
                    }}
                    className="flex-1 py-2 rounded-xl border
                               border-gray-300 text-gray-600
                               text-sm hover:bg-gray-50 transition"
                  >
                    Already know this
                  </button>
                  <button
                    onClick={() => {
                      handleComplete(selectedModule.skill_id);
                      setSelectedModule(null);
                    }}
                    className="flex-1 py-2 rounded-xl bg-green-600
                               text-white text-sm
                               hover:bg-green-700 transition"
                  >
                    Mark complete ✓
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TAB: Reasoning Trace ──────────────────────────────── */}
        {activeTab === "trace" && (
          <TracePanel
            modules={displayModules}
            onSkip={handleSkip}
            onComplete={handleComplete}
          />
        )}

        {/* ── TAB: Progress ─────────────────────────────────────── */}
        {activeTab === "progress" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <HoursSaved
              hoursSaved={reroute.hoursSaved}
              hoursRemaining={reroute.hoursRemaining}
              totalHours={totalHours}
              progressPercent={reroute.progressPercent}
              moduleCount={displayModules.length}
              skippedCount={reroute.skipped.length}
            />

            {/* Strong skills */}
            {strongSkills.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm
                              border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-800 mb-4">
                  Your Strong Skills
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  These meet or exceed the job requirements
                </p>
                <div className="flex flex-wrap gap-2">
                  {strongSkills.map((skill) => (
                    <span
                      key={skill}
                      className="px-3 py-1.5 bg-green-100
                                 text-green-700 rounded-full
                                 text-sm font-medium"
                    >
                      ✓ {skill.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;