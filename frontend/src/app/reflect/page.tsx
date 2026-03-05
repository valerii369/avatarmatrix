"use client";
import { useState, useCallback, useRef } from "react";
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

const MicIcon = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
);

export default function ReflectPage() {
    const { userId, setUser, energy } = useUserStore();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<"main" | "history" | "graph">("main");
    const [activeFilter, setActiveFilter] = useState<string>("all");
    const [timeRange, setTimeRange] = useState<"week" | "month" | "year" | "all">("week");
    const [input, setInput] = useState("");
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const SPHERES = ["all", "IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"];

    const { isRecording, isTranscribing, startRecording, stopRecording } = useVoiceRecorder(userId, setInput);

    // SWR for Reflection history
    const { data: history, isValidating: loadingHistory } = useSWR(
        userId && (activeTab === "history" || activeTab === "graph") ? ["reflect_history", userId, activeFilter] : null,
        () => diaryAPI.getAll(userId!, activeFilter === "all" ? undefined : activeFilter, "reflection").then(res => res.data),
        { revalidateOnFocus: false, dedupingInterval: 5000 }
    );

    const handleSubmit = async () => {
        if (!userId || !input.trim()) return;
        setLoading(true);
        try {
            const res = await reflectAPI.submit(userId, input.trim());
            setResult(res.data);
            if (res.data.energy_awarded > 0) {
                setUser({ energy: (energy || 0) + res.data.energy_awarded });
            }
        } catch (e: any) {
            if (e.response?.data?.detail?.includes("уже пройдена")) {
                setResult({ message: "Рефлексия уже пройдена сегодня", energy_awarded: 0 });
            }
        } finally {
            setLoading(false);
        }
    };

    if (result) return (
        <div className="min-h-screen flex flex-col items-center justify-center px-6 pb-24" style={{ background: "var(--bg-deep)" }}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                className="glass-strong p-8 text-center w-full max-w-sm rounded-[2rem] border border-white/10 shadow-2xl">
                <div className="text-5xl mb-6">✨</div>
                <h2 className="text-xl font-bold mb-4 gradient-text">{result.message}</h2>

                {result.analysis && (
                    <div className="mb-6 space-y-4">
                        <div className="bg-white/5 rounded-2xl p-4">
                            <p className="text-[10px] uppercase tracking-widest text-white/40 mb-1">Уровень сегодня</p>
                            <div className="text-3xl font-black text-violet-400 mb-1">
                                {result.analysis.hawkins_score}
                            </div>
                            <p className="text-sm font-bold text-white/80">{result.analysis.hawkins_level}</p>
                        </div>

                        <div className="bg-white/5 rounded-2xl p-4 text-left border-l-4 border-violet-500">
                            <p className="text-[10px] uppercase tracking-widest text-white/40 mb-2">Инсайт от ИИ</p>
                            <p className="text-sm italic leading-relaxed text-white/70">
                                «{result.analysis.ai_analysis}»
                            </p>
                            <div className="mt-3 flex gap-2">
                                <span className="text-[9px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20">
                                    СФЕРА: {SPHERE_NAMES[result.analysis.sphere] || result.analysis.sphere}
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                <button onClick={() => router.push("/")}
                    className="w-full py-4 rounded-2xl font-bold shadow-lg shadow-violet-500/20 mb-3"
                    style={{ background: "linear-gradient(135deg, var(--violet), #6366f1)", color: "#fff" }}>
                    Продолжить путь
                </button>
                <button onClick={() => { setResult(null); setInput(""); setActiveTab("history"); }}
                    className="w-full py-4 rounded-2xl font-bold border border-white/10 hover:bg-white/5 transition-colors text-white/60">
                    Смотреть историю
                </button>
            </motion.div>
            <BottomNav active="reflect" />
        </div>
    );

    return (
        <div className="min-h-screen pb-24">
            {/* Header matches Diary styling */}
            <div className="px-4 pt-6 pb-3">
                <h1 className="text-xl font-bold gradient-text">Рефлексия</h1>
            </div>

            {/* Tab Switcher */}
            <div className="px-4 mb-3">
                <div className="flex p-1 bg-white/5 rounded-2xl border border-white/5">
                    <button
                        onClick={() => setActiveTab("main")}
                        className={`flex-1 py-2 rounded-xl text-[10px] uppercase tracking-widest font-bold transition-all ${activeTab === "main" ? "bg-white/10 text-white shadow-lg" : "text-white/30 hover:text-white/50"}`}
                    >
                        Главная
                    </button>
                    <button
                        onClick={() => setActiveTab("history")}
                        className={`flex-1 py-2 rounded-xl text-[10px] uppercase tracking-widest font-bold transition-all ${activeTab === "history" ? "bg-white/10 text-white shadow-lg" : "text-white/30 hover:text-white/50"}`}
                    >
                        История
                    </button>
                    <button
                        onClick={() => setActiveTab("graph")}
                        className={`flex-1 py-2 rounded-xl text-[10px] uppercase tracking-widest font-bold transition-all ${activeTab === "graph" ? "bg-white/10 text-white shadow-lg" : "text-white/30 hover:text-white/50"}`}
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
                                    background: activeFilter === s ? "var(--violet)" : "rgba(255,255,255,0.06)",
                                    color: activeFilter === s ? "#fff" : "var(--text-muted)",
                                    border: `1px solid ${activeFilter === s ? "var(--violet)" : "var(--border)"}`,
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
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                        className="glass-strong p-6 w-full max-w-lg rounded-[2rem] border border-white/5 mb-6 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-violet-600/5 blur-[50px] -z-1" />

                        <h2 className="text-[12px] font-bold text-white/20 uppercase tracking-[0.2em] mb-4">О чем вы думаете сейчас?</h2>

                        <div className="relative mb-4">
                            <textarea
                                value={isTranscribing ? "🎤 Обрабатываю голос..." : input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="О чем вы думаете сейчас? Расскажите о своих чувствах или инсайтах. ИИ проанализирует глубину..."
                                className="w-full bg-transparent border-none outline-none text-white/90 text-[16px] leading-relaxed resize-none h-[160px] overflow-y-auto placeholder:text-white/20 font-medium custom-scrollbar"
                                readOnly={isTranscribing}
                            />

                            <AnimatePresence>
                                {isRecording && (
                                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                        className="absolute inset-0 bg-violet-900/10 backdrop-blur-md rounded-[1.5rem] flex items-center justify-center pointer-events-none border border-violet-500/20">
                                        <div className="flex gap-2">
                                            {[0, 1, 2, 3, 4].map(i => (
                                                <motion.div key={i} className="w-1 h-8 bg-violet-400/60 rounded-full"
                                                    animate={{ scaleY: [1, 2.5, 1], opacity: [0.4, 1, 0.4] }}
                                                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.12 }} />
                                            ))}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        <div className="flex items-center justify-between mt-3 pt-4 border-t border-white/5 flex-row-reverse">
                            <button
                                onPointerDown={startRecording}
                                onPointerUp={stopRecording}
                                onPointerLeave={stopRecording}
                                className={`group relative p-4 rounded-full transition-all duration-300 ${isRecording ? "bg-red-500 scale-110 shadow-[0_0_20px_rgba(239,68,68,0.4)]" : "bg-white/5 hover:bg-white/10"}`}
                            >
                                <div className={`w-6 h-6 transition-transform duration-300 flex items-center justify-center ${isRecording ? "scale-110" : "group-hover:scale-110"}`}>
                                    {isRecording ? "🔴" : (
                                        <MicIcon className="w-full h-full text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]" />
                                    )}
                                </div>
                                {isRecording && (
                                    <motion.div
                                        layoutId="pulse"
                                        className="absolute inset-0 rounded-full border-2 border-red-500"
                                        animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                                        transition={{ duration: 1.5, repeat: Infinity }}
                                    />
                                )}
                            </button>

                            <div className="text-left">
                                <p className="text-[10px] text-white/20 uppercase tracking-[0.2em] font-bold mb-1">
                                    {isRecording ? "Идет запись" : "Голосовой ввод"}
                                </p>
                                <p className="text-[9px] text-white/10 uppercase tracking-widest">
                                    {isRecording ? "Слушаю вас..." : "Зажмите кнопку"}
                                </p>
                            </div>
                        </div>
                    </motion.div>

                    <button
                        onClick={handleSubmit}
                        disabled={!input.trim() || loading || isRecording}
                        className="w-full max-w-lg py-5 rounded-[2rem] font-black text-lg transition-all shadow-xl disabled:opacity-30"
                        style={{
                            background: input.trim() ? "linear-gradient(135deg, var(--gold), #fbbf24)" : "rgba(255,255,255,0.05)",
                            color: input.trim() ? "#20124d" : "rgba(255,255,255,0.2)",
                            transform: loading ? "scale(0.98)" : "scale(1)"
                        }}>
                        {loading ? "Анализирую..." : "Сохранить рефлексию +20✦"}
                    </button>

                    <p className="mt-6 text-center text-[10px] text-white/20 leading-relaxed uppercase tracking-[0.2em] max-w-[200px]">
                        Ваша рефлексия поможет ИИ лучше понимать вашу динамику
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
                        <div className="glass p-8 text-center mx-4">
                            <p className="text-3xl mb-2 opacity-20">📜</p>
                            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                                Здесь будут ваши прошлые рефлексии
                            </p>
                        </div>
                    ) : (
                        history?.map((entry: any) => (
                            <motion.div key={entry.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                className="glass-strong p-5 rounded-[2rem] border border-white/5 relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-violet-600/5 blur-[40px] -z-1" />

                                <div className="flex justify-between items-start mb-3">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-[10px] text-white/30 font-bold uppercase tracking-widest text-xs">
                                            {new Date(entry.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
                                        </span>
                                        {entry.hawkins_score && (
                                            <div className="flex items-center gap-2">
                                                <span className="text-xl font-black text-violet-400">{entry.hawkins_score}</span>
                                                <span className="text-[9px] text-white/20 uppercase font-bold tracking-tighter">Хокинс</span>
                                            </div>
                                        )}
                                    </div>
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20 uppercase font-black tracking-tighter">
                                        {SPHERE_NAMES[entry.sphere] || entry.sphere || "Общее"}
                                    </span>
                                </div>

                                <p className="text-sm text-white/90 italic mb-4 leading-relaxed font-medium">
                                    «{entry.content}»
                                </p>

                                {entry.ai_analysis && (
                                    <div className="bg-violet-500/5 rounded-2xl p-4 border border-violet-500/10 backdrop-blur-sm">
                                        <p className="text-[10px] uppercase tracking-[0.2em] text-violet-300/40 mb-2 font-black">Разбор ИИ</p>
                                        <p className="text-[13px] text-white/70 leading-relaxed font-medium">
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

// Keep startRecording and stopRecording as they are used in ReflectPage
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
