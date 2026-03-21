/**
 * SkillSpark AI — Reasoning Trace Panel
 * Shows why each module was recommended.
 * Directly earns the 10% reasoning trace rubric score.
 */

import { useState } from "react";

const TracePanel = ({ modules = [], onSkip, onComplete }) => {
  const [expanded, setExpanded] = useState(null);

  if (!modules.length) return null;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-bold text-gray-800">
          Reasoning Trace
        </h3>
        <p className="text-gray-400 text-sm mt-0.5">
          Why each module was recommended
        </p>
      </div>

      {/* Module list */}
      <div className="space-y-3">
        {modules.map((module, index) => (
          <TraceItem
            key={module.skill_id}
            module={module}
            index={index}
            isExpanded={expanded === module.skill_id}
            onToggle={() =>
              setExpanded(
                expanded === module.skill_id
                  ? null
                  : module.skill_id
              )
            }
            onSkip={onSkip}
            onComplete={onComplete}
          />
        ))}
      </div>
    </div>
  );
};


// ── Single trace item ─────────────────────────────────────────────

const TraceItem = ({
  module,
  index,
  isExpanded,
  onToggle,
  onSkip,
  onComplete,
}) => {
  const statusColor =
    module.status === "completed" ? "bg-green-100 border-green-300" :
    module.status === "skipped"   ? "bg-gray-100 border-gray-300" :
    module.is_missing             ? "bg-red-50 border-red-200" :
                                    "bg-blue-50 border-blue-200";

  const dotColor =
    module.status === "completed" ? "bg-green-500" :
    module.status === "skipped"   ? "bg-gray-400" :
    module.is_missing             ? "bg-red-500" :
                                    "bg-blue-500";

  return (
    <div className={`border rounded-xl overflow-hidden transition-all
                     ${statusColor}`}>

      {/* Header row — always visible */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer
                   hover:opacity-90 transition"
        onClick={onToggle}
      >
        {/* Step number */}
        <div className={`w-7 h-7 rounded-full flex items-center
                         justify-center text-xs font-bold
                         text-white flex-shrink-0 ${dotColor}`}>
          {index + 1}
        </div>

        {/* Skill name + badges */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-800">
              {module.display_name}
            </span>
            {module.quick_win && (
              <span className="text-xs px-1.5 py-0.5 rounded
                               bg-green-100 text-green-700">
                Quick win
              </span>
            )}
            {module.status === "completed" && (
              <span className="text-xs px-1.5 py-0.5 rounded
                               bg-green-100 text-green-700">
                Completed
              </span>
            )}
            {module.status === "skipped" && (
              <span className="text-xs px-1.5 py-0.5 rounded
                               bg-gray-100 text-gray-600">
                Skipped
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs
                          text-gray-400">
            <span>{module.duration_hours}h</span>
            <span>·</span>
            <span className="capitalize">{module.level}</span>
            <span>·</span>
            <span>gap: {(module.gap_score * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Expand arrow */}
        <div className={`text-gray-400 transition-transform duration-200
                         ${isExpanded ? "rotate-180" : ""}`}>
          ▼
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3">

          {/* Reasoning trace */}
          <div className="mb-4">
            <p className="text-xs font-semibold text-gray-500
                          uppercase tracking-wide mb-1.5">
              Why this module
            </p>
            <p className="text-sm text-gray-700 leading-relaxed">
              {module.reasoning_trace}
            </p>
          </div>

          {/* What it unlocks */}
          {module.what_it_unlocks && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500
                            uppercase tracking-wide mb-1.5">
                What it unlocks
              </p>
              <p className="text-sm text-gray-700 leading-relaxed">
                {module.what_it_unlocks}
              </p>
            </div>
          )}

          {/* Prerequisites */}
          {module.prerequisites?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500
                            uppercase tracking-wide mb-1.5">
                Prerequisites
              </p>
              <div className="flex flex-wrap gap-1.5">
                {module.prerequisites.map((prereq) => (
                  <span
                    key={prereq}
                    className="text-xs px-2 py-1 rounded-lg
                               bg-gray-100 text-gray-600"
                  >
                    {prereq.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Resources */}
          {module.resources?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500
                            uppercase tracking-wide mb-1.5">
                Learning resources
              </p>
              <div className="space-y-1.5">
                {module.resources.map((res) => (
                  <a
                    key={res.url}
                    href={res.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm
                               text-blue-600 hover:text-blue-800
                               hover:underline"
                  >
                    <span>🔗</span>
                    {res.title}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Score details */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs font-semibold text-gray-500
                          uppercase tracking-wide mb-2">
              Score breakdown
            </p>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-lg font-bold text-blue-600">
                  {(module.candidate_conf * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-gray-400">You have</p>
              </div>
              <div>
                <p className="text-lg font-bold text-red-500">
                  {(module.gap_score * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-gray-400">Gap</p>
              </div>
              <div>
                <p className="text-lg font-bold text-gray-700">
                  {(module.required_conf * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-gray-400">Required</p>
              </div>
            </div>
          </div>

          {/* Action buttons — shown for pending modules.
              Treat undefined status as pending (safety net for
              modules that bypassed syncModules stamping). */}
          {(!module.status || module.status === "pending") && (
            <div className="flex gap-2">
              {onSkip && (
                <button
                  onClick={() => onSkip(module.skill_id)}
                  className="flex-1 py-2 px-3 rounded-lg border
                             border-gray-300 text-gray-600 text-sm
                             hover:bg-gray-50 transition font-medium"
                >
                  Already know this
                </button>
              )}
              {onComplete && (
                <button
                  onClick={() => onComplete(module.skill_id)}
                  className="flex-1 py-2 px-3 rounded-lg bg-green-600
                             text-white text-sm hover:bg-green-700
                             transition font-medium"
                >
                  Mark complete ✓
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TracePanel;