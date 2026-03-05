import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { calcAPI, api, voiceAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";

const MicIcon = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
);

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
                    const res = await voiceAPI.transcribe(userId, blob, "onboarding");
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

// Constants for date/time selection
const YEARS = Array.from({ length: 101 }, (_, i) => String(2025 - i));
const MONTHS = [
    { value: "01", label: "Январь" }, { value: "02", label: "Февраль" }, { value: "03", label: "Март" },
    { value: "04", label: "Апрель" }, { value: "05", label: "Май" }, { value: "06", label: "Июнь" },
    { value: "07", label: "Июль" }, { value: "08", label: "Август" }, { value: "09", label: "Сентябрь" },
    { value: "10", label: "Октябрь" }, { value: "11", label: "Ноябрь" }, { value: "12", label: "Декабрь" },
];
const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1).padStart(2, '0'));
const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
const MINUTES = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));

const CustomSelect = ({ value, onChange, options, flex, label }: any) => (
    <div style={{ flex: flex || 1, position: "relative" }}>
        {label && <p className="text-[10px] text-white/20 uppercase tracking-widest mb-1.5 ml-1">{label}</p>}
        <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full text-base outline-none appearance-none transition-all"
            style={{
                padding: "14px 12px",
                background: "rgba(255,255,255,0.05)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                color: "var(--text-primary)",
                fontSize: 15,
                WebkitTapHighlightColor: "transparent",
                colorScheme: "dark",
                cursor: "pointer"
            }}
        >
            {options.map((opt: any) => (
                <option key={opt.value || opt} value={opt.value || opt}>
                    {opt.label || opt}
                </option>
            ))}
        </select>
        <div style={{
            position: "absolute", right: 10, bottom: 16,
            pointerEvents: "none", opacity: 0.3, fontSize: 8
        }}>▼</div>
    </div>
);

function AstroFlow({ onBack }: { onBack: () => void }) {
    const router = useRouter();
    const { userId, setUser } = useUserStore();
    const [step, setStep] = useState(0);
    const [form, setForm] = useState({
        birth_year: "1990", birth_month: "01", birth_day: "15",
        birth_hour: "12", birth_minute: "00", birth_place: ""
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const steps = [
        { id: "date", title: "Дата рождения", hint: "Точная дата — основа вашей карты", icon: "✦", iconColor: "var(--gold)", description: "Дата рождения формирует ядро вашей архетипической карты" },
        { id: "time", title: "Время рождения", hint: "Если не знаете — укажите 12:00", icon: "◉", iconColor: "var(--violet-l)", description: "Точное время раскрывает Асцендент и расположение домов" },
        { id: "place", title: "Место рождения", placeholder: "Москва, Россия", hint: "Введите город и страну", icon: "◈", iconColor: "var(--cyan)", description: "Географические координаты влияют на точность расчётов" },
    ];

    const currentStep = steps[step];
    const progress = ((step + 1) / steps.length) * 100;

    const handleNext = async () => {
        if (step < steps.length - 1) {
            setStep(s => s + 1);
            return;
        }
        setLoading(true);
        setError("");
        try {
            await calcAPI.calculate({
                birth_date: `${form.birth_year}-${form.birth_month}-${form.birth_day}`,
                birth_time: `${form.birth_hour}:${form.birth_minute}`,
                birth_place: form.birth_place,
                user_id: userId!,
            });
            setUser({ onboardingDone: true });
            router.push("/");
        } catch (e: any) {
            setError(e.response?.data?.detail || "Ошибка расчёта. Проверьте данные.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="w-full">
            <div className="mb-6">
                <div className="flex justify-between mb-1.5 text-white/20">
                    <span className="text-[10px] uppercase font-bold tracking-widest">Шаг {step + 1} из {steps.length}</span>
                    <span className="text-[10px] font-bold">{Math.round(progress)}%</span>
                </div>
                <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div className="h-full bg-gradient-to-r from-violet-500 to-amber-500 rounded-full" animate={{ width: `${progress}%` }} />
                </div>
            </div>

            <AnimatePresence mode="wait">
                <motion.div
                    key={step}
                    initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                    className="glass-strong p-6 rounded-[2rem] border border-white/10 mb-5 shadow-2xl"
                >
                    <div className="flex items-center gap-4 mb-5">
                        <div style={{
                            width: 40, height: 40, borderRadius: 12, background: "rgba(255,255,255,0.05)",
                            border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 18, color: currentStep.iconColor, flexShrink: 0
                        }}>{currentStep.icon}</div>
                        <div className="min-w-0">
                            <h2 className="text-sm font-bold text-white/90 truncate">{currentStep.title}</h2>
                            <p className="text-[10px] text-white/40 leading-tight mt-0.5">{currentStep.description}</p>
                        </div>
                    </div>
                    <div className="h-px bg-white/5 mb-6" />

                    <div className="space-y-4">
                        {currentStep.id === "date" ? (
                            <div className="flex gap-2">
                                <CustomSelect label="День" value={form.birth_day} onChange={(v: string) => setForm(f => ({ ...f, birth_day: v }))} options={DAYS} flex={0.6} />
                                <CustomSelect label="Месяц" value={form.birth_month} onChange={(v: string) => setForm(f => ({ ...f, birth_month: v }))} options={MONTHS} flex={1.2} />
                                <CustomSelect label="Год" value={form.birth_year} onChange={(v: string) => setForm(f => ({ ...f, birth_year: v }))} options={YEARS} />
                            </div>
                        ) : currentStep.id === "time" ? (
                            <div className="flex gap-2 items-end">
                                <CustomSelect label="Час" value={form.birth_hour} onChange={(v: string) => setForm(f => ({ ...f, birth_hour: v }))} options={HOURS} />
                                <div className="text-white/20 pb-4 font-bold">:</div>
                                <CustomSelect label="Мин" value={form.birth_minute} onChange={(v: string) => setForm(f => ({ ...f, birth_minute: v }))} options={MINUTES} />
                            </div>
                        ) : (
                            <div className="relative">
                                <input
                                    type="text" value={form.birth_place}
                                    onChange={(e) => setForm(f => ({ ...f, birth_place: e.target.value }))}
                                    placeholder={currentStep.placeholder} autoFocus
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 text-[16px] text-white placeholder:text-white/20 outline-none focus:border-violet-500/50 transition-all font-medium"
                                />
                                {form.birth_place && <div className="absolute right-4 top-1/2 -translate-y-1/2 text-emerald-400 text-xs">✓</div>}
                            </div>
                        )}
                    </div>
                    <p className="text-[10px] text-white/20 mt-5 flex items-center gap-2">
                        <span style={{ color: currentStep.iconColor }}>●</span>{currentStep.hint}
                    </p>
                </motion.div>
            </AnimatePresence>

            {error && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-rose-500/10 border border-rose-500/20 p-3 rounded-xl mb-4 text-center">
                    <p className="text-xs text-rose-400">{error}</p>
                </motion.div>
            )}

            <button
                onClick={handleNext}
                disabled={loading || (currentStep.id === "place" && !form.birth_place)}
                className="w-full py-4 rounded-2xl font-black text-sm transition-all shadow-xl disabled:opacity-20 relative overflow-hidden group"
                style={{
                    background: (currentStep.id === "place" && !form.birth_place) ? "rgba(255,255,255,0.05)" : "linear-gradient(135deg, var(--violet), #6366f1)",
                    color: "#fff"
                }}
            >
                <span className="relative z-10">{loading ? "Синхронизация..." : step < steps.length - 1 ? "Продолжить →" : "Построить Аватара ✨"}</span>
                {!(currentStep.id === "place" && !form.birth_place) && !loading && (
                    <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-500 skew-x-12" />
                )}
            </button>

            <button onClick={() => step > 0 ? setStep(s => s - 1) : onBack()} className="w-full mt-4 text-[10px] font-bold text-white/20 uppercase tracking-widest hover:text-white/40 transition-colors">
                ← Назад
            </button>
        </motion.div>
    );
}

function AIFlow({ onBack }: { onBack: () => void }) {
    const router = useRouter();
    const { userId, setUser } = useUserStore();
    const [messages, setMessages] = useState<{ role: string, content: string }[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [calcLoading, setCalcLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const { isRecording, isTranscribing, startRecording, stopRecording } = useVoiceRecorder(userId, setInput);

    // Initial message
    useEffect(() => {
        sendChat([{ role: "user", content: "Привет! Я готов к диагностике и узнать какие у меня активные архетипы." }]);
    }, []);

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages]);

    const sendChat = async (hist: { role: string, content: string }[]) => {
        setLoading(true);
        setMessages(hist);
        try {
            const res = await api.post("/api/onboarding/ai/chat", { user_id: userId, chat_history: hist });
            setMessages([...hist, { role: "assistant", content: res.data.text }]);
        } catch (e: any) {
            console.error(e);
            setMessages([...hist, { role: "assistant", content: "Ошибка связи с ядром. Попробуйте еще раз." }]);
        } finally {
            setLoading(false);
        }
    };

    const handleSend = () => {
        if (!input.trim() || loading || calcLoading) return;
        const newHistory = [...messages, { role: "user", content: input }];
        setInput("");
        sendChat(newHistory);
    };

    const handleCalculate = async () => {
        setCalcLoading(true);
        try {
            await api.post("/api/onboarding/ai/calculate", { user_id: userId, chat_history: messages });
            setUser({ onboardingDone: true });
            router.push("/");
        } catch (e) {
            console.error(e);
            alert("Ошибка расчета карт.");
            setCalcLoading(false);
        }
    };

    const isReadyForSync = messages.length >= 7; // User sent 3+ responses

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="w-full h-[75vh] flex flex-col">
            <p className="text-[9px] text-white/30 text-center mb-3 leading-tight px-4 italic">
                Все данные зашифрованы. Чем подробнее расскажете о своих жизненных ситуациях, тем точнее мы сможем подобрать для вас карты архетипов.
            </p>
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto mb-4 p-4 glass-strong rounded-2xl border border-white/5 space-y-4"
                style={{
                    scrollbarWidth: "none"
                }}
            >
                {messages.filter(m => !(m.role === 'user' && m.content.startsWith('Привет! Я готов'))).map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`p-3 rounded-2xl max-w-[85%] text-[13px] leading-relaxed ${msg.role === "user" ? "bg-amber-500/20 text-amber-50 rounded-tr-sm border border-amber-500/10" : "bg-white/5 text-white/90 rounded-tl-sm border border-white/10"}`}>
                            {msg.content}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="p-3 bg-white/5 text-white/50 rounded-2xl rounded-tl-sm text-[11px] animate-pulse">
                            Анализ ответа...
                        </div>
                    </div>
                )}
            </div>

            <div className="relative mb-3 flex gap-2 items-center">
                <div className="relative flex-1">
                    <input
                        type="text"
                        value={isTranscribing ? "Слушаю..." : input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder="Ваш ответ..."
                        disabled={loading || calcLoading || isTranscribing}
                        className="w-full bg-white/5 border border-white/10 rounded-2xl pl-4 pr-12 py-4 text-[16px] text-white placeholder:text-white/20 outline-none focus:border-amber-500/50 transition-all font-medium"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || loading || calcLoading || isTranscribing}
                        className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center bg-amber-500/20 text-amber-300 rounded-xl disabled:opacity-30"
                    >
                        ↑
                    </button>
                    <AnimatePresence>
                        {isRecording && (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="absolute inset-0 bg-amber-500/10 backdrop-blur-md rounded-2xl flex items-center justify-center pointer-events-none border border-amber-500/20">
                                <div className="flex gap-1">
                                    {[0, 1, 2].map(i => (
                                        <motion.div key={i} className="w-1 h-4 bg-amber-400/60 rounded-full"
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
                    className={`flex-none w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${isRecording ? "bg-rose-500 scale-95 shadow-lg shadow-rose-500/20" : "bg-white/5 border border-white/10"}`}
                >
                    {isRecording ? "🔴" : <MicIcon className="w-6 h-6 text-amber-500/60" />}
                </button>
            </div>

            {isReadyForSync ? (
                <button
                    onClick={handleCalculate}
                    disabled={calcLoading}
                    className="w-full py-4 rounded-2xl font-black text-sm transition-all shadow-xl disabled:opacity-20 relative overflow-hidden group bg-gradient-to-r from-amber-500 to-orange-500 text-white"
                >
                    {calcLoading ? "Генерация..." : "Получить карты ✧"}
                </button>
            ) : (
                <p className="text-[10px] text-center text-white/30 uppercase tracking-wider mb-2">Ответьте еще на несколько вопросов</p>
            )}

            <button onClick={onBack} disabled={calcLoading} className="w-full mt-2 text-[10px] font-bold text-white/20 uppercase tracking-widest hover:text-white/40 transition-colors pb-4">
                ← Назад
            </button>
        </motion.div>
    );
}

export default function OnboardingPage() {
    const [path, setPath] = useState<"astro" | "ai" | null>(null);

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
        <div className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden bg-[#060818]">
            <div className="absolute inset-0 pointer-events-none">
                <div style={{
                    position: "absolute", top: "10%", left: "15%", width: 280, height: 280,
                    background: "radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)",
                    borderRadius: "50%", filter: "blur(32px)"
                }} />
                <div style={{
                    position: "absolute", bottom: "15%", right: "10%", width: 220, height: 220,
                    background: "radial-gradient(circle, rgba(245,158,11,0.10) 0%, transparent 70%)",
                    borderRadius: "50%", filter: "blur(28px)"
                }} />
            </div>

            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {particles.map((p, i) => (
                    <motion.div key={i}
                        className="absolute rounded-full bg-white"
                        style={{ left: p.left, top: p.top, width: p.size, height: p.size, opacity: p.opacity }}
                        animate={{ opacity: [p.opacity, p.opacity * 3, p.opacity] }}
                        transition={{ duration: p.duration, repeat: Infinity, delay: p.delay }}
                    />
                ))}
            </div>

            <div className="relative z-10 w-full max-w-[360px]">
                {/* Logo & Header */}
                {path !== "ai" && (
                    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-8">
                        <div style={{
                            width: 56, height: 56, margin: "0 auto 12px",
                            background: "linear-gradient(135deg, rgba(139,92,246,0.25), rgba(245,158,11,0.15))",
                            border: "1px solid var(--border-glow)",
                            borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 24, boxShadow: "0 8px 32px rgba(139,92,246,0.25)",
                        }}>
                            ✦
                        </div>
                        <h1 className="text-3xl font-bold gradient-text mb-1 tracking-tight">AVATAR</h1>
                        <p className="text-[10px] text-white/30 uppercase tracking-[0.2em]">Платформа эволюции</p>
                    </motion.div>
                )}

                {path === null && (
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col gap-4">
                        <button
                            onClick={() => setPath('astro')}
                            className="bg-white/5 border border-white/10 hover:bg-white/10 p-5 rounded-[2rem] text-left transition-all group shadow-xl"
                        >
                            <h3 className="text-violet-400 font-bold mb-1 flex items-center justify-between">
                                <span>✦ Доверяю астрологии</span>
                                <span className="opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                            </h3>
                            <p className="text-xs text-white/40 leading-relaxed">
                                Расчет архетипов на основе вашей натальной карты. Точный астрологический слепок личности.
                            </p>
                        </button>

                        <button
                            onClick={() => setPath('ai')}
                            className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/20 hover:border-amber-500/40 p-5 rounded-[2rem] text-left transition-all group shadow-xl"
                        >
                            <h3 className="text-amber-400 font-bold mb-1 flex items-center justify-between">
                                <span>☼ Доверяю себе</span>
                                <span className="opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                            </h3>
                            <p className="text-xs text-white/40 leading-relaxed">
                                Диагностика через живой диалог с ИИ. Выявление активных сфер и архетипов в моменте.
                            </p>
                        </button>
                    </motion.div>
                )}

                {path === 'astro' && <AstroFlow onBack={() => setPath(null)} />}
                {path === 'ai' && <AIFlow onBack={() => setPath(null)} />}
            </div>
        </div>
    );
}
