import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

type ToastTone = "info" | "success" | "danger";
type ToastItem = { id: number; message: string; tone: ToastTone };
type ToastContextValue = {
  pushToast: (message: string, tone?: ToastTone) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const pushToast = useCallback((message: string, tone: ToastTone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((items) => [...items, { id, message, tone }]);
    window.setTimeout(
      () => setToasts((items) => items.filter((item) => item.id !== id)),
      4200,
    );
  }, []);
  const value = useMemo(() => ({ pushToast }), [pushToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div key={toast.id} className="toast" data-tone={toast.tone}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) {
    throw new Error("useToast 必须在 ToastProvider 内使用");
  }
  return value;
}
