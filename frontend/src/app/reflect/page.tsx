"use client";
import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import dynamic from "next/dynamic";
import useSWR from "swr";
import { reflectAPI, voiceAPI, diaryAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";
import { CardSkeleton } from "@/components/Skeleton";

// GraphView removed in favor of AI Sessions

const SPHERE_NAMES: Record<string, string> = {
    IDENTITY: "Личность", MONEY: "Деньги", RELATIONS: "Отношения",
    FAMILY: "Род", MISSION: "Миссия", HEALTH: "Здоровье", SOCIETY: "Влияние", SPIRIT: "Духовность"
};

const MicIcon = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
);

function ReflectionChatView({
    messages, loading, draft, setDraft, onSend, onFinish, scrollRef,
    isRecording, isTranscribing, startRecording, stopRecording, ready
}: any) {
    const particles = useMemo(() =>
        Array.from({ length: 24 }, (_, i) => ({
            left: `${(i * 37 + 5) % 100}%`,
            top: `${(i * 53 + 10) % 100}%`,
            opacity: 0.04 + (i % 5) * 0.04,
            duration: 2.5 + (i % 4),
            delay: (i % 6) * 0.4,
            size: i % 3 === 0 ? 2 : 1,
        })), []);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
                position: "fixed", inset: 0, display: "flex", flexDirection: "column",
                background: "#060818", zIndex: 50, overflow: "hidden"
            }}
        >
            {/* Background decorative glows */}
            <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 0 }}>
                <div style={{
                    position: "absolute", top: "10%", left: "15%", width: 280, height: 280,
                    background: "radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)",
                    borderRadius: "50%", filter: "blur(40px)"
                }} />
                <div style={{
                    position: "absolute", bottom: "15%", right: "10%", width: 220, height: 220,
                    background: "radial-gradient(circle, rgba(245,158,11,0.10) 0%, transparent 70%)",
                    borderRadius: "50%", filter: "blur(32px)"
                }} />
            </div>

            {/* Particles */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none" style={{ zIndex: 0 }}>
                {particles.map((p: any, i: number) => (
                    <motion.div key={i}
                        className="absolute rounded-full bg-white"
                        style={{ left: p.left, top: p.top, width: p.size, height: p.size, opacity: p.opacity }}
                        animate={{ opacity: [p.opacity, p.opacity * 3, p.opacity] }}
                        transition={{ duration: p.duration, repeat: Infinity, delay: p.delay }}
                    />
                ))}
            </div>

            {/* Top bar */}
            <div style={{ padding: "12px 16px 8px", borderBottom: "1px solid rgba(255,255,255,0.05)", flexShrink: 0, position: "relative", zIndex: 10 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <button
                        onClick={onFinish}
                        className="text-[12px] text-white/30 font-semibold uppercase tracking-widest bg-none border-none cursor-pointer py-1"
                    >
                        ← Назад
                    </button>
                    <span style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", letterSpacing: "0.1em", textTransform: "uppercase" }}>☼ ИИ-рефлексия</span>
                    <span style={{ fontSize: 10, color: "rgba(245,158,11,0.5)", fontWeight: 700 }}>
                        {messages.length > 0 ? `${Math.min(messages.length, 10)}/10` : "0/10"}
                    </span>
                </div>
            </div>

            {/* Chat content area */}
            <div
                ref={scrollRef}
                style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 10, scrollbarWidth: "none", position: "relative", zIndex: 5 }}
                className="custom-scrollbar"
            >
                {messages.map((msg: any, i: number) => (
                    <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}
                    >
                        <div style={{
                            padding: "10px 14px",
                            borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                            maxWidth: "85%", fontSize: 14, lineHeight: 1.5,
                            background: msg.role === "user" ? "rgba(245,158,11,0.18)" : "rgba(255,255,255,0.06)",
                            color: msg.role === "user" ? "#FEF3C7" : "rgba(255,255,255,0.9)",
                            border: msg.role === "user" ? "1px solid rgba(245,158,11,0.15)" : "1px solid rgba(255,255,255,0.08)",
                        }}>
                            {msg.content}
                        </div>
                    </motion.div>
                ))}
                {loading && (
                    <div style={{ display: "flex", justifyContent: "flex-start" }}>
                        <div style={{ padding: "10px 14px", borderRadius: "18px 18px 18px 4px", background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.4)", fontSize: 12 }} className="animate-pulse">
                            Обдумываю...
                        </div>
                    </div>
                )}
            </div>

            {/* Bottom panel */}
            <div style={{ flexShrink: 0, padding: "10px 16px 30px", borderTop: "1px solid rgba(255,255,255,0.05)", background: "#060818", position: "relative", zIndex: 10 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", position: "relative" }}>
                        <div style={{ flex: 1, position: "relative" }}>
                            <textarea
                                rows={1}
                                value={isTranscribing ? "Транскрибирую..." : draft}
                                onChange={(e) => {
                                    setDraft(e.target.value);
                                    e.target.style.height = "auto";
                                    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        onSend();
                                    }
                                }}
                                placeholder="Ваш ответ..."
                                disabled={loading || isTranscribing}
                                style={{
                                    width: "100%", background: "rgba(255,255,255,0.06)",
                                    border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16,
                                    padding: "14px 48px 14px 16px", fontSize: 14, color: "#fff",
                                    outline: "none", resize: "none", lineHeight: "1.5", display: "block",
                                    maxHeight: "120px", fontFamily: "inherit"
                                }}
                                className="placeholder:text-white/20 focus:border-amber-500/50 custom-scrollbar"
                            />
                            <button
                                onClick={onSend}
                                disabled={!draft.trim() || loading || isTranscribing}
                                style={{
                                    position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
                                    width: 32, height: 32, borderRadius: 10, border: "none", cursor: "pointer",
                                    background: "rgba(245,158,11,0.2)", color: "#FCD34D",
                                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16,
                                    opacity: (!draft.trim() || loading) ? 0.3 : 1, transition: "all 0.2s"
                                }}
                            >
                                ↑
                            </button>
                            <AnimatePresence>
                                {isRecording && (
                                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                        style={{ position: "absolute", inset: 0, background: "rgba(245,158,11,0.1)", backdropFilter: "blur(8px)", borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid rgba(245,158,11,0.2)", pointerEvents: "none" }}>
                                        <div style={{ display: "flex", gap: 4 }}>
                                            {[0, 1, 2].map(i => (
                                                <motion.div key={i} style={{ width: 4, height: 16, borderRadius: 4, background: "rgba(251,191,36,0.6)" }}
                                                    animate={{ scaleY: [1, 2, 1] }}
                                                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }} />
                                            ))}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                        <button
                            onPointerDown={startRecording}
                            onPointerUp={stopRecording}
                            onPointerLeave={stopRecording}
                            style={{
                                flexShrink: 0, width: 52, height: 52, borderRadius: 16, cursor: "pointer",
                                background: isRecording ? "#EF4444" : "rgba(255,255,255,0.06)",
                                border: isRecording ? "none" : "1px solid rgba(255,255,255,0.1)",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                transition: "all 0.15s", transform: isRecording ? "scale(0.95)" : "scale(1)"
                            }}
                        >
                            {isRecording ? "🔴" : <MicIcon className="w-5 h-5 text-amber-500/60" />}
                        </button>
                    </div>

                    <div className="flex flex-col gap-3">
                        <button
                            onClick={onFinish}
                            className={`w-full py-4 rounded-2xl font-black text-xs uppercase tracking-widest transition-all ${ready
                                    ? "shadow-xl"
                                    : "opacity-40 grayscale-[0.5]"
                                }`}
                            style={{
                                background: ready
                                    ? "linear-gradient(135deg, #F59E0B, #F97316)"
                                    : "rgba(255,255,255,0.08)",
                                color: ready ? "#fff" : "rgba(255,255,255,0.4)",
                                boxShadow: ready ? "0 4px 24px rgba(245,158,11,0.3)" : "none",
                                border: ready ? "none" : "1px solid rgba(255,255,255,0.1)"
                            }}
                        >
                            {ready ? "Завершить и получить результат" : "Завершить раньше"}
                        </button>
                        <p style={{ textAlign: "center", fontSize: 10, color: "rgba(255,255,255,0.25)", textTransform: "uppercase", letterSpacing: "0.1em", margin: 0 }}>
                            ☼ Идет анализ вашего состояния
                        </p>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}

const useVoiceRecorder = (userId: number | null, setInput: (val: string | ((prev: string) => string)) => void) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const startRecording = useCallback(async () => {
        if (!userId || isRecording || isTranscribing) return;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus" : "audio/webm";

            const recorder = new MediaRecorder(stream, { mimeType });
            chunksRef.current = [];
            recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            recorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                if (chunksRef.current.length === 0) return;
                const blob = new Blob(chunksRef.current, { type: mimeType });
                setIsTranscribing(true);
                try {
                    const res = await voiceAPI.transcribe(userId, blob, "reflection");
                    const transcript = res.data.transcript?.trim();
                    if (transcript) {
                        setInput(prev => typeof prev === 'string' ? (prev ? prev + " " + transcript : transcript) : transcript);
                    }
                } catch (err) {
                    console.error("Transcription error:", err);
                } finally {
                    setIsTranscribing(false);
                }
            };
            recorder.start(100);
            mediaRecorderRef.current = recorder;
            setIsRecording(true);
        } catch (err) {
            console.error("Microphone access error:", err);
            alert("Нет доступа к микрофону");
        }
    }, [isRecording, isTranscribing, userId, setInput]);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    }, [isRecording]);

    return { isRecording, isTranscribing, startRecording, stopRecording };
};

export default function ReflectPage() {
    const { userId, setUser, energy } = useUserStore();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<"main" | "history" | "ai_sessions">("main");
    const [activeFilter, setActiveFilter] = useState<string>("all");
    const [input, setInput] = useState("");
    const [draft, setDraft] = useState("");
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const draftRef = useRef<HTMLTextAreaElement>(null);
    const SPHERES = ["all", "IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"];

    const [isChatting, setIsChatting] = useState(false);
    const [chatMessages, setChatMessages] = useState<{ role: string, content: string }[]>([]);
    const [chatSessionId, setChatSessionId] = useState<number | null>(null);
    const [chatLoading, setChatLoading] = useState(false);
    const [chatReady, setChatReady] = useState(false);
    const chatScrollRef = useRef<HTMLDivElement>(null);

    const { isRecording, isTranscribing, startRecording, stopRecording } = useVoiceRecorder(userId, setInput);
    const { isRecording: isChatRecording, isTranscribing: isChatTranscribing, startRecording: startChatRecording, stopRecording: stopChatRecording } = useVoiceRecorder(userId, (val: any) => {
        setDraft(val);
    });

    // SWR for Reflection history
    const { data: history, mutate: mutateHistory, isValidating: loadingHistory } = useSWR(
        userId && (activeTab === "history" || activeTab === "ai_sessions") ? ["reflect_history", userId, activeFilter] : null,
        () => diaryAPI.getAll(userId!, activeFilter === "all" ? undefined : activeFilter, "reflection").then(res => res.data),
        { revalidateOnFocus: false, dedupingInterval: 5000 }
    );

    useEffect(() => {
        if (chatScrollRef.current) {
            chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
        }
    }, [chatMessages, chatLoading]);

    const handleDraftSubmit = () => {
        if (!draft.trim()) return;
        if (isChatting) {
            handleSendChatMessage();
        } else {
            setInput(prev => prev ? prev + "\n" + draft.trim() : draft.trim());
            setDraft("");
            if (draftRef.current) draftRef.current.style.height = "auto";
        }
    };

    const handleSendChatMessage = async () => {
        if (!userId || !chatSessionId || !draft.trim() || chatLoading) return;
        const msg = draft.trim();
        setDraft("");
        const newHistory = [...chatMessages, { role: "user", content: msg }];
        setChatMessages(newHistory);
        setChatLoading(true);
        try {
            const res = await reflectAPI.chatMessage(userId, chatSessionId, msg);
            setChatMessages([...newHistory, { role: "assistant", content: res.data.ai_response }]);
            setChatReady(res.data.ready || false);
        } catch (e: any) {
            alert("Ошибка связи");
        } finally {
            setChatLoading(false);
        }
    };

    const handleStartChat = async () => {
        if (!userId || !input.trim()) return;
        setLoading(true);
        setChatReady(false); // Reset
        try {
            const res = await reflectAPI.chatStart(userId, input.trim());
            setChatSessionId(res.data.session_id);
            setChatMessages([
                { role: "user", content: input.trim() },
                { role: "assistant", content: res.data.ai_response }
            ]);
            setChatReady(res.data.ready || false);
            setIsChatting(true);
        } catch (e: any) {
            alert(e.response?.data?.detail || "Ошибка запуска сессии");
        } finally {
            setLoading(false);
        }
    };

    const handleFinishChat = async () => {
        if (!userId || !chatSessionId) return;
        setChatLoading(true);
        try {
            const res = await reflectAPI.chatFinish(userId, chatSessionId);
            setIsChatting(false);
            setResult({ ...res.data, mode: 'ai' });
            if (res.data.energy_awarded > 0) {
                setUser({ energy: (energy || 0) + res.data.energy_awarded });
            }
            mutateHistory();
        } catch (e: any) {
            alert("Ошибка завершения сессии");
        } finally {
            setChatLoading(false);
        }
    };

    const handleDraftChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setDraft(e.target.value);
        if (draftRef.current) {
            draftRef.current.style.height = "auto";
            draftRef.current.style.height = `${Math.min(draftRef.current.scrollHeight, 120)}px`;
        }
    };

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 300)}px`;
        }
    }, [input, isTranscribing]);

    const handleSubmitSimple = async () => {
        if (!userId || !input.trim()) return;
        setLoading(true);
        try {
            const res = await reflectAPI.submit(userId, input.trim(), false);
            setResult({ ...res.data, mode: 'diary' });
            mutateHistory();
        } catch (e: any) {
            alert(e.response?.data?.detail || "Ошибка сохранения");
        } finally {
            setLoading(false);
        }
    };

    const getHawkinsColor = (score: number) => {
        if (score <= 200) {
            const ratio = score / 200;
            const r = Math.round(239 + (245 - 239) * ratio);
            const g = Math.round(68 + (158 - 68) * ratio);
            const b = Math.round(68 + (11 - 68) * ratio);
            return `rgb(${r}, ${g}, ${b})`;
        } else {
            const ratio = Math.min(1, (score - 200) / 300);
            const r = Math.round(245 + (16 - 245) * ratio);
            const g = Math.round(158 + (185 - 158) * ratio);
            const b = Math.round(11 + (129 - 11) * ratio);
            return `rgb(${r}, ${g}, ${b})`;
        }
    };

    if (isChatting) return (
        <ReflectionChatView
            messages={chatMessages}
            loading={chatLoading}
            draft={draft}
            setDraft={setDraft}
            onSend={handleSendChatMessage}
            onFinish={handleFinishChat}
            scrollRef={chatScrollRef}
            isRecording={isChatRecording}
            isTranscribing={isChatTranscribing}
            startRecording={startChatRecording}
            stopRecording={stopChatRecording}
            ready={chatReady}
        />
    );

    if (result) return (
        <div className="min-h-screen flex flex-col items-center justify-center px-4 pb-24" style={{ background: "#060818" }}>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
                <div style={{ textAlign: "center", marginBottom: 32 }}>
                    <div style={{ fontSize: 32, marginBottom: 12 }}>{result.mode === 'ai' ? '✨' : '📝'}</div>
                    <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 8, color: "#fff" }}>
                        {result.message}
                    </h2>
                    <p style={{ fontSize: 13, color: "rgba(255,255,255,0.4)" }}>
                        {result.mode === 'ai' ? 'Ваш внутренний компас настроен' : 'Запись сохранена в ваш личный дневник'}
                    </p>
                </div>

                {result.mode === 'ai' && result.analysis && (
                    <div className="mb-6 space-y-4">
                        <div style={{
                            background: "rgba(255,255,255,0.03)", borderRadius: 28, padding: "32px 16px",
                            border: "1px solid rgba(255,255,255,0.05)", textAlign: "center"
                        }}>
                            <p style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", marginBottom: 8, fontWeight: 800, letterSpacing: "0.15em", textTransform: "uppercase" }}>ИТОГОВЫЙ УРОВЕНЬ</p>
                            <div style={{
                                fontSize: 64, fontWeight: 900, color: getHawkinsColor(result.analysis.hawkins_score),
                                lineHeight: 1, fontFamily: "'Outfit', sans-serif", marginBottom: 8
                            }}>
                                {result.analysis.hawkins_score}
                            </div>
                            <p style={{
                                fontSize: 20, fontWeight: 800, color: getHawkinsColor(result.analysis.hawkins_score),
                                textTransform: "uppercase", letterSpacing: "0.1em"
                            }}>
                                {result.analysis.hawkins_level}
                            </p>
                        </div>

                        <div style={{ background: "rgba(139,92,246,0.08)", padding: 16, borderRadius: 20, borderLeft: "4px solid #8B5CF6" }}>
                            <p style={{ fontSize: 10, color: "#A78BFA", fontWeight: 800, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>ИНСАЙТ ОТ ИИ</p>
                            <p style={{ fontSize: 14, color: "#fff", lineHeight: 1.6, margin: 0, fontStyle: "italic" }}>
                                «{result.analysis.ai_analysis}»
                            </p>
                            <div className="mt-3 flex gap-2">
                                <span style={{ fontSize: 9, padding: "2px 8px", borderRadius: 10, background: "rgba(139,92,246,0.1)", color: "#A78BFA", border: "1px solid rgba(139,92,246,0.2)", fontWeight: 800, textTransform: "uppercase" }}>
                                    СФЕРА: {SPHERE_NAMES[result.analysis.sphere] || result.analysis.sphere}
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                <div className="space-y-3">
                    <button onClick={() => { setResult(null); setInput(""); setDraft(""); }}
                        style={{
                            width: "100%", padding: "18px", borderRadius: 20, border: "none",
                            cursor: "pointer", fontSize: 15, fontWeight: 800, textTransform: "uppercase",
                            background: "linear-gradient(135deg, #8B5CF6, #6366F1)", color: "#fff",
                            boxShadow: "0 8px 24px rgba(139,92,246,0.3)",
                        }}>
                        Вернуться
                    </button>
                </div>
            </motion.div>
            <BottomNav active="reflect" />
        </div>
    );

    return (
        <div className="h-screen flex flex-col" style={{ background: "#060818" }}>
            {/* Header: Title */}
            <div className="flex-shrink-0 px-4 pt-6 pb-2">
                <h1 className="text-xl font-bold text-white">Рефлексия</h1>
            </div>

            {/* Header: Tabs */}
            <div className="flex-shrink-0 px-4 mb-4">
                <div
                    className="grid grid-cols-3 gap-1 p-1"
                    style={{
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid var(--border)",
                        borderRadius: 14,
                    }}
                >
                    {(["main", "history", "ai_sessions"] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            style={{
                                padding: "8px 4px",
                                borderRadius: 10,
                                fontSize: 11,
                                fontWeight: 500,
                                transition: "all 0.2s",
                                background: activeTab === tab ? "rgba(255,255,255,0.1)" : "transparent",
                                color: activeTab === tab ? "var(--text-primary)" : "var(--text-muted)",
                                border: "none",
                                cursor: "pointer",
                            }}
                        >
                            {tab === "main" ? "Основные" : tab === "history" ? "История" : "Разбор ИИ"}
                        </button>
                    ))}
                </div>
            </div>

            {/* Scrollable Content Area */}
            <div className="flex-1 overflow-y-auto px-4 pb-32 custom-scrollbar">
                {/* Filter is active for both History and AI Sessions */}
                {(activeTab === "history" || activeTab === "ai_sessions") && (
                    <div className="space-y-4 mb-4">
                        <div className="flex gap-2 overflow-x-auto pb-4 no-scrollbar" style={{ scrollbarWidth: "none" }}>
                            {SPHERES.map(s => (
                                <button key={s} onClick={() => setActiveFilter(s)}
                                    className="flex-none px-3 py-1.5 rounded-full text-[11px] font-medium transition-all whitespace-nowrap"
                                    style={{
                                        background: activeFilter === s ? "rgba(139,92,246,0.1)" : "transparent",
                                        color: activeFilter === s ? "var(--violet-l)" : "var(--text-muted)",
                                        border: `1px solid ${activeFilter === s ? "var(--violet-l)" : "var(--border)"}`,
                                    }}>
                                    {s === "all" ? "Все сферы" : SPHERE_NAMES[s]}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === "main" ? (
                    <div className="h-full flex flex-col pt-2">
                        {/* Text Area (Middle) */}
                        <div className="flex-1 flex flex-col justify-start">
                            <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
                                className="p-5 w-full rounded-[2rem] border border-white/5 relative overflow-hidden"
                                style={{ background: "rgba(255,255,255,0.03)", boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}>

                                <div className="relative">
                                    <textarea
                                        ref={textareaRef}
                                        value={input}
                                        readOnly
                                        placeholder="Здесь будут появляться ваши мысли. Вводите текст в поле ниже..."
                                        className="w-full bg-transparent border-none outline-none text-[14px] leading-relaxed resize-none min-h-[300px] md:min-h-[400px] overflow-y-auto placeholder:text-white/10 font-medium custom-scrollbar"
                                        style={{ color: "rgba(255,255,255,0.9)" }}
                                    />
                                </div>
                            </motion.div>
                        </div>
                    </div>
                ) : activeTab === "history" ? (
                    <div className="space-y-2">
                        {loadingHistory && !history ? (
                            <><CardSkeleton /><CardSkeleton /></>
                        ) : (history?.filter((e: any) => !e.ai_analysis).length === 0) ? (
                            <div className="p-12 text-center opacity-30">
                                <p className="text-3xl mb-2">📜</p>
                                <p className="text-sm">Здесь будут ваши простые записи в дневник</p>
                            </div>
                        ) : (
                            history?.filter((e: any) => !e.ai_analysis).map((entry: any) => (
                                <motion.div key={entry.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                                    className="glass p-3 border border-white/5"
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="flex flex-col gap-0.5">
                                            <span className="text-[10px] text-white/30 uppercase font-bold tracking-widest">
                                                {new Date(entry.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' }).toUpperCase()}
                                            </span>
                                            {entry.hawkins_score && (
                                                <span className="text-2xl font-black leading-none" style={{ color: getHawkinsColor(entry.hawkins_score) }}>{entry.hawkins_score}</span>
                                            )}
                                        </div>
                                        <span className="text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider" style={{ background: "rgba(139,92,246,0.15)", color: "var(--violet-l)" }}>
                                            {SPHERE_NAMES[entry.sphere] || entry.sphere || "Общее"}
                                        </span>
                                    </div>
                                    <p className={`text-sm leading-relaxed ${entry.ai_analysis ? 'mb-1.5' : ''} line-clamp-3`} style={{ color: "var(--text-secondary)" }}>«{entry.content}»</p>
                                    {entry.ai_analysis && (
                                        <div className="rounded-xl p-3" style={{ background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.15)" }}>
                                            <p className="text-[10px] uppercase font-black tracking-[0.2em] mb-1.5" style={{ color: "#68d391" }}>Разбор ИИ</p>
                                            <p className="text-[13px] leading-relaxed text-white/80">{entry.ai_analysis}</p>
                                        </div>
                                    )}
                                </motion.div>
                            ))
                        )}
                    </div>
                ) : (
                    <div className="space-y-2">
                        {loadingHistory && !history ? (
                            <><CardSkeleton /><CardSkeleton /></>
                        ) : (history?.filter((e: any) => e.ai_analysis).length === 0) ? (
                            <div className="p-12 text-center opacity-30">
                                <p className="text-3xl mb-2">✨</p>
                                <p className="text-sm">Здесь будут ваши сессии с ИИ-анализом</p>
                            </div>
                        ) : (
                            history?.filter((e: any) => e.ai_analysis).map((entry: any) => (
                                <motion.div key={entry.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                                    className="glass p-3 border border-white/5"
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="flex flex-col gap-0.5">
                                            <span className="text-[10px] text-white/30 uppercase font-bold tracking-widest">
                                                {new Date(entry.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' }).toUpperCase()}
                                            </span>
                                            <span className="text-2xl font-black leading-none" style={{ color: getHawkinsColor(entry.hawkins_score) }}>{entry.hawkins_score}</span>
                                        </div>
                                        <span className="text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider" style={{ background: "rgba(139,92,246,0.15)", color: "var(--violet-l)" }}>
                                            {SPHERE_NAMES[entry.sphere] || entry.sphere || "Общее"}
                                        </span>
                                    </div>

                                    <p className="text-sm leading-relaxed mb-1.5 text-white/60">«{entry.content}»</p>

                                    <div className="rounded-xl p-3" style={{ background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.15)" }}>
                                        <p className="text-[10px] uppercase font-black tracking-[0.2em] mb-1.5" style={{ color: "#68d391" }}>Разбор ИИ</p>
                                        <p className="text-[13px] leading-relaxed text-white/80">{entry.ai_analysis}</p>
                                    </div>
                                </motion.div>
                            ))
                        )}
                    </div>
                )}
            </div>

            {/* Bottom Controls (Pinned to bottom of screen, above BottomNav) */}
            {activeTab === "main" && (
                <div className="flex-shrink-0 px-4 pb-28 pt-4 bg-gradient-to-t from-[#060818] via-[#060818] to-transparent">
                    <div className="space-y-4">
                        {/* Mic Row */}
                        <div className="flex gap-3 items-end">
                            <div className="flex-1 relative">
                                <textarea
                                    ref={draftRef}
                                    rows={1}
                                    value={draft}
                                    onChange={handleDraftChange}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" && !e.shiftKey) {
                                            e.preventDefault();
                                            handleDraftSubmit();
                                        }
                                    }}
                                    placeholder={isTranscribing ? "Транскрибирую..." : "Ваша мысль..."}
                                    disabled={loading || isTranscribing}
                                    style={{
                                        width: "100%",
                                        background: "rgba(255,255,255,0.06)",
                                        border: "1px solid rgba(255,255,255,0.1)",
                                        borderRadius: 16,
                                        padding: "14px 48px 14px 16px",
                                        fontSize: 14,
                                        color: "#fff",
                                        outline: "none",
                                        fontFamily: "inherit",
                                        boxSizing: "border-box",
                                        resize: "none",
                                        overflowY: "auto",
                                        maxHeight: "120px",
                                        lineHeight: "1.5",
                                        display: "block",
                                    }}
                                    className="placeholder:text-white/20 focus:border-amber-500/50 custom-scrollbar"
                                />
                                <button
                                    onClick={handleDraftSubmit}
                                    disabled={!draft.trim() || loading || isTranscribing}
                                    style={{
                                        position: "absolute", right: 8, bottom: "calc(50% - 16px)",
                                        width: 32, height: 32, borderRadius: 10, border: "none", cursor: "pointer",
                                        background: "rgba(245,158,11,0.2)", color: "#FCD34D",
                                        display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16,
                                        opacity: (!draft.trim() || loading) ? 0.3 : 1,
                                    }}
                                >
                                    ↑
                                </button>
                                <AnimatePresence>
                                    {isRecording && (
                                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                            style={{ position: "absolute", inset: 0, background: "rgba(245,158,11,0.1)", backdropFilter: "blur(8px)", borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid rgba(245,158,11,0.2)", pointerEvents: "none" }}>
                                            <div style={{ display: "flex", gap: 4 }}>
                                                {[0, 1, 2].map(i => (
                                                    <motion.div key={i} style={{ width: 4, height: 16, borderRadius: 4, background: "rgba(251,191,36,0.6)" }}
                                                        animate={{ scaleY: [1, 2, 1] }}
                                                        transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }} />
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                            <button
                                onPointerDown={startRecording}
                                onPointerUp={stopRecording}
                                onPointerLeave={stopRecording}
                                className={`flex-shrink-0 w-[52px] h-[52px] rounded-[16px] flex items-center justify-center transition-all ${isRecording ? "bg-red-500 shadow-[0_0_24px_rgba(239,68,68,0.4)]" : "bg-white/5 border border-white/10"}`}
                            >
                                {isRecording ? "🔴" : (
                                    <svg viewBox="0 0 24 24" fill="none" stroke="rgba(245,158,11,0.6)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-[22px] h-[22px]">
                                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                                        <line x1="12" y1="19" x2="12" y2="23" />
                                        <line x1="8" y1="23" x2="16" y2="23" />
                                    </svg>
                                )}
                            </button>
                        </div>

                        {/* Action Buttons */}
                        <div className="grid grid-cols-1 gap-3">
                            <button
                                onClick={handleSubmitSimple}
                                disabled={!input.trim() || loading || isRecording}
                                className="w-full py-4 rounded-[1.25rem] border border-white/10 bg-white/3 text-white/50 text-sm font-black uppercase tracking-wider transition-all disabled:opacity-30"
                            >
                                Просто запись в дневник 5 ✦
                            </button>
                            <button
                                onClick={handleStartChat}
                                disabled={!input.trim() || loading || isRecording}
                                className="w-full py-4 rounded-[1.25rem] font-black text-sm uppercase tracking-wider transition-all disabled:opacity-20 shadow-[0_4px_24px_rgba(245,158,11,0.3)]"
                                style={{
                                    background: !input.trim() || loading ? "rgba(255,255,255,0.05)" : "linear-gradient(135deg, #F59E0B, #F97316)",
                                    color: !input.trim() || loading ? "rgba(255,255,255,0.2)" : "#fff"
                                }}
                            >
                                {loading ? "Анализирую..." : "Рефлексия с ИИ 20 ✦"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <BottomNav active="reflect" />
        </div>
    );
}
