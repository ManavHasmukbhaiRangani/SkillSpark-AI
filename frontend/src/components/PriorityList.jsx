/**
 * SkillPathForge AI — Priority List
 * Shows skills ranked by priority score descending.
 * Makes the priority formula visible to judges.
 */

const PriorityList = ({ gaps = [], onSkip }) => {
  if (!gaps.length) return null;

  const sorted = [...gaps].sort(
    (a, b) => b.priority_score - a.priority_score
  );

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-bold text-gray-800">
          Learning Priority
        </h3>
        <p className="text-gray-400 text-sm mt-0.5">
          Ranked by gap × importance weight
        </p>
      </div>

      {/* List */}
      <div className="space-y-3">
        {sorted.map((gap, index) => (
          <PriorityItem
            key={gap.skill_id}
            gap={gap}
            rank={index + 1}
            onSkip={onSkip}
          />
        ))}
      </div>
    </div>
  );
};


// ── Single priority item ──────────────────────────────────────────

const PriorityItem = ({ gap, rank, onSkip }) => {
  const priorityColor =
    gap.priority_score > 0.5  ? "bg-red-500" :
    gap.priority_score > 0.25 ? "bg-amber-500" :
                                 "bg-green-500";

  const rankColor =
    rank === 1 ? "bg-red-100 text-red-700" :
    rank === 2 ? "bg-amber-100 text-amber-700" :
    rank === 3 ? "bg-yellow-100 text-yellow-700" :
                 "bg-gray-100 text-gray-500";

  return (
    <div className="flex items-center gap-4 p-3 rounded-xl
                    hover:bg-gray-50 transition group">

      {/* Rank badge */}
      <div className={`w-7 h-7 rounded-full flex items-center
                       justify-center text-xs font-bold flex-shrink-0
                       ${rankColor}`}>
        {rank}
      </div>

      {/* Skill info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-gray-700 truncate">
            {gap.display_name}
          </span>
          {gap.is_missing && (
            <span className="text-xs px-1.5 py-0.5 rounded
                             bg-red-100 text-red-600 flex-shrink-0">
              Missing
            </span>
          )}
          {gap.quick_win && (
            <span className="text-xs px-1.5 py-0.5 rounded
                             bg-green-100 text-green-600 flex-shrink-0">
              Quick win
            </span>
          )}
        </div>

        {/* Priority bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-gray-100 rounded-full">
            <div
              className={`h-1.5 rounded-full transition-all duration-500
                          ${priorityColor}`}
              style={{
                width: `${Math.min(gap.priority_score * 100, 100)}%`
              }}
            />
          </div>
          <span className="text-xs text-gray-400 flex-shrink-0">
            {gap.priority_score.toFixed(3)}
          </span>
        </div>
      </div>

      {/* Skip button */}
      {onSkip && (
        <button
          onClick={() => onSkip(gap.skill_id)}
          className="opacity-0 group-hover:opacity-100 transition
                     text-xs text-blue-500 hover:text-blue-700
                     font-medium flex-shrink-0 px-2 py-1
                     rounded-lg hover:bg-blue-50"
        >
          Already know
        </button>
      )}
    </div>
  );
};

export default PriorityList;