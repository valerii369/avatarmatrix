"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { reflectAPI, voiceAPI, diaryAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

const SPHERE_NAMES: Record<string, string> = {
    IDENTITY: "Личность", MONEY: "Деньги", RELATIONS: "Отношения",
    FAMILY: "Род", MISSION: "Миссия", HEALTH: "Здоровье", SOCIETY: "Влияние", SPIRIT: "Духовность"
};

export default function ReflectPage() {
    const { userId, setUser, energy } = useUserStore();
    const router = useRouter();
    const [input, setInput] = useState("");
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [history, setHistory] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(true);

    // Voice recording state
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 250)}px`;
        }
    }, [input, isTranscribing]);

    // Fetch reflection history
    useEffect(() => {
        if (!userId) return;
        diaryAPI.getAll(userId, undefined, "reflection")
            .then(res => {
                setHistory(res.data);
                setLoadingHistory(false);
            })
            .catch(() => setLoadingHistory(false));
    }, [userId]);

    const handleSubmit = async () => {
        if (!userId || !input.trim()) return;
        setLoading(true);
        try {
            const res = await reflectAPI.submit(userId, input.trim());
            setResult(res.data);
            if (res.data.energy_awarded > 0) {
                setUser({ energy: (energy || 0) + res.data.energy_awarded });
            }
            // Refresh history
            const hRes = await diaryAPI.getAll(userId, undefined, "reflection");
            setHistory(hRes.data);
        } catch (e: any) {
            if (e.response?.data?.detail?.includes("уже пройдена")) {
                setResult({ message: "Рефлексия уже пройдена сегодня", energy_awarded: 0 });
            }
        } finally {
            setLoading(false);
        }
    };

    const startRecording = useCallback(async () => {
        if (isRecording || isTranscribing) return;
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
                    const res = await voiceAPI.transcribe(userId!, blob, "reflection");
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
        } catch {
            alert("Нет доступа к микрофону");
        }
    }, [userId, isRecording, isTranscribing]);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
    }, []);

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
                    className="w-full py-4 rounded-2xl font-bold shadow-lg shadow-violet-500/20"
                    style={{ background: "linear-gradient(135deg, var(--violet), #6366f1)", color: "#fff" }}>
                    Продолжить путь
                </button>
            </motion.div>
            <BottomNav active="reflect" />
        </div>
    );

    return (
        <div className="min-h-screen pb-24 px-4 flex flex-col" style={{ background: "var(--bg-deep)" }}>
            <div className="pt-8 pb-6 text-center">
                <h1 className="text-2xl font-black gradient-text mb-2 tracking-tight">Ежедневная рефлексия</h1>
                <p className="text-sm text-white/40">Осознайте свой путь сегодня · +20✦</p>
            </div>

            <div className="flex-1 flex flex-col items-center">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    className="glass-strong p-6 w-full max-w-lg rounded-[2rem] border border-white/10 mb-6">
                    <h2 className="text-lg font-bold text-white/90 mb-4">О чем вы думаете сейчас?</h2>

                    <div className="relative mb-4">
                        <textarea
                            ref={textareaRef}
                            value={isTranscribing ? "🎤 Обрабатываю голос..." : input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Расскажите о своем дне, чувствах или инсайтах. ИИ проанализирует глубину..."
                            className="w-full bg-transparent border-none outline-none text-white/90 text-base leading-relaxed resize-none min-h-[150px]"
                            readOnly={isTranscribing}
                        />

                        <AnimatePresence>
                            {isRecording && (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                    className="absolute inset-0 bg-violet-900/20 backdrop-blur-sm rounded-xl flex items-center justify-center pointer-events-none">
                                    <div className="flex gap-1.5">
                                        {[0, 1, 2, 3].map(i => (
                                            <motion.div key={i} className="w-1.5 h-6 bg-violet-400 rounded-full"
                                                animate={{ scaleY: [1, 2, 1] }}
                                                transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.1 }} />
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-white/5">
                        <button
                            onPointerDown={startRecording}
                            onPointerUp={stopRecording}
                            onPointerLeave={stopRecording}
                            className={`p-4 rounded-full transition-all ${isRecording ? "bg-red-500 scale-110 shadow-lg shadow-red-500/20" : "bg-white/5 hover:bg-white/10"}`}
                        >
                            <span className="text-xl">{isRecording ? "🔴" : "🎤"}</span>
                        </button>

                        <p className="text-[10px] text-white/30 uppercase tracking-widest font-medium">
                            {isRecording ? "Слушаю..." : "Зажмите для записи"}
                        </p>
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
                    {loading ? "Анализирую..." : "Сохранить рефлексию"}
                </button>

                <p className="mt-6 text-center text-[10px] text-white/20 leading-relaxed uppercase tracking-[0.2em] max-w-[200px]">
                    Ваша рефлексия поможет ИИ лучше понимать вашу динамику
                </p>

                {/* Reflection History Section */}
                <div className="w-full max-w-lg mt-12 pb-12">
                    <div className="flex items-center justify-between mb-6 px-2">
                        <h3 className="text-sm font-bold uppercase tracking-widest text-white/40">История состояний</h3>
                        <div className="h-px flex-1 bg-white/5 mx-4" />
                    </div>

                    {loadingHistory ? (
                        <div className="flex justify-center py-8">
                            <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                    ) : history.length === 0 ? (
                        <div className="text-center py-12 glass rounded-[2rem] border border-dashed border-white/5">
                            <p className="text-sm text-white/20 italic">Здесь будут ваши прошлые рефлексии</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {history.map(entry => (
                                <motion.div key={entry.id} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
                                    className="glass-strong p-5 rounded-[1.5rem] border border-white/5 relative overflow-hidden">
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-violet-600/5 blur-[40px] -z-1" />

                                    <div className="flex justify-between items-start mb-3">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-[10px] text-white/30 font-bold uppercase tracking-widest">
                                                {new Date(entry.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
                                            </span>
                                            {entry.hawkins_score && (
                                                <div className="flex items-center gap-2">
                                                    <span className="text-lg font-black text-violet-400">{entry.hawkins_score}</span>
                                                    <span className="text-[9px] text-white/20 uppercase font-bold tracking-tighter">Хокинс</span>
                                                </div>
                                            )}
                                        </div>
                                        <span className="text-[9px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20 uppercase font-bold">
                                            {SPHERE_NAMES[entry.sphere] || entry.sphere || "Общее"}
                                        </span>
                                    </div>

                                    <p className="text-xs text-white/60 italic mb-4 line-clamp-2 leading-relaxed">
                                        «{entry.content}»
                                    </p>

                                    {entry.ai_analysis && (
                                        <div className="bg-white/5 rounded-xl p-3 border-l-2 border-violet-500/50">
                                            <p className="text-[10px] text-white/70 leading-relaxed font-medium">
                                                {entry.ai_analysis}
                                            </p>
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <BottomNav active="reflect" />
        </div>
    );
}
