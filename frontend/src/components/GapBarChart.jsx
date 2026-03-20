/**
 * SkillPathForge AI — Gap Bar Chart
 * Shows candidate confidence vs required confidence per skill.
 * Makes the confidence scoring formula visible to judges.
 */

const GapBarChart = ({ gaps = [] }) => {
  if (!gaps.length) return null;

  // Sort by gap_score descending
  const sorted = [...gaps].sort((a, b) => b.gap_score - a.gap_score);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-gray-800">
            Skill Gap Analysis
          </h3>
          <p className="text-gray-400 text-sm mt-0.5">
            Candidate confidence vs required level
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-blue-500"/>
            <span className="text-gray-500">You have</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-400"/>
            <span className="text-gray-500">Gap</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-gray-200"/>
            <span className="text-gray-500">Required</span>
          </div>
        </div>
      </div>

      {/* Bars */}
      <div className="space-y-4">
        {sorted.map((gap) => (
          <SkillBar key={gap.skill_id} gap={gap} />
        ))}
      </div>
    </div>
  );
};


// ── Single skill bar ──────────────────────────────────────────────

const SkillBar = ({ gap }) => {
  const candidatePct = Math.round(gap.candidate_confidence * 100);
  const requiredPct  = Math.round(gap.required_confidence * 100);
  const gapPct       = Math.round(gap.gap_score * 100);

  const priorityColor =
    gap.priority_score > 0.5  ? "text-red-600 bg-red-50" :
    gap.priority_score > 0.25 ? "text-amber-600 bg-amber-50" :
                                 "text-green-600 bg-green-50";

  return (
    <div className="group">
      {/* Skill name + badges */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            {gap.display_name}
          </span>
          {gap.is_missing && (
            <span className="text-xs px-2 py-0.5 rounded-full
                             bg-red-100 text-red-600 font-medium">
              Missing
            </span>
          )}
          {gap.is_weak && !gap.is_missing && (
            <span className="text-xs px-2 py-0.5 rounded-full
                             bg-amber-100 text-amber-600 font-medium">
              Needs work
            </span>
          )}
        </div>

        {/* Priority badge */}
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityColor}`}>
          Priority: {gap.priority_score.toFixed(2)}
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative h-7 bg-gray-100 rounded-full overflow-hidden">

        {/* Required level marker */}
        <div
          className="absolute top-0 bottom-0 bg-gray-200 rounded-full"
          style={{ width: `${requiredPct}%` }}
        />

        {/* Candidate level */}
        <div
          className="absolute top-0 bottom-0 bg-blue-500 rounded-full
                     transition-all duration-500"
          style={{ width: `${candidatePct}%` }}
        />

        {/* Gap overlay */}
        {gapPct > 0 && (
          <div
            className="absolute top-0 bottom-0 bg-red-400 opacity-70
                       rounded-r-full"
            style={{
              left:  `${candidatePct}%`,
              width: `${gapPct}%`,
            }}
          />
        )}

        {/* Labels inside bar */}
        <div className="absolute inset-0 flex items-center
                        justify-between px-3">
          <span className="text-xs font-semibold text-white drop-shadow">
            {candidatePct > 0 ? `${candidatePct}%` : "0%"}
          </span>
          <span className="text-xs font-medium text-gray-500">
            Need {requiredPct}%
          </span>
        </div>
      </div>

      {/* Formula display */}
      <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
        <span>
          gap = {requiredPct}% − {candidatePct}% = {gapPct}%
        </span>
        <span>·</span>
        <span>
          priority = {gapPct}% × {gap.importance_weight.toFixed(2)} = {gap.priority_score.toFixed(3)}
        </span>
      </div>
    </div>
  );
};

export default GapBarChart;