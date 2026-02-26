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
    const [isComplete, setIsComplete] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [isAiTyping, setIsAiTyping] = useState(false);
    const [error, setError] = useState("");
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
                if (data.is_complete) setIsComplete(true);
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
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream, {
                mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4",
            });
            chunksRef.current = [];
            recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            recorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
                setIsTranscribing(true);
                try {
                    const res = await voiceAPI.transcribe(userId!, blob, "session");
                    setInput(prev => prev ? prev + " " + res.data.transcript : res.data.transcript);
                } catch {
                    alert("Ошибка транскрибации");
                } finally {
                    setIsTranscribing(false);
                }
            };
            recorder.start();
            mediaRecorderRef.current = recorder;
            setIsRecording(true);
        } catch {
            alert("Нет доступа к микрофону");
        }
    }, [userId]);

    const stopRecording = useCallback(() => {
        mediaRecorderRef.current?.stop();
        setIsRecording(false);
    }, []);

    const progress = (stage / 6) * 100;
    const lastMessage = messages[messages.length - 1];
    const showStageButton = !isAiTyping && lastMessage?.role === "ai" && !isComplete;

    if (error) return (
        <div className="flex flex-col items-center justify-center min-h-screen px-6 gap-4">
            <div className="text-4xl">⚠️</div>
            <p className="text-center text-sm" style={{ color: "#fc8181" }}>{error}</p>
            <button onClick={() => router.back()} className="px-6 py-3 rounded-xl text-sm"
                style={{ background: "var(--violet)", color: "#fff", fontSize: "16px" }}>
                Назад
            </button>
        </div>
    );

    if (!isConnected) return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-4">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full" />
            <p style={{ color: "var(--text-muted)" }}>Подключение к агенту...</p>
        </div>
    );

    return (
        <div className="flex flex-col min-h-screen max-h-screen">
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
                            <span>Этап {stage}/6: {STAGE_NAMES[stage]}</span>
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
                        className="glass-strong p-6 text-center mt-4">
                        <div className="text-4xl mb-3">🌟</div>
                        <h2 className="text-lg font-bold gradient-text mb-2">Сессия завершена</h2>
                        <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
                            Пик Хокинса: {hawkins} · Все 6 этапов пройдены
                        </p>
                        <button onClick={() => router.push(`/diary`)}
                            className="w-full py-3 rounded-xl font-semibold"
                            style={{ background: "linear-gradient(135deg, var(--violet), var(--gold))", color: "#fff", fontSize: "16px" }}>
                            Записи в дневнике →
                        </button>
                    </motion.div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            {!isComplete && (
                <div className="flex-none px-4 pb-6 pt-2"
                    style={{ background: "linear-gradient(0deg, var(--bg-deep) 80%, transparent)" }}>
                    {/* Stage advance button */}
                    {showStageButton && (
                        <button onClick={completeStage} className="w-full text-xs py-2 mb-2 rounded-lg transition-all"
                            style={{ background: "rgba(139,92,246,0.12)", color: "var(--violet-l)", border: "1px solid rgba(139,92,246,0.2)", fontSize: "14px" }}>
                            {stage < 6
                                ? `→ Перейти к этапу ${stage + 1}: ${STAGE_NAMES[stage + 1]}`
                                : "✅ Завершить сессию"
                            }
                        </button>
                    )}

                    <div className="flex gap-2 items-end">
                        <textarea
                            ref={textareaRef}
                            value={isTranscribing ? "🎤 Обработка голоса..." : input}
                            onChange={(e) => {
                                setInput(e.target.value);
                            }}
                            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                            placeholder="Ваш ответ..."
                            rows={1}
                            readOnly={isTranscribing}
                            className="flex-1 px-4 py-3 rounded-xl outline-none resize-none"
                            style={{
                                background: "rgba(255,255,255,0.06)",
                                border: "1px solid var(--border)",
                                color: "var(--text-primary)",
                                maxHeight: "180px",
                                fontSize: "16px",   // Prevents mobile auto-zoom
                                lineHeight: "1.5",
                            }}
                        />
                        {/* Mic button */}
                        <button
                            onPointerDown={startRecording}
                            onPointerUp={stopRecording}
                            onPointerLeave={isRecording ? stopRecording : undefined}
                            disabled={isTranscribing || isAiTyping}
                            className="flex-none w-11 h-11 rounded-xl flex items-center justify-center text-xl transition-all select-none"
                            style={{
                                background: isRecording ? "rgba(236,72,153,0.3)" : "rgba(255,255,255,0.06)",
                                border: isRecording ? "1px solid rgba(236,72,153,0.6)" : "1px solid var(--border)",
                                color: isTranscribing ? "var(--text-muted)" : isRecording ? "#EC4899" : "var(--text-muted)",
                            }}
                        >
                            {isTranscribing ? "⏳" : isRecording ? "⏹" : "🎤"}
                        </button>
                        {/* Send button */}
                        <button onClick={sendMessage} disabled={!input.trim() || isAiTyping}
                            className="flex-none w-11 h-11 rounded-xl flex items-center justify-center text-lg transition-all"
                            style={{
                                background: input.trim() && !isAiTyping ? "var(--violet)" : "rgba(255,255,255,0.06)",
                                color: input.trim() && !isAiTyping ? "#fff" : "var(--text-muted)",
                            }}>
                            →
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
