"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cardsAPI, createSessionWS, voiceAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";

const STAGE_NAMES = [
    "", "Контакт", "Осознание", "Переживание",
    "Перезапись", "Закрепление", "Мост в реальность"
];

interface Message {
    role: "user" | "ai" | "system";
    content: string;
    stage?: number;
    hawkins?: number;
}

export default function SessionPage() {
    const router = useRouter();
    const params = useParams();
    const { userId } = useUserStore();
    const wsRef = useRef<WebSocket | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const [card, setCard] = useState<any>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [stage, setStage] = useState(1);
    const [hawkins, setHawkins] = useState(0);
    const [hawkinsMin, setHawkinsMin] = useState(1000);
    const [hawkinsPeak, setHawkinsPeak] = useState(0);
    const [isComplete, setIsComplete] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [isAiTyping, setIsAiTyping] = useState(true);
    const [error, setError] = useState("");
    const [expertResults, setExpertResults] = useState<any>(null);
    const [isDeepening, setIsDeepening] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Voice recording state
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    useEffect(() => {
        if (!userId || !params.id) return;
        const cardId = Number(params.id);

        cardsAPI.getOne(userId, cardId).then(r => setCard(r.data));

        const ws = createSessionWS(userId, cardId);
        wsRef.current = ws;

        ws.onopen = () => setIsConnected(true);

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === "error") {
                    setError(data.content);
                    ws.close();
                    return;
                }

                setIsAiTyping(false);
                setMessages(prev => [...prev, {
                    role: "ai",
                    content: data.content,
                    stage: data.stage,
                    hawkins: data.hawkins_current,
                }]);

                if (data.stage) setStage(data.stage);
                if (data.hawkins_current) setHawkins(data.hawkins_current);
                if (data.hawkins_min) setHawkinsMin(data.hawkins_min);
                if (data.hawkins_peak) setHawkinsPeak(data.hawkins_peak);
                if (data.expert_results) setExpertResults(data.expert_results);
                if (data.is_complete) setIsComplete(true);
                setIsDeepening(data.is_deepening || false);
            } catch (e) {
                console.error("WS parse error", e);
            }
        };

        ws.onerror = () => setError("Соединение потеряно");
        ws.onclose = () => setIsConnected(false);

        return () => ws.close();
    }, [userId, params.id]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Auto-resize textarea when content changes
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
        }
    }, [input, isTranscribing]);

    const sendMessage = () => {
        if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        const content = input.trim();
        setMessages(prev => [...prev, { role: "user", content, stage }]);
        setInput("");
        setIsAiTyping(true);

        wsRef.current.send(JSON.stringify({ type: "message", content, stage }));

        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
    };

    const completeStage = () => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        setIsAiTyping(true);
        wsRef.current.send(JSON.stringify({ type: "complete_stage", content: "", stage }));

        if (stage < 6) {
            setMessages(prev => [...prev, {
                role: "system",
                content: `→ Этап ${stage + 1}/6: ${STAGE_NAMES[stage + 1]}`,
            }]);
            setStage(s => s + 1);
        }
    };

    const closeSession = () => {
        wsRef.current?.send(JSON.stringify({ type: "close" }));
        wsRef.current?.close();
        router.push(`/card/${params.id}`);
    };

    // Voice recording handlers
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
            recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            recorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                if (chunksRef.current.length === 0) return;
                const blob = new Blob(chunksRef.current, { type: mimeType });
                setIsTranscribing(true);
                try {
                    const res = await voiceAPI.transcribe(userId!, blob, "session");
                    const transcript = res.data.transcript?.trim();
                    if (transcript) {
                        setInput(prev => prev ? prev + " " + transcript : transcript);
                    }
                } catch (err: any) {
                    console.error("Transcription error:", err);
                    alert("Ошибка транскрибации. Попробуйте еще раз.");
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

    const toggleRecording = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    const progress = (stage / 6) * 100;
    const lastMessage = messages[messages.length - 1];
    const canSendMessage = input.trim() && !isAiTyping && !isTranscribing;

    if (error) return (
        <div className="flex flex-col items-center justify-center min-h-screen px-6 gap-4" style={{ background: "var(--bg-deep)" }}>
            <div className="text-4xl">⚠️</div>
            <p className="text-center text-sm" style={{ color: "#fc8181" }}>{error}</p>
            <button onClick={() => router.back()} className="px-6 py-3 rounded-xl text-sm"
                style={{ background: "var(--violet)", color: "#fff", fontSize: "16px" }}>
                Назад
            </button>
        </div>
    );

    if (!isConnected) return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-4" style={{ background: "var(--bg-deep)" }}>
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full" />
            <p style={{ color: "var(--text-muted)" }}>Подключение к агенту...</p>
        </div>
    );

    return (
        <div className="flex flex-col min-h-screen max-h-screen" style={{ background: "var(--bg-deep)" }}>
            {/* Header */}
            <div className="px-4 pt-4 pb-3 flex-none"
                style={{ background: "linear-gradient(180deg, var(--bg-deep) 80%, transparent)" }}>
                <div className="flex items-center justify-between mb-3">
                    <div className="flex-1">
                        {card && (
                            <>
                                <p className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>{card.archetype_name}</p>
                                <p className="text-xs" style={{ color: card.sphere_color || "var(--violet-l)" }}>{card.sphere_name_ru}</p>
                            </>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        {hawkins > 0 && (
                            <span className="text-xs font-semibold" style={{ color: "var(--gold)" }}>
                                {hawkins} ↑
                            </span>
                        )}
                        <button onClick={closeSession} className="text-xs px-3 py-1.5 rounded-lg"
                            style={{ background: "rgba(255,255,255,0.06)", color: "var(--text-muted)", fontSize: "14px" }}>
                            Завершить
                        </button>
                    </div>
                </div>

                {!isComplete && (
                    <>
                        <div className="phase-bar mb-1">
                            <div className="phase-bar-fill" style={{ width: `${progress}%` }} />
                        </div>
                        <div className="flex justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                            <span className="flex items-center gap-2">
                                Этап {stage}/6: {STAGE_NAMES[stage]}
                                {isDeepening && (
                                    <motion.span
                                        initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }}
                                        className="text-[9px] px-1.5 py-0.5 bg-violet-500/20 text-violet-300 rounded-md border border-violet-500/30 animate-pulse uppercase tracking-tighter font-black"
                                    >
                                        углубление
                                    </motion.span>
                                )}
                            </span>
                            {hawkins > 0 && <span>Хокинс: {hawkins}</span>}
                        </div>
                    </>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
                {messages.map((msg, i) => (
                    <AnimatePresence key={i}>
                        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                            className={msg.role === "system" ? "text-center" : ""}>
                            {msg.role === "system" ? (
                                <p className="text-xs py-1" style={{ color: "var(--violet-l)" }}>{msg.content}</p>
                            ) : msg.role === "user" ? (
                                <div className="bubble-user">
                                    <p className="text-sm" style={{ color: "var(--text-primary)" }}>{msg.content}</p>
                                </div>
                            ) : (
                                <div className="bubble-ai">
                                    <p className="text-sm leading-relaxed" style={{ color: "var(--text-primary)", whiteSpace: "pre-line" }}>
                                        {msg.content}
                                    </p>
                                    {msg.hawkins && msg.hawkins > 0 && (
                                        <div className="mt-2 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                                            <div className="hawkins-bar rounded-full h-1">
                                                <div style={{ width: `${(msg.hawkins / 1000) * 100}%`, height: "100%" }} />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                ))}

                {isAiTyping && (
                    <div className="bubble-ai">
                        <div className="flex gap-1">
                            {[0, 1, 2].map(i => (
                                <motion.div key={i} className="w-2 h-2 rounded-full" style={{ background: "var(--violet-l)" }}
                                    animate={{ opacity: [0.3, 1, 0.3] }}
                                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }} />
                            ))}
                        </div>
                    </div>
                )}

                {isComplete && (
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                        className="glass-strong p-6 text-center mt-4 rounded-3xl border border-white/10">
                        <div className="text-4xl mb-4">✨</div>
                        <h2 className="text-2xl font-bold gradient-text mb-2">Выравнивание завершено</h2>

                        <div className="mb-6 space-y-4">
                            <div className="bg-white/5 rounded-2xl p-4">
                                <p className="text-[10px] uppercase tracking-widest text-white/40 mb-1">Финальный уровень</p>
                                <div className="text-4xl font-black mb-1" style={{ color: "var(--gold)" }}>
                                    {hawkins}
                                </div>
                                <p className="text-sm font-bold uppercase tracking-wide text-white/80">
                                    {expertResults?.hawkins_level || "..."}
                                </p>
                            </div>

                            {expertResults && (
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="bg-white/5 rounded-xl p-3 text-left">
                                        <p className="text-[9px] uppercase tracking-widest text-white/40 mb-1">Глубина</p>
                                        <p className="text-lg font-bold text-white/90">{expertResults.transformation_depth}/10</p>
                                    </div>
                                    <div className="bg-white/5 rounded-xl p-3 text-left">
                                        <p className="text-[9px] uppercase tracking-widest text-white/40 mb-1">Тень</p>
                                        <p className="text-sm font-bold text-white/90">
                                            {expertResults.is_shadow_integrated ? "Интегрирована" : "В процессе"}
                                        </p>
                                    </div>
                                </div>
                            )}

                            {expertResults?.final_state_summary && (
                                <div className="bg-white/5 rounded-xl p-4 text-left border-l-4 border-violet-500">
                                    <p className="text-[9px] uppercase tracking-widest text-white/40 mb-2">Итог трансформации</p>
                                    <p className="text-sm italic leading-relaxed text-white/70">
                                        «{expertResults.final_state_summary}»
                                    </p>
                                </div>
                            )}
                        </div>

                        <button onClick={() => router.push(`/diary`)}
                            className="w-full py-4 rounded-2xl font-bold shadow-lg shadow-violet-500/20"
                            style={{ background: "linear-gradient(135deg, var(--violet), #6366f1)", color: "#fff", fontSize: "16px" }}>
                            Открыть записи в дневнике
                        </button>
                    </motion.div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            {!isComplete && (
                <div className="flex-none px-4 pb-10 pt-2"
                    style={{ background: "linear-gradient(0deg, var(--bg-deep) 80%, transparent)" }}>

                    <div className="flex flex-col gap-3">
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
                                value={isTranscribing ? "🎤 Обрабатываю голос..." : input}
                                onChange={(e) => {
                                    setInput(e.target.value);
                                }}
                                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                                placeholder="Ваш ответ..."
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
                                disabled={isTranscribing || isAiTyping}
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
                                style={{ fontSize: 11, color: "#EC4899", marginTop: -6, paddingLeft: 4 }}
                            >
                                ● Запись... нажмите ⏹ чтобы остановить
                            </motion.p>
                        )}

                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            onClick={sendMessage}
                            disabled={isAiTyping || isTranscribing || !input.trim()}
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
                                background: (isAiTyping || !input.trim())
                                    ? "rgba(255,255,255,0.06)"
                                    : "linear-gradient(135deg, var(--violet), #6366f1)",
                                color: (isAiTyping || !input.trim())
                                    ? "var(--text-muted)"
                                    : "#fff",
                                boxShadow: (isAiTyping || !input.trim())
                                    ? "none"
                                    : "0 8px 24px rgba(139,92,246,0.3)",
                            }}
                        >
                            {isAiTyping ? "···" : "Далее →"}
                        </motion.button>
                    </div>
                </div>
            )}
        </div>
    );
}
