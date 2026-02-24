"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { reflectAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { BottomNav } from "@/app/page";

const SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"];
const SPHERE_NAMES: Record<string, string> = {
    IDENTITY: "Личность", MONEY: "Деньги", RELATIONS: "Отношения",
    FAMILY: "Род", MISSION: "Миссия", HEALTH: "Здоровье", SOCIETY: "Влияние", SPIRIT: "Духовность"
};
const EMOTIONS = ["радость", "спокойствие", "тревога", "страх", "гнев", "печаль", "вина", "стыд", "апатия", "вдохновение", "любовь"];

export default function ReflectPage() {
    const { userId, setUser } = useUserStore();
    const router = useRouter();
    const [step, setStep] = useState(0);
    const [emotion, setEmotion] = useState("");
    const [integration, setIntegration] = useState("");
    const [sphere, setSphere] = useState("");
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        if (!userId) return;
        setLoading(true);
        try {
            const res = await reflectAPI.submit(userId, emotion, integration, sphere);
            setResult(res.data);
            setUser({ energy: (useUserStore.getState().energy || 0) + 10 });
        } catch (e: any) {
            if (e.response?.data?.detail?.includes("уже пройдена")) {
                setResult({ message: "Рефлексия уже пройдена сегодня", energy_awarded: 0 });
            }
        } finally {
            setLoading(false);
        }
    };

    if (result) return (
        <div className="min-h-screen flex flex-col items-center justify-center px-6 pb-24">
            <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                className="glass-strong p-8 text-center w-full max-w-sm">
                <div className="text-5xl mb-4">✅</div>
                <h2 className="text-xl font-bold mb-2 gradient-text">{result.message}</h2>
                {result.energy_awarded > 0 && (
                    <p className="text-3xl font-bold text-yellow-400 mb-2">+{result.energy_awarded} ✦</p>
                )}
                {result.hawkins_today > 0 && (
                    <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
                        Ваш уровень сейчас: {result.hawkins_level} ({result.hawkins_today})
                    </p>
                )}
                <button onClick={() => router.push("/")}
                    className="w-full py-3 rounded-xl" style={{ background: "var(--violet)", color: "#fff" }}>
                    На главную
                </button>
            </motion.div>
            <BottomNav active="reflect" />
        </div>
    );

    const steps = [
        {
            title: "Какую эмоцию вы ощущаете прямо сейчас?",
            content: (
                <div className="flex flex-wrap gap-2">
                    {EMOTIONS.map(e => (
                        <button key={e} onClick={() => setEmotion(e)}
                            className={`px-4 py-2 rounded-full text-sm transition-all ${emotion === e ? "text-white" : ""}`}
                            style={{
                                background: emotion === e ? "var(--violet)" : "rgba(255,255,255,0.06)",
                                border: `1px solid ${emotion === e ? "var(--violet)" : "var(--border)"}`,
                                color: emotion === e ? "#fff" : "var(--text-secondary)",
                            }}>
                            {e}
                        </button>
                    ))}
                    <input value={emotion} onChange={e => setEmotion(e.target.value)}
                        placeholder="или напишите своё..."
                        className="w-full px-4 py-2 rounded-xl text-sm outline-none"
                        style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
                </div>
            ),
        },
        {
            title: "Вчерашний интеграционный план выполнен?",
            content: (
                <div className="space-y-3">
                    {[["yes", "✅ Да, выполнил"], ["partial", "🌗 Частично"], ["no", "❌ Нет"]].map(([val, label]) => (
                        <button key={val} onClick={() => setIntegration(val)}
                            className="w-full py-3 rounded-xl text-sm font-medium transition-all"
                            style={{
                                background: integration === val ? "rgba(139,92,246,0.2)" : "rgba(255,255,255,0.04)",
                                border: `1px solid ${integration === val ? "var(--violet)" : "var(--border)"}`,
                                color: integration === val ? "var(--violet-l)" : "var(--text-secondary)",
                            }}>
                            {label}
                        </button>
                    ))}
                </div>
            ),
        },
        {
            title: "Какой сфере уделить внимание сегодня?",
            content: (
                <div className="grid grid-cols-2 gap-2">
                    {SPHERES.map(s => (
                        <button key={s} onClick={() => setSphere(s)}
                            className="py-3 rounded-xl text-sm transition-all"
                            style={{
                                background: sphere === s ? "rgba(139,92,246,0.2)" : "rgba(255,255,255,0.04)",
                                border: `1px solid ${sphere === s ? "var(--violet)" : "var(--border)"}`,
                                color: sphere === s ? "var(--violet-l)" : "var(--text-secondary)",
                            }}>
                            {SPHERE_NAMES[s]}
                        </button>
                    ))}
                </div>
            ),
        },
    ];
    const canProceed = [!!emotion, !!integration, !!sphere][step];

    return (
        <div className="min-h-screen pb-24 px-4">
            <div className="pt-6 pb-4">
                <h1 className="text-xl font-bold gradient-text">Ежедневная рефлексия</h1>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>3 вопроса · +10 ✦</p>
            </div>
            {/* Progress */}
            <div className="flex gap-2 mb-6">
                {steps.map((_, i) => (
                    <div key={i} className="flex-1 h-0.5 rounded-full" style={{ background: i <= step ? "var(--violet)" : "var(--border)" }} />
                ))}
            </div>
            <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                className="glass p-5 mb-4">
                <h2 className="text-base font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                    {steps[step].title}
                </h2>
                {steps[step].content}
            </motion.div>
            {step < 2 ? (
                <button onClick={() => setStep(s => s + 1)} disabled={!canProceed}
                    className="w-full py-4 rounded-2xl font-semibold transition-all"
                    style={{ background: canProceed ? "var(--violet)" : "rgba(255,255,255,0.06)", color: canProceed ? "#fff" : "var(--text-muted)" }}>
                    Далее →
                </button>
            ) : (
                <button onClick={handleSubmit} disabled={!canProceed || loading}
                    className="w-full py-4 rounded-2xl font-semibold"
                    style={{ background: canProceed ? "linear-gradient(135deg, var(--violet), var(--gold))" : "rgba(255,255,255,0.06)", color: canProceed ? "#fff" : "var(--text-muted)" }}>
                    {loading ? "Сохраняю..." : "Завершить · +10 ✦"}
                </button>
            )}
            {step > 0 && <button onClick={() => setStep(s => s - 1)} className="w-full mt-2 text-sm py-2" style={{ color: "var(--text-muted)" }}>← Назад</button>}
            <BottomNav active="reflect" />
        </div>
    );
}
