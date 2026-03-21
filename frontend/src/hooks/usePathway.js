/**
 * SkillPathForge AI — usePathway Hook
 * Manages the complete pathway generation state.
 * Handles upload → analyse → generate flow.
 */

import { useState, useCallback } from "react";
import {
  uploadFile,
  analyseGaps,
  generatePathway,
} from "../api/client";

const initialState = {
  // Files
  resumeFile:    null,
  jdFile:        null,
  resumeText:    "",
  jdText:        "",

  // Job info
  jobTitle:      "",
  domain:        null,

  // Analysis results
  gaps:          [],
  strongSkills:  [],
  gapSummary:    null,
  domainResult:  null,

  // Pathway
  modules:       [],
  pathwaySummary: "",
  estimatedImpact: "",
  totalHours:    0,
  hoursSaved:    0,
  usedFallback:  false,

  // UI state
  step:          "upload",   // upload → analyse → pathway
  loading:       false,
  error:         null,
  uploadProgress: 0,
};

export const usePathway = () => {
  const [state, setState] = useState(initialState);

  // ── Update state helper ───────────────────────────────────────
  const update = useCallback((updates) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  // ── Reset everything ──────────────────────────────────────────
  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  // ── Step 1: Upload resume ─────────────────────────────────────
  const uploadResume = useCallback(async (file) => {
    update({ loading: true, error: null });
    try {
      const result = await uploadFile(file);
      update({
        resumeFile: file,
        resumeText: result.raw_text,
        loading:    false,
      });
      return result;
    } catch (err) {
      update({ loading: false, error: err.message });
      throw err;
    }
  }, [update]);

  // ── Step 2: Upload JD ─────────────────────────────────────────
  const uploadJD = useCallback(async (file) => {
    update({ loading: true, error: null });
    try {
      const result = await uploadFile(file);
      update({
        jdFile:  file,
        jdText:  result.raw_text,
        loading: false,
      });
      return result;
    } catch (err) {
      update({ loading: false, error: err.message });
      throw err;
    }
  }, [update]);

  // ── Step 3: Analyse gaps ──────────────────────────────────────
  const analyse = useCallback(async () => {
    // Read current values via functional setState to avoid capturing
    // a stale closure — state spread into the dependency array means
    // any unrelated field change (e.g. loading) re-creates this
    // callback with potentially out-of-date text values.
    let resumeText, jdText, jobTitle, domain;
    setState((prev) => {
      ({ resumeText, jdText, jobTitle, domain } = prev);
      return prev; // no change, just reading
    });

    if (!resumeText || !jdText) {
      update({ error: "Please upload both resume and JD first" });
      return;
    }

    update({ loading: true, error: null, step: "analyse" });

    try {
      const result = await analyseGaps(
        resumeText,
        jdText,
        jobTitle || "Target Role",
        domain,
      );

      update({
        gaps:         result.gaps || [],
        strongSkills: result.strong_skills || [],
        gapSummary:   result.gap_summary,
        domainResult: {
          domain:     result.domain,
          label:      result.domain_label,
          confidence: result.domain_confidence,
        },
        loading: false,
        step:    "pathway",
      });

      return result;
    } catch (err) {
      update({
        loading: false,
        error:   err.message,
        step:    "upload",
      });
      throw err;
    }
  }, [update]);

  // ── Step 4: Generate pathway ──────────────────────────────────
  const generate = useCallback(async (knownSkills = []) => {
    // Same pattern as analyse — read current state values without
    // closing over the state object in the dependency array.
    let resumeText, jdText, jobTitle, domain;
    setState((prev) => {
      ({ resumeText, jdText, jobTitle, domain } = prev);
      return prev;
    });

    update({ loading: true, error: null });

    try {
      const result = await generatePathway(
        resumeText,
        jdText,
        jobTitle || "Target Role",
        domain || "tech",
        knownSkills,
      );

      update({
        modules:          result.modules || [],
        pathwaySummary:   result.pathway_summary || "",
        estimatedImpact:  result.estimated_impact || "",
        totalHours:       result.total_hours || 0,
        hoursSaved:       result.hours_saved || 0,
        usedFallback:     result.used_fallback || false,
        loading:          false,
        step:             "results",
      });

      return result;
    } catch (err) {
      update({ loading: false, error: err.message });
      throw err;
    }
  }, [update]);

  // ── Set job title ─────────────────────────────────────────────
  const setJobTitle = useCallback((title) => {
    update({ jobTitle: title });
  }, [update]);

  // ── Set domain ────────────────────────────────────────────────
  const setDomain = useCallback((domain) => {
    update({ domain });
  }, [update]);

  // ── Set resume/JD text directly (for manual input) ───────────
  const setResumeText = useCallback((text) => {
    update({ resumeText: text });
  }, [update]);

  const setJdText = useCallback((text) => {
    update({ jdText: text });
  }, [update]);

  // ── Clear error ───────────────────────────────────────────────
  const clearError = useCallback(() => {
    update({ error: null });
  }, [update]);

  return {
    // State
    ...state,

    // Actions
    uploadResume,
    uploadJD,
    analyse,
    generate,
    setJobTitle,
    setDomain,
    setResumeText,
    setJdText,
    clearError,
    reset,
  };
};