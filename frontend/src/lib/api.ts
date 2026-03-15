import axios from "axios";

// API endpoint via environment variable or fallback to production
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://avatar.aiguro.pro";

export const api = axios.create({
    baseURL: API_BASE,
    timeout: 60000,
});

export const voiceAxios = axios.create({
    baseURL: API_BASE,
    timeout: 60000,   // 60s for Whisper transcription
});

voiceAxios.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("avatar_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Inject user token from localStorage
api.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("avatar_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const authAPI = {
    login: (initData: string, testMode = false) =>
        api.post("/api/auth", { initData, test_mode: testMode }),
};

export const calcAPI = {
    calculate: (data: { birth_date: string; birth_time: string; birth_place: string; user_id: number; gender?: string }) =>
        api.post("/api/calc", data),
    geocode: (place: string) =>
        api.post("/api/calc/geocode", { birth_place: place }),
};

export const cardsAPI = {
    getAll: (userId: number) => api.get(`/api/cards/${userId}`),
    getOne: (userId: number, cardId: number) => api.get(`/api/cards/${userId}/card/${cardId}`),
    getHistory: (userId: number, cardId: number) => api.get(`/api/cards/${userId}/card/${cardId}/history`),
};

export const syncAPI = {
    start: (userId: number, cardProgressId: number) =>
        api.post("/api/sync/start", { user_id: userId, card_progress_id: cardProgressId }),
    phase: (userId: number, syncSessionId: number, phase: number, userResponse?: string) =>
        api.post("/api/sync/phase", { user_id: userId, sync_session_id: syncSessionId, phase, user_response: userResponse }),
};

export const diaryAPI = {
    create: (data: Record<string, unknown>) => api.post("/api/diary", data),
    getAll: (userId: number, sphere?: string, entryType?: string, excludeType?: string) =>
        api.get(`/api/diary/${userId}`, { params: { sphere, entry_type: entryType, exclude_type: excludeType } }),
    updateIntegration: (userId: number, entryId: number, done: boolean, partial = false) =>
        api.post("/api/diary/integration", { user_id: userId, entry_id: entryId, done, partial }),
};

export const gameAPI = {
    getState: (userId: number) => api.get(`/api/game/${userId}`),
};

export const profileAPI = {
    get: (userId: number) => api.get(`/api/profile/${userId}`),
    getReferrals: (userId: number) => api.get(`/api/profile/${userId}/referrals`),
    reset: (tgId: number) => api.post(`/api/profile/tg/${tgId}/reset`),
};

export const reflectAPI = {
    submit: (userId: number, content: string, useAi = true, isVoice = false) =>
        api.post("/api/reflect", { user_id: userId, content, use_ai: useAi, is_voice: isVoice }),
    chatStart: (userId: number, content: string) =>
        api.post("/api/reflect/chat/start", { user_id: userId, content }),
    chatMessage: (userId: number, sessionId: number, message: string) =>
        api.post("/api/reflect/chat/message", { user_id: userId, session_id: sessionId, message }),
    chatFinish: (userId: number, sessionId: number) =>
        api.post("/api/reflect/chat/finish", { user_id: userId, session_id: sessionId, message: "FINISH" }),
};

export const retro = {
    week: (userId: number) => api.get(`/api/retro/${userId}/week`),
    month: (userId: number) => api.get(`/api/retro/${userId}/month`),
};

export const voiceAPI = {
    transcribe: (userId: number, audioBlob: Blob, sessionType = "general") => {
        const form = new FormData();
        form.append("user_id", String(userId));
        form.append("session_type", sessionType);
        // Use the correct file extension based on actual mime type
        const ext = audioBlob.type.includes("mp4") ? "m4a" : "webm";
        form.append("audio", audioBlob, `voice.${ext}`);
        return voiceAxios.post("/api/voice", form);
    },
};

export const visualAPI = {
    getSet: (userId: number, count = 4) => api.get("/api/visual/set", { params: { user_id: userId, count } }),
    report: (data: {
        user_id: number;
        shown_ids: number[];
        selected_id: number | null;
        reaction_time_ms: number;
        context_tag?: string;
        interactions?: any[];
    }) => api.post("/api/visual/report", data),
    logEvent: (data: { user_id: number; session_id?: number; event_type: string; payload: any }) =>
        api.post("/api/visual/event", data),
};
export const paymentsAPI = {
    getOffers: () => api.get("/api/payments/offers"),
    createInvoice: (userId: number, offerId: string) =>
        api.post("/api/payments/create-invoice", { user_id: userId, offer_id: offerId }),
};
export const economyAPI = {
    claim: (userId: number) => api.post("/api/economy/claim", { user_id: userId }),
};

export const masterHubAPI = {
    get: (userId: number) => api.get(`/api/master-hub/${userId}`),
};

export const assistantAPI = {
    init: (userId: number) => api.post("/api/assistant/init", { user_id: userId }),
    chat: (userId: number, sessionId: number, message: string) =>
        api.post("/api/assistant/chat", { user_id: userId, session_id: sessionId, message }),
    finish: (userId: number, sessionId: number) =>
        api.post("/api/assistant/finish", { user_id: userId, session_id: sessionId }),
    saveToDiary: (userId: number, sessionId: number) =>
        api.post("/api/assistant/save-to-diary", { user_id: userId, session_id: sessionId }),
};

// WebSocket helper
export function createSessionWS(userId: number, cardProgressId: number): WebSocket {
    const wsBase = API_BASE.replace("http", "ws");
    return new WebSocket(`${wsBase}/api/session/${userId}/${cardProgressId}`);
}
