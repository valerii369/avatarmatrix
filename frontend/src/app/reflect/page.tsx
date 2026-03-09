"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import dynamic from "next/dynamic";
import useSWR from "swr";
import { reflectAPI, voiceAPI, diaryAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";
import { CardSkeleton } from "@/components/Skeleton";

const GraphView = dynamic(() => import("./GraphView"), {
    loading: () => <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>
});

const SPHERE_NAMES: Record<string, string> = {
    IDENTITY: "Личность", MONEY: "Деньги", RELATIONS: "Отношения",
    FAMILY: "Род", MISSION: "Миссия", HEALTH: "Здоровье", SOCIETY: "Влияние", SPIRIT: "Духовность"
};

export default function ReflectPage() {
    const { userId, setUser, energy } = useUserStore();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<"main" | "history" | "graph">("main");
    const [activeFilter, setActiveFilter] = useState<string>("all");
    const [timeRange, setTimeRange] = useState<"week" | "month" | "year" | "all">("week");
    const [input, setInput] = useState("");
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const SPHERES = ["all", "IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"];

    const { isRecording, isTranscribing, startRecording, stopRecording } = useVoiceRecorder(userId, setInput);

    // SWR for Reflection history
    const { data: history, mutate: mutateHistory, isValidating: loadingHistory } = useSWR(
        userId && (activeTab === "history" || activeTab === "graph") ? ["reflect_history", userId, activeFilter] : null,
        () => diaryAPI.getAll(userId!, activeFilter === "all" ? undefined : activeFilter, "reflection").then(res => res.data),
        { revalidateOnFocus: false, dedupingInterval: 5000 }
    );

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 300)}px`;
        }
    }, [input, isTranscribing]);

    const handleSubmit = async (useAi: boolean) => {
        if (!userId || !input.trim()) return;
        setLoading(true);
        try {
            const res = await reflectAPI.submit(userId, input.trim(), useAi);
            setResult({ ...res.data, mode: useAi ? 'ai' : 'diary' });
            if (res.data.energy_awarded > 0) {
                setUser({ energy: (energy || 0) + res.data.energy_awarded });
            }
            mutateHistory();
        } catch (e: any) {
            if (e.response?.data?.detail?.includes("уже пройдена")) {
                setResult({ message: "Рефлексия уже пройдена сегодня", energy_awarded: 0 });
            } else {
                alert(e.response?.data?.detail || "Ошибка сохранения");
            }
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

    if (result) return (
        <div className="min-h-screen flex flex-col items-center justify-center px-4 pb-24" style={{ background: "#060818" }}>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
                <div style={{ textAlign: "center", marginBottom: 32 }}>
                    <div style={{ fontSize: 48, marginBottom: 16 }}>{result.mode === 'ai' ? '✨' : '📝'}</div>
                    <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8, color: "#fff" }}>
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
                    <button onClick={() => router.push("/")}
                        style={{
                            width: "100%", padding: "18px", borderRadius: 20, border: "none",
                            cursor: "pointer", fontSize: 15, fontWeight: 800, textTransform: "uppercase",
                            background: "linear-gradient(135deg, #8B5CF6, #6366F1)", color: "#fff",
                            boxShadow: "0 8px 24px rgba(139,92,246,0.3)",
                        }}>
                        Продолжить путь
                    </button>
                    <button onClick={() => { setResult(null); setInput(""); setActiveTab("history"); }}
                        style={{
                            width: "100%", padding: "16px", borderRadius: 20, border: "1px solid rgba(255,255,255,0.1)",
                            background: "rgba(255,255,255,0.03)", color: "rgba(255,255,255,0.4)", fontSize: 14, fontWeight: 700, cursor: "pointer"
                        }}>
                        Смотреть историю
                    </button>
                </div>
            </motion.div>
            <BottomNav active="reflect" />
        </div>
    );

    return (
        <div className="min-h-screen pb-24" style={{ background: "#060818" }}>
            {/* Header normalized */}
            <div className="px-4 pt-6 pb-2">
                <h1 className="text-xl font-bold" style={{ color: "#fff" }}>Рефлексия</h1>
            </div>

            {/* Tab Switcher normalized */}
            <div className="px-4 mb-4">
                <div className="flex p-1 bg-white/5 rounded-2xl border border-white/5">
                    <button
                        onClick={() => setActiveTab("main")}
                        className={`flex-1 py-2 rounded-xl text-[10px] uppercase tracking-widest font-bold transition-all ${activeTab === "main" ? "bg-white/10 text-white" : "text-white/30 hover:text-white/50"}`}
                    >
                        Основные
                    </button>
                    <button
                        onClick={() => setActiveTab("history")}
                        className={`flex-1 py-2 rounded-xl text-[10px] uppercase tracking-widest font-bold transition-all ${activeTab === "history" ? "bg-white/10 text-white" : "text-white/30 hover:text-white/50"}`}
                    >
                        История
                    </button>
                    <button
                        onClick={() => setActiveTab("graph")}
                        className={`flex-1 py-2 rounded-xl text-[10px] uppercase tracking-widest font-bold transition-all ${activeTab === "graph" ? "bg-white/10 text-white" : "text-white/30 hover:text-white/50"}`}
                    >
                        График
                    </button>
                </div>
            </div>

            {/* Sphere & Time range filters for History/Graph */}
            {(activeTab === "history" || activeTab === "graph") && (
                <div className="space-y-4 mb-4">
                    {/* Sphere Filters */}
                    <div className="flex gap-2 px-4 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
                        {SPHERES.map(s => (
                            <button key={s} onClick={() => setActiveFilter(s)}
                                className="flex-none px-3 py-1.5 rounded-full text-[10px] font-bold uppercase transition-all whitespace-nowrap"
                                style={{
                                    background: activeFilter === s ? "#8B5CF6" : "rgba(255,255,255,0.06)",
                                    color: activeFilter === s ? "#fff" : "rgba(255,255,255,0.4)",
                                    border: `1px solid ${activeFilter === s ? "#8B5CF6" : "rgba(255,255,255,0.05)"}`,
                                }}>
                                {s === "all" ? "Все" : SPHERE_NAMES[s]}
                            </button>
                        ))}
                    </div>

                    {/* Time Range Filters for Graph */}
                    {activeTab === "graph" && (
                        <div className="flex gap-2 px-4 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
                            {([
                                { id: 'week', label: 'Неделя' },
                                { id: 'month', label: 'Месяц' },
                                { id: 'year', label: 'Год' },
                                { id: 'all', label: 'Все время' }
                            ] as const).map(r => (
                                <button key={r.id} onClick={() => setTimeRange(r.id)}
                                    className="flex-none px-4 py-1.5 rounded-xl text-[9px] font-bold uppercase transition-all tracking-tighter"
                                    style={{
                                        background: timeRange === r.id ? "rgba(255,255,255,0.15)" : "transparent",
                                        color: timeRange === r.id ? "#fff" : "rgba(255,255,255,0.3)",
                                        border: "1px solid rgba(255,255,255,0.05)"
                                    }}>
                                    {r.label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {activeTab === "main" ? (
                <div className="px-4 flex flex-col items-center">
                    <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
                        className="p-5 w-full max-w-lg rounded-[2rem] border border-white/5 mb-4 relative overflow-hidden"
                        style={{ background: "rgba(255,255,255,0.02)" }}>

                        <div className="relative mb-2">
                            <textarea
                                ref={textareaRef}
                                value={isTranscribing ? "Транскрибирую в текст..." : input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="О чем вы думаете сейчас? Расскажите о своих чувствах или инсайтах..."
                                className="w-full bg-transparent border-none outline-none text-[16px] leading-relaxed resize-none min-h-[160px] overflow-y-auto placeholder:text-white/10 font-medium custom-scrollbar"
                                style={{ color: "rgba(255,255,255,0.9)" }}
                                readOnly={isTranscribing}
                            />

                            <AnimatePresence>
                                {isRecording && (
                                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                        className="absolute inset-0 bg-violet-900/10 backdrop-blur-md rounded-2xl flex items-center justify-center pointer-events-none border border-violet-500/20">
                                        <div className="flex gap-2">
                                            {[0, 1, 2, 3, 4].map(i => (
                                                <motion.div key={i} className="w-1.5 h-10 bg-violet-400 rounded-full"
                                                    animate={{ scaleY: [1, 2.8, 1], opacity: [0.6, 1, 0.6] }}
                                                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.12 }} />
                                            ))}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        <div className="flex items-center justify-between pt-4 border-t border-white/5">
                            <div className="text-left">
                                <p style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 2 }}>
                                    {isRecording ? "Запись..." : (isTranscribing ? "Обработка..." : "Голос")}
                                </p>
                                <p style={{ fontSize: 9, color: "rgba(255,255,255,0.15)", textTransform: "uppercase" }}>
                                    {isRecording ? "Слушаю вас" : (isTranscribing ? "Транскрибирую" : "Удерживайте мик")}
                                </p>
                            </div>

                            <button
                                onPointerDown={startRecording}
                                onPointerUp={stopRecording}
                                onPointerLeave={stopRecording}
                                style={{
                                    width: 56, height: 56, borderRadius: 20, cursor: "pointer",
                                    background: isRecording ? "#EF4444" : "rgba(255,255,255,0.06)",
                                    border: isRecording ? "none" : "1px solid rgba(255,255,255,0.1)",
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    transition: "all 0.15s", transform: isRecording ? "scale(0.95)" : "scale(1)",
                                    boxShadow: isRecording ? "0 0 20px rgba(239, 68, 68, 0.3)" : "none"
                                }}
                            >
                                {isRecording ? "🔴" : (
                                    <svg viewBox="0 0 24 24" fill="none" stroke="#A78BFA" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 24, height: 24 }}>
                                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                                        <line x1="12" y1="19" x2="12" y2="23" />
                                        <line x1="8" y1="23" x2="16" y2="23" />
                                    </svg>
                                )}
                            </button>
                        </div>
                    </motion.div>

                    <div className="w-full max-w-lg space-y-3">
                        <button
                            onClick={() => handleSubmit(true)}
                            disabled={!input.trim() || loading || isRecording}
                            style={{
                                width: "100%", padding: "20px", borderRadius: 24, border: "none",
                                cursor: "pointer", fontSize: 16, fontWeight: 800, textTransform: "uppercase",
                                background: !input.trim() || loading ? "rgba(255,255,255,0.05)" : "linear-gradient(135deg, #8B5CF6, #6366F1)",
                                color: !input.trim() || loading ? "rgba(255,255,255,0.2)" : "#fff",
                                boxShadow: !input.trim() || loading ? "none" : "0 8px 30px rgba(139,92,246,0.3)",
                                transition: "all 0.2s"
                            }}>
                            {loading ? "Анализ..." : "Глубокая рефлексия (ИИ) -15 ✦"}
                        </button>

                        <button
                            onClick={() => handleSubmit(false)}
                            disabled={!input.trim() || loading || isRecording}
                            style={{
                                width: "100%", padding: "16px", borderRadius: 20, border: "1px solid rgba(255,255,255,0.1)",
                                background: "rgba(255,255,255,0.03)", color: "rgba(255,255,255,0.4)",
                                cursor: "pointer", fontSize: 14, fontWeight: 700,
                                transition: "all 0.2s"
                            }}>
                            Просто записать в дневник (0 ✦)
                        </button>
                    </div>

                    <p style={{ marginTop: 24, padding: "0 40px", textAlign: "center", fontSize: 11, color: "rgba(255,255,255,0.15)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", lineHeight: 1.6 }}>
                        Глубокая рефлексия с ИИ дает +25 XP и прогресс по картам архетипов
                    </p>
                </div>
            ) : activeTab === "history" ? (
                <div className="px-4 space-y-4">
                    {loadingHistory && !history ? (
                        <div className="space-y-4">
                            <CardSkeleton />
                            <CardSkeleton />
                        </div>
                    ) : (history && history.length === 0) ? (
                        <div className="p-12 text-center opacity-30">
                            <p className="text-3xl mb-2">📜</p>
                            <p className="text-sm">Здесь будут ваши прошлые рефлексии</p>
                        </div>
                    ) : (
                        history?.map((entry: any) => (
                            <motion.div key={entry.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                className="p-5 rounded-[2rem] border border-white/5 relative overflow-hidden"
                                style={{ background: "rgba(255,255,255,0.02)" }}>

                                <div className="flex justify-between items-start mb-3">
                                    <div className="flex flex-col gap-1">
                                        <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                            {new Date(entry.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
                                        </span>
                                        {entry.hawkins_score && (
                                            <div className="flex items-center gap-2">
                                                <span style={{ fontSize: 20, fontWeight: 900, color: getHawkinsColor(entry.hawkins_score) }}>{entry.hawkins_score}</span>
                                            </div>
                                        )}
                                    </div>
                                    <span style={{ fontSize: 9, padding: "2px 8px", borderRadius: 10, background: "rgba(139,92,246,0.1)", color: "#A78BFA", border: "1px solid rgba(139,92,246,0.2)", fontWeight: 800, textTransform: "uppercase" }}>
                                        {SPHERE_NAMES[entry.sphere] || entry.sphere || "Общее"}
                                    </span>
                                </div>

                                <p style={{ fontSize: 14, color: "rgba(255,255,255,0.8)", lineHeight: 1.5, fontStyle: "italic", marginBottom: 16 }}>
                                    «{entry.content}»
                                </p>

                                {entry.ai_analysis && (
                                    <div style={{ background: "rgba(255,255,255,0.03)", padding: 14, borderRadius: 16, border: "1px solid rgba(255,255,255,0.05)" }}>
                                        <p style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 6 }}>Разбор ИИ</p>
                                        <p style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 1.5 }}>
                                            {entry.ai_analysis}
                                        </p>
                                    </div>
                                )}
                            </motion.div>
                        ))
                    )}
                </div>
            ) : (
                <GraphView
                    history={history || []}
                    loadingHistory={loadingHistory && !history}
                    activeFilter={activeFilter}
                    timeRange={timeRange}
                    sphereNames={SPHERE_NAMES}
                />
            )}

            <BottomNav active="reflect" />
        </div>
    );
}

const useVoiceRecorder = (userId: number | null, setInput: React.Dispatch<React.SetStateAction<string>>) => {
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
                        setInput(prev => prev ? prev + " " + transcript : transcript);
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
