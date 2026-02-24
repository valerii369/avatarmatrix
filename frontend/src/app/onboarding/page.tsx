"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { calcAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";

const SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"];

export default function OnboardingPage() {
    const router = useRouter();
    const { userId } = useUserStore();
    const [step, setStep] = useState(0);
    const [form, setForm] = useState({ birth_date: "", birth_time: "", birth_place: "" });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const steps = [
        { title: "Дата рождения", field: "birth_date", type: "date", placeholder: "1990-01-15", hint: "Точная дата — основа вашей карты" },
        { title: "Время рождения", field: "birth_time", type: "time", placeholder: "14:30", hint: "Если не знаете — укажите 12:00 (снизит точность)" },
        { title: "Место рождения", field: "birth_place", type: "text", placeholder: "Москва, Россия", hint: "Город и страна рождения" },
    ];

    const handleNext = async () => {
        if (step < steps.length - 1) {
            setStep(s => s + 1);
            return;
        }
        // Calculate
        setLoading(true);
        setError("");
        try {
            await calcAPI.calculate({
                birth_date: form.birth_date,
                birth_time: form.birth_time || "12:00",
                birth_place: form.birth_place,
                user_id: userId!,
            });
            router.push("/");
        } catch (e: any) {
            setError(e.response?.data?.detail || "Ошибка расчёта. Проверьте данные.");
        } finally {
            setLoading(false);
        }
    };

    const currentStep = steps[step];
    const currentValue = form[currentStep.field as keyof typeof form];

    return (
        <div className="min-h-screen flex flex-col items-center justify-center px-6">
            {/* Stars decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {[...Array(20)].map((_, i) => (
                    <motion.div key={i}
                        className="absolute w-1 h-1 rounded-full bg-white"
                        style={{ left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%`, opacity: 0.1 + Math.random() * 0.2 }}
                        animate={{ opacity: [0.1, 0.4, 0.1] }}
                        transition={{ duration: 2 + Math.random() * 3, repeat: Infinity, delay: Math.random() * 2 }} />
                ))}
            </div>

            <div className="relative z-10 w-full max-w-sm">
                {/* Logo */}
                <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-8">
                    <h1 className="text-4xl font-bold gradient-text mb-2">AVATAR</h1>
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                        Платформа эволюции сознания
                    </p>
                </motion.div>

                {/* Progress */}
                <div className="flex gap-2 mb-8">
                    {steps.map((_, i) => (
                        <div key={i} className="flex-1 h-0.5 rounded-full transition-all"
                            style={{ background: i <= step ? "var(--violet)" : "var(--border)" }} />
                    ))}
                </div>

                {/* Step card */}
                <motion.div key={step} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }}
                    className="glass-strong p-6 mb-6">
                    <p className="text-xs mb-1" style={{ color: "var(--violet-l)" }}>
                        Шаг {step + 1} из {steps.length}
                    </p>
                    <h2 className="text-xl font-bold mb-4" style={{ color: "var(--text-primary)" }}>
                        {currentStep.title}
                    </h2>
                    <input
                        type={currentStep.type}
                        value={currentValue}
                        onChange={(e) => setForm(f => ({ ...f, [currentStep.field]: e.target.value }))}
                        placeholder={currentStep.placeholder}
                        className="w-full px-4 py-3 rounded-xl text-base outline-none transition-all"
                        style={{
                            background: "rgba(255,255,255,0.06)",
                            border: "1px solid var(--border)",
                            color: "var(--text-primary)",
                        }}
                    />
                    <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                        {currentStep.hint}
                    </p>
                </motion.div>

                {error && (
                    <p className="text-sm text-red-400 mb-4 text-center">{error}</p>
                )}

                <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={handleNext}
                    disabled={!currentValue || loading}
                    className="w-full py-4 rounded-2xl font-semibold text-base transition-all"
                    style={{
                        background: currentValue && !loading
                            ? "linear-gradient(135deg, var(--violet), #6366f1)"
                            : "rgba(255,255,255,0.06)",
                        color: currentValue && !loading ? "#fff" : "var(--text-muted)",
                        boxShadow: currentValue && !loading ? "0 8px 24px rgba(139,92,246,0.4)" : "none",
                    }}>
                    {loading ? "Рассчитываем карту..." : step < steps.length - 1 ? "Далее →" : "Построить карту ✨"}
                </motion.button>

                {step > 0 && !loading && (
                    <button onClick={() => setStep(s => s - 1)}
                        className="w-full mt-3 text-sm"
                        style={{ color: "var(--text-muted)" }}>
                        ← Назад
                    </button>
                )}
            </div>
        </div>
    );
}
