"use client";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { assistantAPI, voiceAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import SacredGeometryLogo from "@/components/SacredGeometryLogo";

const MicIcon = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
);

export default function AssistantPage() {
    const router = useRouter();
    const { userId } = useUserStore();
    const [messages, setMessages] = useState<{ role: string, content: string }[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<number | null>(null);
    const [isInitialized, setIsInitialized] = useState(false);
    const [isFirstTouch, setIsFirstTouch] = useState(false);
    
    const scrollRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Initialization
    useEffect(() => {
        if (!userId) return;
        const init = async () => {
            try {
                const res = await assistantAPI.init(userId);
                setSessionId(res.data.session_id);
                setIsFirstTouch(res.data.is_first_touch);
                setMessages([{ role: "assistant", content: res.data.ai_response }]);
                setIsInitialized(true);
            } catch (err) {
                console.error("Assistant init error:", err);
            }
        };
        init();
    }, [userId]);

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading || !sessionId || !userId) return;
        
        const userMsg = input.trim();
        const newHistory = [...messages, { role: "user", content: userMsg }];
        setMessages(newHistory);
        setInput("");
        setLoading(true);

        try {
            const res = await assistantAPI.chat(userId, sessionId, userMsg);
            setMessages([...newHistory, { role: "assistant", content: res.data.ai_response }]);
        } catch (err) {
            console.error("Assistant chat error:", err);
            setMessages([...newHistory, { role: "assistant", content: "Прости, мое зеркало помутнело. Давай попробуем еще раз?" }]);
        } finally {
            setLoading(false);
        }
    };

    const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, window.innerHeight * 0.4)}px`;
        }
    };

    const particles = useMemo(() =>
        Array.from({ length: 20 }, (_, i) => ({
            left: `${(i * 37 + 5) % 100}%`,
            top: `${(i * 53 + 10) % 100}%`,
            opacity: 0.03 + (i % 5) * 0.03,
            duration: 3 + (i % 4),
            delay: (i % 6) * 0.5,
            size: i % 3 === 0 ? 2 : 1,
        })), []);

    if (!isInitialized) {
        return (
            <div className="min-h-screen bg-[#060818] flex flex-col items-center justify-center p-10">
                <SacredGeometryLogo size={180} progress={0.5} />
                <p className="mt-8 text-white/20 uppercase tracking-[0.3em] text-[10px] animate-pulse">Настройка зеркала...</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#060818] text-white flex flex-col relative overflow-hidden">
            {/* Background Particles */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
                {particles.map((p, i) => (
                    <motion.div key={i}
                        className="absolute rounded-full bg-white"
                        style={{ left: p.left, top: p.top, width: p.size, height: p.size, opacity: p.opacity }}
                        animate={{ opacity: [p.opacity, p.opacity * 4, p.opacity] }}
                        transition={{ duration: p.duration, repeat: Infinity, delay: p.delay }}
                    />
                ))}
            </div>

            {/* Header */}
            <header className="relative z-20 px-4 py-3 border-bottom border-white/5 flex items-center justify-between backdrop-blur-md bg-[#060818]/40">
                <button onClick={() => router.push("/")} className="text-white/40 text-xs font-bold uppercase tracking-widest">Назад</button>
                <div className="flex flex-col items-center">
                    <span className="text-[10px] font-bold text-amber-500/80 uppercase tracking-[0.2em]">Цифровой Помощник</span>
                    <span className="text-[8px] text-white/20 uppercase tracking-widest">Зеркало Личности</span>
                </div>
                <div className="w-10" />
            </header>

            {/* Chat Messages */}
            <div 
                ref={scrollRef}
                className="flex-1 overflow-y-auto px-4 py-6 flex flex-col gap-6 relative z-10 no-scrollbar"
            >
                {messages.map((msg, i) => (
                    <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        key={i} 
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div className={`
                            max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed
                            ${msg.role === 'user' 
                                ? 'bg-amber-500/10 border border-amber-500/20 text-amber-100 rounded-tr-none' 
                                : 'bg-white/5 border border-white/10 text-white/90 rounded-tl-none'}
                        `}>
                            {msg.content}
                        </div>
                    </motion.div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white/5 border border-white/10 px-4 py-2 rounded-2xl rounded-tl-none animate-pulse">
                            <span className="text-[10px] text-white/20 uppercase tracking-widest">Зеркало настраивается...</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="relative z-20 px-4 pt-2 pb-8 bg-gradient-to-t from-[#060818] via-[#060818]/95 to-transparent">
                <div className="relative flex items-end gap-3 max-w-[500px] mx-auto">
                    <div className="relative flex-1">
                        <textarea
                            ref={textareaRef}
                            rows={1}
                            value={input}
                            onChange={handleTextChange}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSend();
                                }
                            }}
                            placeholder="О чем молчит твоё отражение?"
                            className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3.5 text-sm text-white placeholder:text-white/20 outline-none focus:border-amber-500/40 transition-all resize-none max-h-[200px]"
                        />
                        <button 
                            onClick={handleSend}
                            disabled={!input.trim() || loading}
                            className="absolute right-2 bottom-2 w-9 h-9 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center disabled:opacity-20 transition-all"
                        >
                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="12" y1="19" x2="12" y2="5" />
                                <polyline points="5 12 12 5 19 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
