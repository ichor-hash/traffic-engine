/* ── Toast — Material 3 notification system ── */

import { useState, useCallback, useRef, useEffect } from "react";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

export interface ToastData {
    id: string;
    type: "error" | "success" | "info";
    title: string;
    description?: string;
    onClick?: () => void;
    duration?: number;
}

interface ToastItemProps {
    toast: ToastData;
    onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
    const [exiting, setExiting] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => {
            setExiting(true);
            setTimeout(() => onDismiss(toast.id), 250);
        }, toast.duration ?? 5000);
        return () => clearTimeout(timer);
    }, [toast, onDismiss]);

    const handleClick = () => {
        if (toast.onClick) toast.onClick();
        setExiting(true);
        setTimeout(() => onDismiss(toast.id), 250);
    };

    const Icon = toast.type === "error" ? AlertTriangle
        : toast.type === "success" ? CheckCircle2
            : Info;

    return (
        <div className={`toast ${exiting ? "exit" : ""}`} onClick={handleClick}>
            <div className={`toast-icon ${toast.type}`}>
                <Icon />
            </div>
            <div className="toast-body">
                <div className="toast-title">{toast.title}</div>
                {toast.description && <div className="toast-desc">{toast.description}</div>}
            </div>
        </div>
    );
}

export function ToastContainer({ toasts, onDismiss }: {
    toasts: ToastData[];
    onDismiss: (id: string) => void;
}) {
    return (
        <div className="toast-container">
            {toasts.map(t => (
                <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
            ))}
        </div>
    );
}

let _counter = 0;

export function useToast() {
    const [toasts, setToasts] = useState<ToastData[]>([]);

    const addToast = useCallback((t: Omit<ToastData, "id">) => {
        const id = `toast-${++_counter}`;
        setToasts(prev => [...prev, { ...t, id }]);
        return id;
    }, []);

    const dismissToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    return { toasts, addToast, dismissToast };
}
