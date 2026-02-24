"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { syncAPI, cardsAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";

const PHASE_NAMES = [
    "", "Врата", "Первый выбор", "Зеркало", "Развилка",
    "Голос", "Тело", "Тень говорит", "Неожиданный поворот",
    "Кристаллизация", "Оценка Хокинса"
];

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
    const [starting, setStarting] = useState(true);
    const [card, setCard] = useState<any>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (!userId || !params.id) return;
        const cardId = Number(params.id);

        // Load card info
        cardsAPI.getOne(userId, cardId).then(r => setCard(r.data));

        // Start sync session
        syncAPI.start(userId, cardId)
            .then(r => {
                setSessionId(r.data.session_id);
                setCurrentPhase(r.data.current_phase);
                setPhaseContent(r.data.phase_content);
                setStarting(false);
            })
            .catch(e => {
                alert(e.response?.data?.detail || "Ошибка запуска");
                router.back();
            });
    }, [userId, params.id, router]);

    const handleNext = async () => {
        if (!sessionId || !userId) return;
        setLoading(true);
        try {
            const res = await syncAPI.phase(userId, sessionId, currentPhase, userInput || undefined);
            setCurrentPhase(res.data.current_phase);
            setPhaseContent(res.data.phase_content);
            setIsComplete(res.data.is_complete);
            setUserInput("");
            if (textareaRef.current) textareaRef.current.style.height = "auto";
        } catch (e: any) {
            alert(e.response?.data?.detail || "Ошибка");
        } finally {
            setLoading(false);
        }
    };

    const progress = (currentPhase / 10) * 100;

    if (starting) return (
        <div className="flex items-center justify-center min-h-screen flex-col gap-4">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full" />
            <p style={{ color: "var(--text-muted)" }}>Открываем врата...</p>
        </div>
    );

    return (
        <div className="min-h-screen flex flex-col pb-6">
            {/* Header */}
            <div className="px-4 pt-4 pb-2">
                <button onClick={() => router.back()} className="text-sm mb-3 block" style={{ color: "var(--text-muted)" }}>
                    ← Выйти
                </button>
                {card && (
                    <div className="flex items-center justify-between mb-3">
                        <div>
                            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{card.archetype_name}</p>
                            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{card.sphere_name_ru}</p>
                        </div>
                        {!isComplete && (
                            <span className="text-xs px-3 py-1 rounded-full" style={{ background: "rgba(139,92,246,0.15)", color: "var(--violet-l)" }}>
                                Фаза {currentPhase}/10
                            </span>
                        )}
                    </div>
                )}
                {/* Phase progress */}
                {!isComplete && (
                    <div>
                        <div className="phase-bar mb-1">
                            <div className="phase-bar-fill" style={{ width: `${progress}%` }} />
                        </div>
                        <p className="text-xs" style={{ color: "var(--violet-l)" }}>
                            {PHASE_NAMES[currentPhase] || ""}
                        </p>
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="flex-1 px-4 overflow-y-auto">
                <AnimatePresence mode="wait">
                    <motion.div key={currentPhase} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }} className="glass p-5 mb-4 mt-2">
                        {isComplete ? (
                            <div className="text-center">
                                <div className="text-5xl mb-4">✅</div>
                                <h2 className="text-xl font-bold mb-3 gradient-text">Синхронизация завершена</h2>
                                <p className="text-sm" style={{ color: "var(--text-secondary)", whiteSpace: "pre-line" }}>
                                    {phaseContent}
                                </p>
                            </div>
                        ) : (
                            <p className="text-sm leading-relaxed" style={{ color: "var(--text-primary)", whiteSpace: "pre-line" }}>
                                {phaseContent}
                            </p>
                        )}
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Input */}
            {!isComplete && (
                <div className="px-4 pt-2">
                    {currentPhase > 1 && (
                        <textarea
                            ref={textareaRef}
                            value={userInput}
                            onChange={(e) => {
                                setUserInput(e.target.value);
                                e.target.style.height = "auto";
                                e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
                            }}
                            placeholder="Ваш ответ..."
                            rows={2}
                            className="w-full px-4 py-3 rounded-xl text-sm outline-none resize-none mb-3 transition-all"
                            style={{
                                background: "rgba(255,255,255,0.06)",
                                border: "1px solid var(--border)",
                                color: "var(--text-primary)",
                                maxHeight: "150px",
                            }}
                        />
                    )}
                    <motion.button whileTap={{ scale: 0.97 }} onClick={handleNext}
                        disabled={loading || (currentPhase > 1 && !userInput.trim())}
                        className="w-full py-4 rounded-2xl font-semibold text-base transition-all"
                        style={{
                            background: (!loading && (currentPhase === 1 || userInput.trim()))
                                ? "linear-gradient(135deg, var(--violet), #6366f1)"
                                : "rgba(255,255,255,0.06)",
                            color: (!loading && (currentPhase === 1 || userInput.trim())) ? "#fff" : "var(--text-muted)",
                            boxShadow: "0 8px 24px rgba(139,92,246,0.3)",
                        }}>
                        {loading ? "..." : currentPhase >= 10 ? "Завершить синхронизацию" : `Фаза ${currentPhase + 1} →`}
                    </motion.button>
                </div>
            )}

            {isComplete && (
                <div className="px-4 pt-2 space-y-3">
                    <motion.button whileTap={{ scale: 0.97 }}
                        onClick={() => router.push(`/session/${params.id}`)}
                        className="w-full py-4 rounded-2xl font-semibold text-base"
                        style={{ background: "linear-gradient(135deg, var(--gold), #f97316)", color: "#000" }}>
                        Сессия выравнивания · 40 ✦
                    </motion.button>
                    <button onClick={() => router.push("/")} className="w-full py-3 text-sm"
                        style={{ color: "var(--text-muted)" }}>
                        На главную
                    </button>
                </div>
            )}
        </div>
    );
}
