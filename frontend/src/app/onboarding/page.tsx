"use client";
import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { calcAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";

export default function OnboardingPage() {
    const router = useRouter();
    const { userId } = useUserStore();
    const [step, setStep] = useState(0);
    const [form, setForm] = useState({ birth_date: "", birth_time: "", birth_place: "" });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const steps = [
        {
            title: "Дата рождения",
            field: "birth_date",
            type: "date",
            placeholder: "1990-01-15",
            hint: "Точная дата — основа вашей карты",
            icon: "✦",
            iconColor: "var(--gold)",
            description: "Дата рождения формирует ядро вашей архетипической карты",
        },
        {
            title: "Время рождения",
            field: "birth_time",
            type: "time",
            placeholder: "14:30",
            hint: "Если не знаете — укажите 12:00 (снизит точность)",
            icon: "◉",
            iconColor: "var(--violet-l)",
            description: "Точное время раскрывает Асцендент и расположение домов",
        },
        {
            title: "Место рождения",
            field: "birth_place",
            type: "text",
            placeholder: "Москва, Россия",
            hint: "Введите город и страну",
            icon: "◈",
            iconColor: "var(--cyan)",
            description: "Географические координаты влияют на точность расчётов",
        },
    ];

    const handleNext = async () => {
        if (step < steps.length - 1) {
            setStep(s => s + 1);
            return;
        }
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
    const progress = ((step + 1) / steps.length) * 100;

    // Stable random particles (useMemo to avoid recalculation on each render)
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
        <div className="min-h-screen flex flex-col items-center justify-center px-5 relative overflow-hidden">

            {/* Ambient background glows */}
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
                <div style={{
                    position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
                    width: 340, height: 340,
                    background: "radial-gradient(circle, rgba(6,182,212,0.05) 0%, transparent 70%)",
                    borderRadius: "50%", filter: "blur(48px)"
                }} />
            </div>

            {/* Star particles */}
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

            <div className="relative z-10 w-full max-w-sm">

                {/* Logo */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                    className="text-center mb-10"
                >
                    {/* Hexagon logo mark */}
                    <div style={{
                        width: 64, height: 64, margin: "0 auto 16px",
                        background: "linear-gradient(135deg, rgba(139,92,246,0.25), rgba(245,158,11,0.15))",
                        border: "1px solid var(--border-glow)",
                        borderRadius: 18,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 28,
                        boxShadow: "0 8px 32px rgba(139,92,246,0.25)",
                    }}>
                        ✦
                    </div>
                    <h1 className="text-4xl font-bold gradient-text mb-1" style={{ fontFamily: "'Outfit', sans-serif", letterSpacing: "-0.5px" }}>
                        AVATAR
                    </h1>
                    <p className="text-xs" style={{ color: "var(--text-muted)", letterSpacing: "2px", textTransform: "uppercase" }}>
                        Платформа эволюции сознания
                    </p>
                </motion.div>

                {/* Progress bar */}
                <div className="mb-8">
                    <div className="flex justify-between mb-2" style={{ color: "var(--text-muted)" }}>
                        <span className="text-xs">Настройка профиля</span>
                        <span className="text-xs">{step + 1} / {steps.length}</span>
                    </div>
                    <div style={{ height: 3, background: "rgba(255,255,255,0.07)", borderRadius: 4, overflow: "hidden" }}>
                        <motion.div
                            style={{
                                height: "100%",
                                background: "linear-gradient(90deg, var(--violet), var(--gold))",
                                borderRadius: 4,
                            }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.4, ease: "easeOut" }}
                        />
                    </div>
                    {/* Step indicators */}
                    <div className="flex gap-3 mt-3">
                        {steps.map((s, i) => (
                            <motion.div key={i}
                                className="flex items-center gap-1.5"
                                animate={{ opacity: i <= step ? 1 : 0.35 }}
                                transition={{ duration: 0.3 }}
                            >
                                <div style={{
                                    width: 20, height: 20, borderRadius: "50%",
                                    background: i < step
                                        ? "linear-gradient(135deg, var(--violet), var(--gold))"
                                        : i === step
                                            ? "rgba(139,92,246,0.3)"
                                            : "rgba(255,255,255,0.05)",
                                    border: i === step ? "1px solid var(--border-glow)" : "1px solid transparent",
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    fontSize: 10,
                                }}>
                                    {i < step ? "✓" : <span style={{ color: s.iconColor, fontSize: 8 }}>{s.icon}</span>}
                                </div>
                                <span className="text-xs" style={{ color: i === step ? "var(--text-secondary)" : "var(--text-muted)", display: "none" }}>
                                    {s.title}
                                </span>
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Step card */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={step}
                        initial={{ opacity: 0, x: 40, scale: 0.97 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: -40, scale: 0.97 }}
                        transition={{ duration: 0.35, ease: "easeOut" }}
                        className="glass-strong mb-5"
                        style={{ padding: "28px 24px" }}
                    >
                        {/* Field icon & title */}
                        <div className="flex items-center gap-3 mb-4">
                            <div style={{
                                width: 44, height: 44, borderRadius: 12,
                                background: "rgba(255,255,255,0.04)",
                                border: "1px solid var(--border)",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: 20, color: currentStep.iconColor,
                                flexShrink: 0,
                            }}>
                                {currentStep.icon}
                            </div>
                            <div>
                                <h2 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                                    {currentStep.title}
                                </h2>
                                <p className="text-xs" style={{ color: "var(--text-muted)", marginTop: 1 }}>
                                    {currentStep.description}
                                </p>
                            </div>
                        </div>

                        {/* Divider */}
                        <div style={{ height: 1, background: "var(--border)", marginBottom: 20 }} />

                        {/* Input */}
                        <div style={{ position: "relative" }}>
                            <input
                                type={currentStep.type}
                                value={currentValue}
                                onChange={(e) => setForm(f => ({ ...f, [currentStep.field]: e.target.value }))}
                                placeholder={currentStep.placeholder}
                                autoFocus
                                className="w-full text-base outline-none transition-all"
                                style={{
                                    padding: "14px 16px",
                                    background: "rgba(255,255,255,0.05)",
                                    border: currentValue
                                        ? "1px solid var(--border-glow)"
                                        : "1px solid var(--border)",
                                    borderRadius: 12,
                                    color: "var(--text-primary)",
                                    fontSize: 16, // prevents iOS zoom
                                    WebkitTapHighlightColor: "transparent",
                                    boxShadow: currentValue
                                        ? "0 0 0 3px rgba(139,92,246,0.1)"
                                        : "none",
                                    transition: "all 0.2s ease",
                                    colorScheme: "dark",
                                }}
                            />
                            {currentValue && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.5 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    style={{
                                        position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)",
                                        color: "var(--emerald)", fontSize: 16,
                                    }}
                                >
                                    ✓
                                </motion.div>
                            )}
                        </div>

                        {/* Hint */}
                        <p className="text-xs mt-3 flex items-center gap-1.5" style={{ color: "var(--text-muted)" }}>
                            <span style={{ color: currentStep.iconColor, fontSize: 8 }}>●</span>
                            {currentStep.hint}
                        </p>
                    </motion.div>
                </AnimatePresence>

                {/* Error */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            style={{
                                padding: "10px 16px",
                                background: "rgba(236,72,153,0.1)",
                                border: "1px solid rgba(236,72,153,0.25)",
                                borderRadius: 10,
                                marginBottom: 16,
                            }}
                        >
                            <p className="text-sm text-center" style={{ color: "var(--rose)" }}>{error}</p>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Main button */}
                <motion.button
                    whileTap={{ scale: 0.97 }}
                    whileHover={currentValue && !loading ? { scale: 1.01 } : {}}
                    onClick={handleNext}
                    disabled={!currentValue || loading}
                    className="w-full font-semibold text-base transition-all"
                    style={{
                        padding: "15px 24px",
                        borderRadius: 14,
                        border: "none",
                        cursor: currentValue && !loading ? "pointer" : "not-allowed",
                        background: currentValue && !loading
                            ? "linear-gradient(135deg, var(--violet) 0%, #6366f1 100%)"
                            : "rgba(255,255,255,0.05)",
                        color: currentValue && !loading ? "#fff" : "var(--text-muted)",
                        boxShadow: currentValue && !loading
                            ? "0 8px 28px rgba(139,92,246,0.45)"
                            : "none",
                        transition: "all 0.25s ease",
                    }}
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <motion.span
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                style={{ display: "inline-block" }}
                            >⟳</motion.span>
                            Строим карту...
                        </span>
                    ) : step < steps.length - 1 ? (
                        "Далее →"
                    ) : (
                        "Построить карту ✨"
                    )}
                </motion.button>

                {/* Back button */}
                <AnimatePresence>
                    {step > 0 && !loading && (
                        <motion.button
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 8 }}
                            onClick={() => setStep(s => s - 1)}
                            className="w-full mt-3 text-sm font-medium transition-all"
                            style={{
                                padding: "12px",
                                background: "transparent",
                                border: "none",
                                color: "var(--text-muted)",
                                cursor: "pointer",
                            }}
                            whileTap={{ scale: 0.97 }}
                        >
                            ← Назад
                        </motion.button>
                    )}
                </AnimatePresence>

                {/* Bio trust signal */}
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="text-center text-xs mt-6"
                    style={{ color: "var(--text-muted)" }}
                >
                    🔒 Данные защищены и используются только для расчёта карты
                </motion.p>
            </div>
        </div>
    );
}
