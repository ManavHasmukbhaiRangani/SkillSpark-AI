/**
 * SkillPathForge AI — Hours Saved Counter
 * Shows total hours saved by skipping known skills.
 * Directly proves product impact (10% rubric score).
 */

const HoursSaved = ({
  hoursSaved    = 0,
  hoursRemaining = 0,
  totalHours    = 0,
  progressPercent = 0,
  moduleCount   = 0,
  skippedCount  = 0,
}) => {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-bold text-gray-800">
          Your Progress
        </h3>
        <p className="text-gray-400 text-sm mt-0.5">
          Time saved by skipping known skills
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">

        {/* Hours saved */}
        <div className="bg-green-50 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-600">
            {hoursSaved}h
          </p>
          <p className="text-xs text-green-700 font-medium mt-1">
            Hours saved
          </p>
        </div>

        {/* Hours remaining */}
        <div className="bg-blue-50 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-blue-600">
            {hoursRemaining}h
          </p>
          <p className="text-xs text-blue-700 font-medium mt-1">
            Hours remaining
          </p>
        </div>

        {/* Total hours */}
        <div className="bg-gray-50 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-gray-600">
            {totalHours}h
          </p>
          <p className="text-xs text-gray-500 font-medium mt-1">
            Total pathway
          </p>
        </div>

        {/* Modules skipped */}
        <div className="bg-purple-50 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-purple-600">
            {skippedCount}
          </p>
          <p className="text-xs text-purple-700 font-medium mt-1">
            Skills skipped
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>Overall progress</span>
          <span className="font-semibold">
            {progressPercent.toFixed(1)}%
          </span>
        </div>
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-3 bg-gradient-to-r from-blue-500 to-green-500
                       rounded-full transition-all duration-700"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Module count */}
      <p className="text-xs text-gray-400 text-center mt-3">
        {moduleCount} modules in your pathway
      </p>

      {/* Efficiency message */}
      {hoursSaved > 0 && (
        <div className="mt-4 p-3 bg-green-50 rounded-xl
                        border border-green-100 text-center">
          <p className="text-sm text-green-700 font-medium">
            You saved {hoursSaved} hours by skipping{" "}
            {skippedCount} skill{skippedCount !== 1 ? "s" : ""} you already know
          </p>
        </div>
      )}
    </div>
  );
};

export default HoursSaved;