"use client";

import React, { useEffect, useState } from "react";
import {
  getMonths,
  toggleTopicCompletion,
  getTopicMaterial,
  getClassroomStatus,
  updateCurrentLesson,
  Month,
  Week,
  Topic,
  LessonMaterial,
  ProgressStatus,
} from "../lib/api";

interface SubtitleCue {
  id: string;
  startTime: number;
  endTime: number;
  text: string;
}

function parseVTT(vttText: string): SubtitleCue[] {
  const blocks = vttText.trim().split("\n\n");
  const cues: SubtitleCue[] = [];
  const timestampRegex = /(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})/;

  for (const block of blocks) {
    const lines = block.trim().split("\n");
    if (lines.length < 2) continue;

    let timesLine = lines[0].trim();
    let textLine = lines.slice(1).join(" ").trim();

    if (lines[0].match(/^\d+$/) && lines.length >= 3) {
      timesLine = lines[1].trim();
      textLine = lines.slice(2).join(" ").trim();
    }

    const match = timesLine.match(timestampRegex);
    if (match) {
      const startS = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + parseInt(match[3]) + parseInt(match[4]) / 1000;
      const endS = parseInt(match[5]) * 3600 + parseInt(match[6]) * 60 + parseInt(match[7]) + parseInt(match[8]) / 1000;
      cues.push({
        id: lines[0].trim(),
        startTime: startS,
        endTime: endS,
        text: textLine
      });
    }
  }
  return cues;
}

const MarkdownRenderer: React.FC<{ text: string }> = ({ text }) => {
  if (!text) return null;
  const lines = text.split("\n");
  let inCodeBlock = false;
  let codeLines: string[] = [];

  return (
    <div className="space-y-4 text-gray-300">
      {lines.map((line, idx) => {
        if (line.trim().startsWith("```")) {
          if (inCodeBlock) {
            inCodeBlock = false;
            const codeContent = codeLines.join("\n");
            codeLines = [];
            return (
              <pre key={idx} className="bg-gray-900 border border-gray-800 p-4 rounded-xl font-mono text-sm overflow-x-auto text-indigo-400">
                <code>{codeContent}</code>
              </pre>
            );
          } else {
            inCodeBlock = true;
            return null;
          }
        }

        if (inCodeBlock) {
          codeLines.push(line);
          return null;
        }

        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} className="h-2" />;

        if (trimmed.startsWith("# ")) {
          return (
            <h1 key={idx} className="text-3xl font-bold text-white border-b border-gray-800 pb-2 mt-6">
              {trimmed.substring(2)}
            </h1>
          );
        }

        if (trimmed.startsWith("## ")) {
          return (
            <h2 key={idx} className="text-2xl font-semibold text-indigo-300 mt-5">
              {trimmed.substring(3)}
            </h2>
          );
        }

        if (trimmed.startsWith("### ")) {
          return (
            <h3 key={idx} className="text-xl font-medium text-purple-300 mt-4">
              {trimmed.substring(4)}
            </h3>
          );
        }

        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <li key={idx} className="list-disc list-inside ml-4 text-gray-300">
              {trimmed.substring(2)}
            </li>
          );
        }

        let rawContent = trimmed;
        const boldRegex = /\*\*(.*?)\*\*/g;
        const matches = rawContent.matchAll(boldRegex);
        const parts: React.ReactNode[] = [];
        let lastIdx = 0;

        for (const match of matches) {
          const matchIndex = match.index ?? 0;
          if (matchIndex > lastIdx) {
            parts.push(rawContent.substring(lastIdx, matchIndex));
          }
          parts.push(
            <strong key={matchIndex} className="text-white font-semibold">
              {match[1]}
            </strong>
          );
          lastIdx = matchIndex + match[0].length;
        }
        if (lastIdx < rawContent.length) {
          parts.push(rawContent.substring(lastIdx));
        }

        return (
          <p key={idx} className="leading-relaxed">
            {parts.length > 0 ? parts : rawContent}
          </p>
        );
      })}
    </div>
  );
};

export default function ClassroomDashboard() {
  const [months, setMonths] = useState<Month[]>([]);
  const [status, setStatus] = useState<ProgressStatus>({
    total_topics: 0,
    completed_topics: 0,
    progress_percent: 0.0,
    current_topic_id: null,
  });

  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [material, setMaterial] = useState<LessonMaterial | null>(null);

  const [loadingMonths, setLoadingMonths] = useState(true);
  const [loadingMaterial, setLoadingMaterial] = useState(false);
  const [activeTab, setActiveTab] = useState<"video" | "notes" | "quiz">("video");

  // Subtitles / Media simulation states
  const [subtitles, setSubtitles] = useState<SubtitleCue[]>([]);
  const [activeSubtitle, setActiveSubtitle] = useState<string>("");
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Topic[]>([]);
  const [searching, setSearching] = useState(false);

  const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({});
  const [quizSubmitted, setQuizSubmitted] = useState<Record<number, boolean>>({});
  const [expandedMonths, setExpandedMonths] = useState<Record<number, boolean>>({ 1: true });

  // Capstone Spec generator state parameters
  const [generatingCapstone, setGeneratingCapstone] = useState(false);
  const [capstoneBlueprint, setCapstoneBlueprint] = useState<string>("");

  const maxVideoDuration = subtitles.length > 0 ? subtitles[subtitles.length - 1].endTime : 15;

  useEffect(() => {
    async function loadInitialData() {
      try {
        const monthsData = await getMonths();
        setMonths(monthsData);
        setLoadingMonths(false);

        const statusData = await getClassroomStatus();
        setStatus(statusData);

        if (statusData.current_topic_id) {
          const foundTopic = findTopicInMonths(monthsData, statusData.current_topic_id);
          if (foundTopic) {
            handleSelectTopic(foundTopic);
          }
        } else if (monthsData.length > 0 && monthsData[0].weeks.length > 0 && monthsData[0].weeks[0].topics.length > 0) {
          handleSelectTopic(monthsData[0].weeks[0].topics[0]);
        }
      } catch (err) {
        console.error("Initialization error:", err);
        setLoadingMonths(false);
      }
    }
    loadInitialData();
  }, []);

  // Handle live search typing queries
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const delayDebounce = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await fetch(`http://localhost:8000/api/classroom/search?q=${encodeURIComponent(searchQuery)}`);
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data);
        }
      } catch (e) {
        console.error("Error executing query:", e);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentTime((prev) => {
          const next = prev + 0.1;
          if (next >= maxVideoDuration) {
            setIsPlaying(false);
            return 0;
          }
          return next;
        });
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isPlaying, maxVideoDuration]);

  useEffect(() => {
    const cue = subtitles.find(c => currentTime >= c.startTime && currentTime <= c.endTime);
    setActiveSubtitle(cue ? cue.text : "");
  }, [currentTime, subtitles]);

  function findTopicInMonths(monthsList: Month[], topicId: number): Topic | null {
    for (const m of monthsList) {
      for (const w of m.weeks) {
        for (const t of w.topics) {
          if (t.id === topicId) return t;
        }
      }
    }
    return null;
  }

  const handleSelectTopic = async (topic: Topic) => {
    setSelectedTopic(topic);
    setLoadingMaterial(true);
    setMaterial(null);
    setSubtitles([]);
    setActiveSubtitle("");
    setCurrentTime(0);
    setIsPlaying(false);
    setQuizAnswers({});
    setQuizSubmitted({});
    setActiveTab("video");

    // Auto expand respective curriculum month folder reactively
    const matchMonth = months.find(m => m.weeks.some(w => w.topics.some(t => t.id === topic.id)));
    if (matchMonth) {
      setExpandedMonths(prev => ({ ...prev, [matchMonth.number]: true }));
    }

    try {
      await updateCurrentLesson(topic.id);

      const materialData = await getTopicMaterial(topic.id);
      setMaterial(materialData);

      const subtitlesUrl = `http://localhost:8000/api/topics/${topic.id}/subtitles`;
      const subRes = await fetch(subtitlesUrl);
      if (subRes.ok) {
        const vttText = await subRes.text();
        const parsed = parseVTT(vttText);
        setSubtitles(parsed);
      }
    } catch (err) {
      console.error("Error loading topic materials/subtitles:", err);
    } finally {
      setLoadingMaterial(false);
    }
  };

  const handleToggleCompletion = async () => {
    if (!selectedTopic) return;
    try {
      const toggleRes = await toggleTopicCompletion(selectedTopic.id);
      setSelectedTopic((prev) => (prev ? { ...prev, completed: toggleRes.completed } : null));

      setMonths((prevMonths) =>
        prevMonths.map((m) => ({
          ...m,
          weeks: m.weeks.map((w) => ({
            ...w,
            topics: w.topics.map((t) => (t.id === selectedTopic.id ? { ...t, completed: toggleRes.completed } : t)),
          })),
        }))
      );

      // Also update search results dynamically if they include the toggled item
      setSearchResults(prevResults =>
        prevResults.map(t => t.id === selectedTopic.id ? { ...t, completed: toggleRes.completed } : t)
      );

      const statusData = await getClassroomStatus();
      setStatus(statusData);
    } catch (err) {
      console.error("Error toggling completion:", err);
    }
  };

  const handleSelectAnswer = (qIdx: number, oIdx: number) => {
    if (quizSubmitted[qIdx]) return;
    setQuizAnswers((prev) => ({
      ...prev,
      [qIdx]: oIdx,
    }));
  };

  const handleSubmitQuizQuestion = (qIdx: number) => {
    if (quizAnswers[qIdx] === undefined) return;
    setQuizSubmitted((prev) => ({
      ...prev,
      [qIdx]: true,
    }));
  };

  const handleGenerateCapstone = async () => {
    setGeneratingCapstone(true);
    setCapstoneBlueprint("");
    try {
      const res = await fetch("http://localhost:8000/api/classroom/capstone", {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setCapstoneBlueprint(data.blueprint);
      }
    } catch (e) {
      console.error("Error generating capstone spec:", e);
    } finally {
      setGeneratingCapstone(false);
    }
  };

  const toggleMonthExpand = (monthNumber: number) => {
    setExpandedMonths((prev) => ({
      ...prev,
      [monthNumber]: !prev[monthNumber],
    }));
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden font-sans">
      {/* 1. SIDEBAR */}
      <aside className="w-80 border-r border-gray-900 bg-gray-900/40 flex flex-col h-full flex-shrink-0">
        <div className="p-4 border-b border-gray-900 bg-gray-900/60 backdrop-blur-md">
          <div className="flex items-center space-x-2 text-indigo-400 font-bold text-xl uppercase tracking-wider">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.168.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <span>Classroom Hub</span>
          </div>

          <div className="mt-4 bg-gray-950/80 rounded-xl p-3 border border-gray-800">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Overall Progress</span>
              <span className="font-semibold text-white">{status.progress_percent}%</span>
            </div>
            <div className="w-full bg-gray-850 h-2 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-500 to-purple-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${status.progress_percent}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-gray-500 mt-2 font-mono">
              <span>COMPLETED: {status.completed_topics}/{status.total_topics}</span>
            </div>
          </div>

          {/* Dynamic Search Bar Input */}
          <div className="relative mt-3">
            <div className="flex bg-gray-950 border border-gray-800 rounded-xl overflow-hidden focus-within:border-indigo-505 transition">
              <span className="pl-3 flex items-center text-gray-500">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </span>
              <input
                type="text"
                placeholder="Search semantic concepts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent p-2 text-xs text-white placeholder-gray-500 outline-none"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="pr-3 text-gray-500 hover:text-white text-xs font-bold"
                >
                  ×
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Tree Outline / Search Results view switcher */}
        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-3">
          {searchQuery.trim() ? (
            <div className="space-y-2">
              <div className="text-[10px] uppercase font-bold tracking-widest text-indigo-400 px-2 flex justify-between items-center mb-1">
                <span>Semantic Results</span>
                <span className="font-mono text-gray-600 font-semibold lowercase">hybrid rank</span>
              </div>
              {searching ? (
                <div className="flex flex-col items-center justify-center py-10 space-y-2">
                  <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-[10px] text-gray-500 font-mono">Running hybrid ML search...</span>
                </div>
              ) : searchResults.length > 0 ? (
                searchResults.map((t) => {
                  const isSelected = selectedTopic?.id === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => handleSelectTopic(t)}
                      className={`w-full flex items-start space-x-3 p-3 rounded-xl text-left text-xs transition duration-200 ${isSelected
                        ? "bg-indigo-650 text-white font-medium shadow-md shadow-indigo-900/10"
                        : "bg-gray-900/30 border border-gray-900/60 hover:bg-gray-900/60 text-gray-400 hover:text-gray-200"
                        }`}
                    >
                      <div className="mt-0.5 flex-shrink-0">
                        {t.completed ? (
                          <div className="w-4 h-4 bg-indigo-500 text-gray-950 rounded-full flex items-center justify-center">
                            <svg className="w-3 h-3 text-white font-black" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        ) : (
                          <div className={`w-4 h-4 rounded-full border ${isSelected ? "border-indigo-300" : "border-gray-700"} flex-shrink-0`} />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="leading-snug truncate text-white">{t.content}</p>
                        <p className="text-[8px] text-indigo-400 mt-1 uppercase font-mono tracking-widest">
                          {t.category} • Category
                        </p>
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="text-center py-10 text-xs text-gray-600 italic">
                  No semantic matches found.
                </div>
              )}
            </div>
          ) : loadingMonths ? (
            <div className="flex flex-col items-center justify-center h-48 space-y-2">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-gray-500 font-mono">Loading curriculum...</span>
            </div>
          ) : (
            months.map((m) => {
              const isExpanded = expandedMonths[m.number];
              return (
                <div key={m.id} className="bg-gray-900/20 border border-gray-900/60 rounded-xl overflow-hidden">
                  <button
                    onClick={() => toggleMonthExpand(m.number)}
                    className="w-full text-left p-3 flex justify-between items-center bg-gray-900/40 hover:bg-gray-900/70 transition"
                  >
                    <div>
                      <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest font-mono">Month {m.number}</div>
                      <div className="text-sm font-semibold truncate text-white max-w-[200px]">{m.title}</div>
                    </div>
                    <svg
                      className={`w-4 h-4 text-gray-400 transform transition-transform duration-300 ${isExpanded ? "rotate-90" : ""}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7" />
                    </svg>
                  </button>

                  {isExpanded && (
                    <div className="p-2 bg-gray-950/20 border-t border-gray-900/30 space-y-2">
                      {m.weeks.map((w) => (
                        <div key={w.id} className="space-y-1">
                          <div className="text-[10px] uppercase font-bold tracking-wider text-gray-500 px-2 mt-1">
                            Week {w.number}: {w.title}
                          </div>

                          <div className="space-y-0.5">
                            {w.topics.map((t) => {
                              const isSelected = selectedTopic?.id === t.id;
                              return (
                                <button
                                  key={t.id}
                                  onClick={() => handleSelectTopic(t)}
                                  className={`w-full flex items-start space-x-3 p-2 rounded-lg text-left text-xs transition ${isSelected
                                    ? "bg-indigo-650 text-white font-medium shadow-md shadow-indigo-900/10"
                                    : "hover:bg-gray-900/50 text-gray-400 hover:text-gray-200"
                                    }`}
                                >
                                  <div className="mt-0.5 flex-shrink-0">
                                    {t.completed ? (
                                      <div className="w-4 h-4 bg-indigo-500 text-gray-950 rounded-full flex items-center justify-center">
                                        <svg className="w-3 h-3 text-white font-black" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                        </svg>
                                      </div>
                                    ) : (
                                      <div className={`w-4 h-4 rounded-full border ${isSelected ? "border-indigo-300" : "border-gray-700"} flex-shrink-0`} />
                                    )}
                                  </div>
                                  <span className="leading-tight">{t.content}</span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* 2. MAIN VIEWPANEL */}
      <main className="flex-1 flex flex-col h-full bg-gray-950 overflow-hidden relative">
        {selectedTopic ? (
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-900 bg-gray-950 flex justify-between items-center">
              <div>
                <span className="text-[10px] text-gray-500 font-mono font-bold tracking-widest uppercase">
                  ACTIVE LESSON OBJECTIVE
                </span>
                <h2 className="text-lg font-bold text-white leading-tight">
                  {selectedTopic.content}
                </h2>
              </div>

              <button
                onClick={handleToggleCompletion}
                className={`py-2 px-4 rounded-xl text-xs font-semibold flex items-center space-x-2 transition ${selectedTopic.completed
                  ? "bg-green-600 hover:bg-green-700 text-white"
                  : "bg-indigo-600 hover:bg-indigo-700 text-white"
                  }`}
              >
                {selectedTopic.completed ? (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Completed!</span>
                  </>
                ) : (
                  <span>Mark as Completed</span>
                )}
              </button>
            </div>

            <div className="px-6 border-b border-gray-900 bg-gray-950">
              <div className="flex space-x-6 text-sm font-semibold">
                <button
                  onClick={() => setActiveTab("video")}
                  className={`py-3 border-b-2 transition ${activeTab === "video"
                    ? "border-indigo-500 text-white"
                    : "border-transparent text-gray-500 hover:text-gray-300"
                    }`}
                >
                  Video Lecture Player
                </button>
                <button
                  onClick={() => setActiveTab("notes")}
                  className={`py-3 border-b-2 transition ${activeTab === "notes"
                    ? "border-indigo-500 text-white"
                    : "border-transparent text-gray-500 hover:text-gray-300"
                    }`}
                >
                  Technical Notes
                </button>
                <button
                  onClick={() => setActiveTab("quiz")}
                  className={`py-3 border-b-2 transition ${activeTab === "quiz"
                    ? "border-indigo-500 text-white"
                    : "border-transparent text-gray-500 hover:text-gray-300"
                    }`}
                >
                  MCQ Quiz
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-gray-950">
              {loadingMaterial ? (
                <div className="flex flex-col items-center justify-center h-64 space-y-4">
                  <div className="relative w-12 h-12">
                    <div className="absolute inset-0 border-4 border-indigo-900 rounded-full" />
                    <div className="absolute inset-0 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-semibold text-white">Generating Lecture Content...</p>
                    <p className="text-xs text-gray-500 font-mono mt-1">Connecting to Gemini AI to generate video scripts, notes, list and quizzes.</p>
                  </div>
                </div>
              ) : material ? (
                <div>
                  {activeTab === "video" && (
                    <div className="space-y-6 max-w-4xl">
                      <div className="w-full aspect-video bg-gradient-to-br from-indigo-950/80 to-slate-900 border border-indigo-500/20 rounded-2xl flex flex-col justify-between p-6 shadow-2xl relative overflow-hidden backdrop-blur-md">
                        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.12),transparent_70%)] pointer-events-none" />

                        <div className="flex justify-between items-center z-10">
                          <span className="bg-indigo-500/20 text-indigo-300 text-[10px] font-bold py-1 px-2.5 rounded-full border border-indigo-500/30 tracking-widest font-mono">
                            SYNCHRONIZED WEB VIDEO & CAPTIONS
                          </span>
                          <span className="text-xs text-indigo-400 font-mono">Synced VTT engine</span>
                        </div>

                        <div className="flex-1 flex flex-col justify-center items-center py-6 px-10 z-10 text-center">
                          {isPlaying ? (
                            <div className="flex space-x-1.5 items-end justify-center mb-6 h-6">
                              <span className="w-1.5 bg-indigo-500 rounded-full animate-bounce h-3" style={{ animationDelay: '0.1s' }} />
                              <span className="w-1.5 bg-indigo-400 rounded-full animate-bounce h-5" style={{ animationDelay: '0.3s' }} />
                              <span className="w-1.5 bg-purple-500 rounded-full animate-bounce h-2" style={{ animationDelay: '0.5s' }} />
                              <span className="w-1.5 bg-indigo-500 rounded-full animate-bounce h-4" style={{ animationDelay: '0.2s' }} />
                            </div>
                          ) : (
                            <div className="h-6 mb-6 font-mono text-xs text-gray-500">PAUSED</div>
                          )}

                          {activeSubtitle ? (
                            <div className="px-6 py-3 bg-gray-950/70 border border-gray-800/80 rounded-2xl text-shadow text-base text-gray-100 max-w-xl font-medium shadow-xl backdrop-blur-sm transition-all duration-300">
                              {activeSubtitle}
                            </div>
                          ) : (
                            <div className="px-6 py-3 bg-gray-950/20 border border-transparent italic text-sm text-gray-600 max-w-xl select-none">
                              (Silence)
                            </div>
                          )}
                        </div>

                        <div className="space-y-4 z-10">
                          <div className="flex items-center space-x-4">
                            <span className="text-xs text-gray-500 font-mono w-10 text-right">{formatTime(currentTime)}</span>
                            <input
                              type="range"
                              min="0"
                              max={maxVideoDuration}
                              step="0.1"
                              value={currentTime}
                              onChange={(e) => {
                                setCurrentTime(parseFloat(e.target.value));
                                setIsPlaying(false);
                              }}
                              className="flex-1 accent-indigo-500 h-1 bg-gray-800 rounded-lg cursor-pointer outline-none"
                            />
                            <span className="text-xs text-gray-500 font-mono w-10">{formatTime(maxVideoDuration)}</span>
                          </div>

                          <div className="flex justify-between items-center">
                            <button
                              onClick={() => setIsPlaying(!isPlaying)}
                              className="py-2 px-6 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-2 shadow-md shadow-indigo-650/20 transition-all duration-200"
                            >
                              {isPlaying ? (
                                <>
                                  <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                                  </svg>
                                  <span>Pause Playback</span>
                                </>
                              ) : (
                                <>
                                  <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M8 5v14l11-7z" />
                                  </svg>
                                  <span>Play Lecture</span>
                                </>
                              )}
                            </button>
                            <span className="text-[10px] text-gray-600 font-mono">SYSTEM READY</span>
                          </div>
                        </div>
                      </div>

                      <div className="bg-gray-900/30 border border-gray-900 rounded-2xl p-6 space-y-4">
                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest">
                          Subtitles Outline ({subtitles.length} cues)
                        </h3>
                        <div className="h-48 overflow-y-auto space-y-2.5 font-mono text-xs pr-2">
                          {subtitles.map((cue, idx) => {
                            const isActive = currentTime >= cue.startTime && currentTime <= cue.endTime;
                            return (
                              <div
                                key={cue.id}
                                onClick={() => {
                                  setCurrentTime(cue.startTime);
                                  setIsPlaying(false);
                                }}
                                className={`p-2 border rounded-xl text-left cursor-pointer transition ${isActive
                                  ? "bg-indigo-950/40 border-indigo-500/50 text-indigo-200"
                                  : "bg-gray-950/40 border-gray-900 hover:border-gray-800 text-gray-500"
                                  }`}
                              >
                                <span className="text-[10px] text-indigo-400 mr-2 font-bold">
                                  [{formatTime(cue.startTime)} - {formatTime(cue.endTime)}]
                                </span>
                                {cue.text}
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Month 6 Capstone Spec Generator */}
                      {months.find(m => m.number === 6 && m.weeks.some(w => w.topics.some(t => t.id === selectedTopic.id))) !== undefined && (
                        <div className="bg-gradient-to-br from-indigo-950/40 via-purple-950/20 to-slate-900 border border-indigo-500/20 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-4">
                          <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-3 md:space-y-0">
                            <div>
                              <h3 className="text-base font-bold text-white">Month 6 Portfolio Capstone Spec</h3>
                              <p className="text-xs text-gray-400 mt-1">Generates a tailored portfolio blueprint matching your learning history.</p>
                            </div>
                            <button
                              onClick={handleGenerateCapstone}
                              disabled={generatingCapstone}
                              className="py-2.5 px-6 bg-purple-650 hover:bg-purple-700 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-900/25 transition-all duration-200"
                            >
                              {generatingCapstone ? "Compiling Spec..." : "Generate Capstone Spec"}
                            </button>
                          </div>
                          {capstoneBlueprint && (
                            <div className="border-t border-gray-900 pt-6 mt-4">
                              <MarkdownRenderer text={capstoneBlueprint} />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === "notes" && (
                    <div className="max-w-4xl bg-gray-900/20 border border-gray-900 rounded-2xl p-8 shadow-xl">
                      <MarkdownRenderer text={material.technical_notes} />
                    </div>
                  )}

                  {activeTab === "quiz" && (
                    <div className="max-w-3xl space-y-6">
                      {material.quiz.map((q, qIdx) => {
                        const hasSelected = quizAnswers[qIdx] !== undefined;
                        const isSubmitted = quizSubmitted[qIdx];
                        const selectedAns = quizAnswers[qIdx];
                        const isCorrect = selectedAns === q.correct_answer_idx;

                        return (
                          <div key={qIdx} className="bg-gray-900/30 border border-gray-900 rounded-2xl p-6 space-y-4">
                            <div className="flex justify-between items-start">
                              <span className="text-xs font-mono font-bold text-indigo-400 uppercase tracking-widest">
                                QUESTION {qIdx + 1} OF 3
                              </span>
                              {isSubmitted && (
                                <span className={`text-xs font-bold font-mono px-3 py-1 rounded-full ${isCorrect ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                                  }`}>
                                  {isCorrect ? "CORRECT" : "INCORRECT"}
                                </span>
                              )}
                            </div>
                            <p className="font-semibold text-white text-base">
                              {q.question}
                            </p>

                            <div className="space-y-3">
                              {q.options.map((opt, oIdx) => {
                                const isOptionSelected = selectedAns === oIdx;
                                let cardStyle = "bg-gray-900/60 border-gray-800 hover:border-gray-700 hover:bg-gray-900/80";

                                if (isOptionSelected) {
                                  cardStyle = "bg-indigo-950/40 border-indigo-500 text-indigo-200";
                                }

                                if (isSubmitted) {
                                  if (oIdx === q.correct_answer_idx) {
                                    cardStyle = "bg-green-950/30 border-green-500 text-green-200";
                                  } else if (isOptionSelected && !isCorrect) {
                                    cardStyle = "bg-red-950/30 border-red-500 text-red-200";
                                  } else {
                                    cardStyle = "bg-gray-900/20 border-gray-900 text-gray-600 opacity-60";
                                  }
                                }

                                return (
                                  <button
                                    key={oIdx}
                                    onClick={() => handleSelectAnswer(qIdx, oIdx)}
                                    disabled={isSubmitted}
                                    className={`w-full text-left p-3.5 border rounded-xl flex items-center justify-between text-sm transition ${cardStyle}`}
                                  >
                                    <span>{opt}</span>
                                    {isSubmitted && oIdx === q.correct_answer_idx && (
                                      <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                      </svg>
                                    )}
                                  </button>
                                );
                              })}
                            </div>

                            {!isSubmitted && (
                              <div className="flex justify-end pt-2">
                                <button
                                  onClick={() => handleSubmitQuizQuestion(qIdx)}
                                  disabled={!hasSelected}
                                  className={`py-2 px-6 rounded-xl text-xs font-semibold transition ${hasSelected
                                    ? "bg-indigo-650 hover:bg-indigo-700 text-white"
                                    : "bg-gray-900 text-gray-500 cursor-not-allowed"
                                    }`}
                                >
                                  Submit Question
                                </button>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-center">
                  <p className="text-sm text-gray-400">Failed to render contents for this objective.</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col justify-center items-center p-8 text-center max-w-lg mx-auto">
            <svg className="w-16 h-16 text-gray-700 mb-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.168.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <h3 className="text-xl font-bold text-white">Select a Topic</h3>
            <p className="text-sm text-gray-500 mt-2 leading-relaxed">
              Choose an AI Engineer curriculum objective from the sidebar navigation tree to begin your self-paced interactive learning session.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
