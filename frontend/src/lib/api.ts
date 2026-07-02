const API_BASE_URL = "http://localhost:8000/api";

export interface Topic {
    id: number;
    week_id: number;
    content: string;
    category: string;
    order_num: number;
    completed: boolean;
}

export interface Week {
    id: number;
    month_id: number;
    number: number;
    title: string;
    topics: Topic[];
}

export interface Month {
    id: number;
    number: number;
    title: string;
    focus?: string;
    build_target?: string;
    weeks: Week[];
}

export interface QuizQuestion {
    question: string;
    options: string[];
    correct_answer_idx: number;
}

export interface LessonMaterial {
    voice_script: string;
    technical_notes: string;
    quiz: QuizQuestion[];
}

export interface ProgressStatus {
    total_topics: number;
    completed_topics: number;
    progress_percent: number;
    current_topic_id?: number | null;
}

export async function getMonths(): Promise<Month[]> {
    const res = await fetch(`${API_BASE_URL}/months`);
    if (!res.ok) throw new Error("Failed to fetch months");
    return res.json();
}

export async function toggleTopicCompletion(topicId: number): Promise<{ topic_id: number; completed: boolean }> {
    const res = await fetch(`${API_BASE_URL}/topics/${topicId}/toggle`, {
        method: "POST",
    });
    if (!res.ok) throw new Error("Failed to toggle completion");
    return res.json();
}

export async function getTopicMaterial(topicId: number): Promise<LessonMaterial> {
    const res = await fetch(`${API_BASE_URL}/topics/${topicId}/material`);
    if (!res.ok) throw new Error("Failed to fetch topic material");
    return res.json();
}

export async function getClassroomStatus(): Promise<ProgressStatus> {
    const res = await fetch(`${API_BASE_URL}/classroom/status`);
    if (!res.ok) throw new Error("Failed to fetch classroom status");
    return res.json();
}

export async function updateCurrentLesson(topicId: number | null): Promise<{ current_topic_id: number | null }> {
    const res = await fetch(`${API_BASE_URL}/classroom/current-lesson`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic_id: topicId }),
    });
    if (!res.ok) throw new Error("Failed to update active lesson");
    return res.json();
}
