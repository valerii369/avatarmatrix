"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { syncAPI, cardsAPI, voiceAPI } from "@/lib/api";
import { useUserStore, useCardsStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

export default function SyncPage() {
    const router = useRouter();
    const params = useParams();
    const { userId } = useUserStore();

    const [sessionId, setSessionId] = useState<number | null>(null);
    const [currentPhase, setCurrentPhase] = useState(0);
    const [phaseContent, setPhaseContent] = useState("");
    const [userInput, setUserInput] = useState("");
    const [isComplete, setIsComplete] = useState(false);
    const [loading, setLoading] = useState(false);
    const [starting, setStarting] = useState(false);
    const [hasStarted, setHasStarted] = useState(false);
    const [card, setCard] = useState<any>(null);
    const [insights, setInsights] = useState<any>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Voice state
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    useEffect(() => {
        if (!userId || !params.id) return;
        const cardId = Number(params.id);
        cardsAPI.getOne(userId, cardId).then(r => setCard(r.data));
    }, [userId, params.id]);

    const handleStartSync = async () => {
        if (!userId || !params.id) return;
        setStarting(true);
        setHasStarted(true);
        const cardId = Number(params.id);
        try {
            const r = await syncAPI.start(userId, cardId);
            setSessionId(r.data.session_id);
            setCurrentPhase(r.data.current_phase);
            setPhaseContent(r.data.phase_content);
        } catch (e: any) {
            alert(e.response?.data?.detail || "Ошибка запуска");
            setHasStarted(false);
        } finally {
            setStarting(false);
        }
    };

    // Auto-resize textarea when content changes (e.g. voice transcription)
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [userInput, isTranscribing]);

    const handleNext = async () => {
        if (!sessionId || !userId) return;
        setLoading(true);
        try {
            const res = await syncAPI.phase(userId, sessionId, currentPhase, userInput || undefined);
            setCurrentPhase(res.data.current_phase);
            setPhaseContent(res.data.phase_content);
            if (res.data.is_complete) {
                setIsComplete(true);
                // Also update the local store immediately for consistency
                useCardsStore.getState().updateCard(Number(params.id), { status: "synced" });
            }
            if (res.data.insights) setInsights(res.data.insights);
            setUserInput("");
            if (textareaRef.current) {
                textareaRef.current.style.height = "auto";
            }
        } catch (e: any) {
            alert(e.response?.data?.detail || "Ошибка");
        } finally {
            setLoading(false);
        }
    };

    // ── Voice recording ────────────────────────────────────────────────────────
    const startRecording = useCallback(async () => {
        if (isRecording || isTranscribing) return;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus"
                : MediaRecorder.isTypeSupported("audio/webm")
                    ? "audio/webm"
                    : "audio/mp4";
            const recorder = new MediaRecorder(stream, { mimeType });
            chunksRef.current = [];
            recorder.ondataavailable = e => {
                if (e.data.size > 0) chunksRef.current.push(e.data);
            };
            recorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                if (chunksRef.current.length === 0) return;
                const blob = new Blob(chunksRef.current, { type: mimeType });
                setIsTranscribing(true);
                try {
                    const res = await voiceAPI.transcribe(userId!, blob, "sync");
                    const transcript = res.data.transcript?.trim();
                    if (transcript) {
                        setUserInput(prev => prev ? prev + " " + transcript : transcript);
                    }
                } catch (err) {
                    console.error("Transcription error:", err);
                    alert("Ошибка транскрибации. Попробуйте ещё раз.");
                } finally {
                    setIsTranscribing(false);
                }
            };
            recorder.start(100); // collect data every 100ms
            mediaRecorderRef.current = recorder;
            setIsRecording(true);
        } catch {
            alert("Нет доступа к микрофону");
        }
    }, [isRecording, isTranscribing, userId]);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
    }, []);

    const toggleRecording = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    const progress = Math.round((currentPhase / 5) * 100);
    const isFirstPhase = currentPhase === 0;
    const needsInput = hasStarted && !isComplete && currentPhase < 5;

    if (starting) return (
        <div className="flex items-center justify-center min-h-screen flex-col gap-4" style={{ background: "var(--bg-deep)" }}>
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full" />
            <p style={{ color: "var(--text-muted)", fontSize: 14 }}>Открываем врата...</p>
        </div>
    );

    // Color gradient for Hawkins score: 0-200 (Red-Yellow), 200-500 (Yellow-Green)
    const getHawkinsColor = (score: number) => {
        if (score <= 200) {
            // Lerp 0-200: Red (#EF4444) to Yellow (#F59E0B)
            const ratio = score / 200;
            const r = Math.round(239 + (245 - 239) * ratio);
            const g = Math.round(68 + (158 - 68) * ratio);
            const b = Math.round(68 + (11 - 68) * ratio);
            return `rgb(${r}, ${g}, ${b})`;
        } else {
            // Lerp 200-500+: Yellow (#F59E0B) to Green (#10B981)
            const ratio = Math.min(1, (score - 200) / 300);
            const r = Math.round(245 + (16 - 245) * ratio);
            const g = Math.round(158 + (185 - 158) * ratio);
            const b = Math.round(11 + (129 - 11) * ratio);
            return `rgb(${r}, ${g}, ${b})`;
        }
    };

    return (
        <div className="min-h-screen flex flex-col pb-32" style={{ background: "var(--bg-deep)" }}>

            {/* ── Header ── */}
            <div className="px-4 pt-5 pb-3" style={{ flexShrink: 0 }}>
                <button onClick={() => router.back()} style={{
                    fontSize: 13, color: "var(--text-muted)",
                    background: "none", border: "none", cursor: "pointer", padding: 0, marginBottom: 14, display: "block",
                }}>
                    ‹ Выйти
                </button>

                {card && (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                        <div>
                            <p style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, margin: 0 }}>
                                {card.archetype_name}
                            </p>
                            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>{card.sphere_name_ru}</p>
                        </div>
                        {!isComplete && (
                            <span style={{
                                fontSize: 11, padding: "4px 12px", borderRadius: 20,
                                background: "rgba(139,92,246,0.15)", color: "var(--violet-l)", fontWeight: 600,
                            }}>
                                {currentPhase}/5
                            </span>
                        )}
                    </div>
                )}

                {/* Progress bar */}
                {!isComplete && (
                    <div style={{ height: 3, background: "rgba(255,255,255,0.07)", borderRadius: 2, overflow: "hidden" }}>
                        <motion.div
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.5 }}
                            style={{ height: "100%", background: "linear-gradient(90deg, var(--violet), #6366f1)", borderRadius: 2 }}
                        />
                    </div>
                )}
            </div>

            {/* ── Content ── */}
            <div style={{ flex: 1, padding: "0 16px", overflowY: "auto", paddingBottom: 12 }}>
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentPhase}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={{ duration: 0.35 }}
                        style={{
                            background: "rgba(255,255,255,0.04)",
                            border: "1px solid var(--border)",
                            borderRadius: 20,
                            padding: "20px 18px",
                            marginBottom: 16,
                            marginTop: 4,
                        }}
                    >
                        {isComplete ? (
                            <div style={{ textAlign: "center" }}>
                                <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
                                <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12, color: "var(--text-primary)" }}
                                    className="gradient-text">
                                    Синхронизация завершена
                                </h2>

                                {insights?.hawkins_score && (
                                    <div style={{ marginBottom: 20 }}>
                                        <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4, fontWeight: 600 }}>УРОВЕНЬ ЭНЕРГИИ (ПО ХОКИНСУ)</p>
                                        <div style={{
                                            fontSize: 48,
                                            fontWeight: 800,
                                            color: getHawkinsColor(insights.hawkins_score),
                                            lineHeight: 1,
                                            fontFamily: "'Outfit', sans-serif"
                                        }}>
                                            {insights.hawkins_score}
                                        </div>
                                        <p style={{ fontSize: 16, fontWeight: 600, color: getHawkinsColor(insights.hawkins_score), marginTop: 4 }}>
                                            {insights.hawkins_level}
                                        </p>
                                    </div>
                                )}

                                <p style={{ fontSize: 14, color: "var(--text-secondary)", whiteSpace: "pre-line", lineHeight: 1.7 }}>
                                    {phaseContent}
                                </p>
                            </div>
                        ) : !hasStarted ? (
                            <div style={{ textAlign: "center", padding: "20px 0" }}>
                                <div style={{ fontSize: 40, marginBottom: 16 }}>👁</div>
                                <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 14, color: "var(--text-primary)" }}>
                                    Синхронизация
                                </h2>
                                <p style={{ fontSize: 16, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 24 }}>
                                    Глубокая диагностика текущего состояния через 5 уровней подсознания.
                                    Оставьте логику — доверяйте первым образам и ощущениям.
                                </p>
                                <p style={{ fontSize: 18, fontWeight: 600, color: "var(--violet-l)", marginBottom: 20 }}>
                                    Готовы войти?
                                </p>
                            </div>
                        ) : currentPhase === 0 ? (
                            <div style={{ textAlign: "center", padding: "10px 0" }}>
                                <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12, color: "var(--text-primary)" }}>
                                    Врата Синхронизации
                                </h2>
                                <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--text-secondary)", whiteSpace: "pre-line" }}>
                                    {phaseContent}
                                </p>
                            </div>
                        ) : (
                            <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--text-primary)", whiteSpace: "pre-line", margin: 0 }}>
                                {phaseContent}
                            </p>
                        )}
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* ── Input + Actions (fixed bottom area) ── */}
            <div style={{
                position: "fixed", bottom: 0, left: 0, right: 0,
                padding: "20px 16px 24px",
                background: "linear-gradient(to top, var(--bg-deep) 75%, transparent)",
            }}>
                {!isComplete && (
                    <>
                        {/* Textarea row — only shown when user needs to type */}
                        {needsInput && (
                            <div style={{ marginBottom: 10 }}>
                                <div style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 10,
                                    background: "rgba(255,255,255,0.05)",
                                    border: isRecording
                                        ? "1px solid rgba(236,72,153,0.5)"
                                        : "1px solid var(--border)",
                                    borderRadius: 18,
                                    padding: "12px 12px 12px 16px",
                                    transition: "border-color 0.2s",
                                }}>
                                    <textarea
                                        ref={textareaRef}
                                        value={isTranscribing ? "🎤 Обрабатываю голос..." : userInput}
                                        onChange={(e) => {
                                            if (isTranscribing) return;
                                            setUserInput(e.target.value);
                                        }}
                                        placeholder="Напишите ваш ответ..."
                                        rows={1}
                                        readOnly={isTranscribing}
                                        style={{
                                            flex: 1,
                                            background: "transparent",
                                            border: "none",
                                            outline: "none",
                                            resize: "none",
                                            fontSize: 16,
                                            color: "var(--text-primary)",
                                            lineHeight: 1.5,
                                            maxHeight: 200,
                                            fontFamily: "'Inter', sans-serif",
                                            padding: 0,
                                        }}
                                    />
                                    {/* Mic button */}
                                    <button
                                        onClick={toggleRecording}
                                        disabled={isTranscribing}
                                        style={{
                                            flexShrink: 0,
                                            width: 38,
                                            height: 38,
                                            borderRadius: 12,
                                            border: "none",
                                            cursor: isTranscribing ? "default" : "pointer",
                                            background: isRecording
                                                ? "rgba(236,72,153,0.25)"
                                                : "rgba(255,255,255,0.07)",
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "center",
                                            fontSize: 18,
                                            transition: "all 0.2s",
                                            color: isRecording ? "#EC4899" : "var(--text-muted)",
                                        }}
                                    >
                                        {isTranscribing ? (
                                            <motion.span
                                                animate={{ opacity: [1, 0.3, 1] }}
                                                transition={{ duration: 1, repeat: Infinity }}
                                            >⏳</motion.span>
                                        ) : isRecording ? "⏹" : "🎤"}
                                    </button>
                                </div>
                                {isRecording && (
                                    <motion.p
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        style={{ fontSize: 11, color: "#EC4899", marginTop: 6, paddingLeft: 4 }}
                                    >
                                        ● Запись... нажмите ⏹ чтобы остановить
                                    </motion.p>
                                )}
                            </div>
                        )}

                        {/* Main action button */}
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            onClick={hasStarted ? handleNext : handleStartSync}
                            disabled={loading || starting || (needsInput && currentPhase > 0 && !userInput.trim() && !isTranscribing)}
                            style={{
                                width: "100%",
                                padding: "16px",
                                borderRadius: 18,
                                border: "none",
                                cursor: "pointer",
                                fontSize: 16,
                                fontWeight: 700,
                                fontFamily: "'Outfit', sans-serif",
                                letterSpacing: "0.03em",
                                transition: "all 0.2s",
                                background: (loading || starting || (needsInput && !userInput.trim()))
                                    ? "rgba(255,255,255,0.06)"
                                    : "linear-gradient(135deg, var(--violet), #6366f1)",
                                color: (loading || starting || (needsInput && !userInput.trim()))
                                    ? "var(--text-muted)"
                                    : "#fff",
                                boxShadow: (loading || starting || (needsInput && !userInput.trim()))
                                    ? "none"
                                    : "0 8px 24px rgba(139,92,246,0.3)",
                            }}
                        >
                            {loading || starting ? (
                                <motion.span animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 1, repeat: Infinity }}>
                                    ···
                                </motion.span>
                            ) : !hasStarted
                                ? "Войти →"
                                : (isFirstPhase || currentPhase > 0) ? "Далее →" : "Войти →"}
                        </motion.button>
                    </>
                )}

                {/* Completion buttons */}
                {isComplete && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            onClick={() => router.push(`/session/${params.id}`)}
                            style={{
                                width: "100%", padding: "16px", borderRadius: 18, border: "none",
                                cursor: "pointer", fontSize: 16, fontWeight: 700,
                                background: "linear-gradient(135deg, var(--gold), #f97316)", color: "#000",
                            }}
                        >
                            Сессия выравнивания · 40 ✦
                        </motion.button>
                        <button
                            onClick={() => router.push("/")}
                            style={{
                                width: "100%", padding: "12px", background: "none",
                                border: "none", cursor: "pointer", fontSize: 14,
                                color: "var(--text-muted)",
                            }}
                        >
                            На главную
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
