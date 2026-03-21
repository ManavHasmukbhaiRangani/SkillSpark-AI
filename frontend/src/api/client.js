/**
 * SkillSpark AI — API Client
 * Axios instance for all backend API calls.
 * All API calls go through this file only.
 */

import axios from "axios";

// ── Base config ───────────────────────────────────────────────────

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request interceptor ───────────────────────────────────────────

client.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor ──────────────────────────────────────────

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      "Something went wrong";
    console.error("API Error:", message);
    return Promise.reject(new Error(message));
  }
);

// ── API functions ─────────────────────────────────────────────────

/**
 * Upload resume or JD file
 * @param {File} file - PDF or DOCX file
 * @returns {Promise} parsed text + sections
 */
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await client.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

/**
 * Analyse skill gaps
 * @param {string} resumeText - parsed resume text
 * @param {string} jdText - job description text
 * @param {string} jobTitle - target job title
 * @param {string} domain - "tech" or "ops"
 * @returns {Promise} gap analysis results
 */
export const analyseGaps = async (
  resumeText,
  jdText,
  jobTitle = "Target Role",
  domain = null
) => {
  const response = await client.post("/analyse", {
    resume_text: resumeText,
    jd_text: jdText,
    job_title: jobTitle,
    domain: domain,
  });
  return response.data;
};

/**
 * Generate learning pathway
 * @param {string} resumeText - parsed resume text
 * @param {string} jdText - job description text
 * @param {string} jobTitle - target job title
 * @param {string} domain - "tech" or "ops"
 * @param {string[]} knownSkills - skills to pre-skip
 * @returns {Promise} complete pathway with modules
 */
export const generatePathway = async (
  resumeText,
  jdText,
  jobTitle = "Target Role",
  domain = "tech",
  knownSkills = []
) => {
  const response = await client.post("/pathway", {
    resume_text: resumeText,
    jd_text: jdText,
    job_title: jobTitle,
    domain: domain,
    known_skills: knownSkills,
  });
  return response.data;
};

/**
 * Skip a skill and recalculate pathway
 * @param {string} skillId - skill to skip
 * @param {string[]} currentPath - current pathway
 * @param {string[]} skipped - already skipped skills
 * @param {string[]} completed - completed skills
 * @returns {Promise} updated pathway state
 */
export const reroutePathway = async (
  skillId,
  currentPath,
  skipped = [],
  completed = []
) => {
  const response = await client.post("/reroute", {
    skill_id: skillId,
    current_path: currentPath,
    skipped: skipped,
    completed: completed,
  });
  return response.data;
};

/**
 * Mark skill as completed
 * @param {string} skillId - skill to complete
 * @param {string[]} currentPath - current pathway
 * @param {string[]} skipped - skipped skills
 * @param {string[]} completed - already completed
 * @returns {Promise} updated pathway state
 */
export const completeSkill = async (
  skillId,
  currentPath,
  skipped = [],
  completed = []
) => {
  const response = await client.post("/complete", {
    skill_id: skillId,
    current_path: currentPath,
    skipped: skipped,
    completed: completed,
  });
  return response.data;
};

/**
 * Health check
 * @returns {Promise} API health status
 */
export const checkHealth = async () => {
  const response = await axios.get(`${API_BASE_URL}/health`);
  return response.data;
};

export default client;