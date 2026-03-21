/**
 * SkillPathForge AI — Upload Page
 * Step 1: User uploads resume + JD and enters job title.
 */

import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

// ── File Upload Zone ──────────────────────────────────────────────

const UploadZone = ({ label, hint, file, onFile, accept }) => {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) onFile(dropped);
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`
        border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
        transition-all duration-200
        ${dragging
          ? "border-blue-500 bg-blue-50"
          : file
          ? "border-green-500 bg-green-50"
          : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50"
        }
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
      />

      {/* Icon */}
      <div className="text-4xl mb-3">
        {file ? "✅" : dragging ? "📂" : "📄"}
      </div>

      {/* Label */}
      <p className="font-semibold text-gray-700 text-lg mb-1">
        {label}
      </p>

      {/* File name or hint */}
      {file ? (
        <p className="text-green-600 font-medium text-sm">
          {file.name}
        </p>
      ) : (
        <p className="text-gray-400 text-sm">{hint}</p>
      )}
    </div>
  );
};


// ── Main Upload Page ──────────────────────────────────────────────

const Upload = ({ pathwayHook }) => {
  const navigate    = useNavigate();
  const [localError, setLocalError] = useState("");

  const {
    resumeFile, jdFile,
    jobTitle, domain,
    loading, error,
    uploadResume, uploadJD,
    setJobTitle, setDomain,
    analyse, clearError,
  } = pathwayHook;

  // ── Handle resume file ────────────────────────────────────────
  const handleResume = async (file) => {
    setLocalError("");
    try {
      await uploadResume(file);
    } catch (err) {
      setLocalError("Failed to parse resume. Please try PDF or DOCX.");
    }
  };

  // ── Handle JD file ────────────────────────────────────────────
  const handleJD = async (file) => {
    setLocalError("");
    try {
      await uploadJD(file);
    } catch (err) {
      setLocalError("Failed to parse JD. Please try PDF or DOCX.");
    }
  };

  // ── Handle submit ─────────────────────────────────────────────
  const handleSubmit = async () => {
    setLocalError("");
    clearError();

    if (!resumeFile) {
      setLocalError("Please upload your resume.");
      return;
    }
    if (!jdFile) {
      setLocalError("Please upload the job description.");
      return;
    }
    if (!jobTitle.trim()) {
      setLocalError("Please enter the job title.");
      return;
    }

    try {
      await analyse();
      navigate("/dashboard");
    } catch (err) {
      setLocalError(err.message || "Analysis failed. Please try again.");
    }
  };

  const canSubmit = resumeFile && jdFile && jobTitle.trim() && !loading;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">

      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">S</span>
          </div>
          <h1 className="text-xl font-bold text-gray-800">
            SkillPathForge AI
          </h1>
          <span className="text-gray-400 text-sm ml-2">
            Adaptive Onboarding Engine
          </span>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-4xl mx-auto px-6 py-12">

        {/* Hero */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-800 mb-4">
            Find Your Learning Path
          </h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto">
            Upload your resume and job description. Our AI diagnoses
            your skill gaps and generates a personalised learning pathway.
          </p>
        </div>

        {/* Upload card */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">

          {/* Upload zones */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <UploadZone
              label="Your Resume"
              hint="Drag & drop or click to upload PDF / DOCX"
              file={resumeFile}
              onFile={handleResume}
              accept=".pdf,.docx,.doc"
            />
            <UploadZone
              label="Job Description"
              hint="Drag & drop or click to upload PDF / DOCX"
              file={jdFile}
              onFile={handleJD}
              accept=".pdf,.docx,.doc"
            />
          </div>

          {/* Job title input */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Job Title
            </label>
            <input
              type="text"
              placeholder="e.g. Data Scientist, Warehouse Supervisor"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-4 py-3
                         text-gray-700 placeholder-gray-400
                         focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent transition"
            />
          </div>

          {/* Domain selector */}
          <div className="mb-8">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Role Type
              <span className="font-normal text-gray-400 ml-1">
                (auto-detected if not selected)
              </span>
            </label>
            <div className="flex gap-3">
              {[
                { value: null,   label: "Auto detect",      icon: "🔍" },
                { value: "tech", label: "Tech / Desk role",  icon: "💻" },
                { value: "ops",  label: "Ops / Field role",  icon: "🏭" },
              ].map((opt) => (
                <button
                  key={String(opt.value)}
                  onClick={() => setDomain(opt.value)}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-xl border-2
                    text-sm font-medium transition-all
                    ${domain === opt.value
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-gray-200 bg-white text-gray-600 hover:border-blue-300"
                    }
                  `}
                >
                  <span>{opt.icon}</span>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Error message */}
          {(localError || error) && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200
                            rounded-xl text-red-700 text-sm">
              {localError || error}
            </div>
          )}

          {/* Submit button */}
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`
              w-full py-4 rounded-xl font-semibold text-lg transition-all
              ${canSubmit
                ? "bg-blue-600 hover:bg-blue-700 text-white shadow-lg hover:shadow-xl"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
              }
            `}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10"
                    stroke="currentColor" strokeWidth="4" fill="none"/>
                  <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Analysing your profile...
              </span>
            ) : (
              "Analyse My Skills →"
            )}
          </button>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center justify-center gap-2 text-sm text-gray-400">
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded-full bg-blue-600 text-white
                            flex items-center justify-center text-xs font-bold">
              1
            </div>
            <span className="text-blue-600 font-medium">Upload</span>
          </div>
          <div className="w-8 h-px bg-gray-300"/>
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded-full bg-gray-200
                            flex items-center justify-center text-xs font-bold">
              2
            </div>
            <span>Analyse</span>
          </div>
          <div className="w-8 h-px bg-gray-300"/>
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded-full bg-gray-200
                            flex items-center justify-center text-xs font-bold">
              3
            </div>
            <span>Your Pathway</span>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Upload;