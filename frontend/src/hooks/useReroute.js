/**
 * SkillPathForge AI — useReroute Hook
 * Manages skill skip and pathway recalculation state.
 * Called when user marks a skill as already known.
 */

import { useState, useCallback } from "react";
import { reroutePathway, completeSkill } from "../api/client";

export const useReroute = (initialModules = []) => {
  const [modules, setModules] = useState(initialModules);
  const [remainingPath, setRemainingPath] = useState(
    initialModules.map((m) => m.skill_id)
  );
  const [skipped, setSkipped] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [hoursSaved, setHoursSaved] = useState(0);
  const [hoursRemaining, setHoursRemaining] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ── Sync with new modules from parent ────────────────────────
  const syncModules = useCallback((newModules) => {
    const stamped = newModules.map((m) => ({
      ...m,
      status: m.status || "pending",
    }));
    setModules(stamped);
    setRemainingPath(stamped.map((m) => m.skill_id));
    setSkipped([]);
    setCompleted([]);
    setHoursSaved(0);
    setProgressPercent(0);
    const total = stamped.reduce(
      (sum, m) => sum + (m.duration_hours || 0), 0
    );
    setHoursRemaining(total);
  }, []);

  // ── Skip skill ────────────────────────────────────────────────
  const skipSkill = useCallback(async (skillId) => {
    setLoading(true);
    setError(null);

    try {
      const result = await reroutePathway(
        skillId,
        remainingPath,
        skipped,
        completed,
      );

      // Update path state
      setRemainingPath(result.remaining_path || []);
      setSkipped(result.skipped_skills || []);
      setHoursSaved(result.hours_saved || 0);
      setHoursRemaining(result.hours_remaining || 0);
      setProgressPercent(result.progress_percent || 0);

      // Update modules list to reflect new order
      if (result.remaining_path) {
        const remainingIds = new Set(result.remaining_path);
        const skippedIds   = new Set(result.skipped_skills || []);

        setModules((prev) =>
          prev.map((m) => ({
            ...m,
            status: skippedIds.has(m.skill_id)
              ? "skipped"
              : remainingIds.has(m.skill_id)
              ? "pending"
              : m.status,
          }))
        );
      }

      setLoading(false);
      return result;

    } catch (err) {
      setError(err.message);
      setLoading(false);
      throw err;
    }
  }, [remainingPath, skipped, completed]);

  // ── Complete skill ────────────────────────────────────────────
  const markComplete = useCallback(async (skillId) => {
    setLoading(true);
    setError(null);

    try {
      const result = await completeSkill(
        skillId,
        remainingPath,
        skipped,
        completed,
      );

      setRemainingPath(result.remaining_path || []);
      setCompleted(result.completed_skills || []);
      setHoursRemaining(result.hours_remaining || 0);
      setProgressPercent(result.progress_percent || 0);

      // Update module status
      setModules((prev) =>
        prev.map((m) => ({
          ...m,
          status: m.skill_id === skillId
            ? "completed"
            : m.status,
        }))
      );

      setLoading(false);
      return result;

    } catch (err) {
      setError(err.message);
      setLoading(false);
      throw err;
    }
  }, [remainingPath, skipped, completed]);

  // ── Get skill status ──────────────────────────────────────────
  const getSkillStatus = useCallback((skillId) => {
    if (completed.includes(skillId)) return "completed";
    if (skipped.includes(skillId))   return "skipped";
    if (remainingPath.includes(skillId)) return "pending";
    return "unknown";
  }, [completed, skipped, remainingPath]);

  // ── Check if pathway complete ─────────────────────────────────
  const isComplete = remainingPath.length === 0;

  // ── Clear error ───────────────────────────────────────────────
  const clearError = useCallback(() => setError(null), []);

  return {
    // State
    modules,
    remainingPath,
    skipped,
    completed,
    hoursSaved,
    hoursRemaining,
    progressPercent,
    isComplete,
    loading,
    error,

    // Actions
    skipSkill,
    markComplete,
    getSkillStatus,
    syncModules,
    clearError,
  };
};