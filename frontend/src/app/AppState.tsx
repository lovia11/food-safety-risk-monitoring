import {
  createContext,
  type ReactNode,
  useContext,
  useMemo,
  useState,
} from "react";

type AppStateValue = {
  currentSamplingCount: number | null;
  setCurrentSamplingCount: (count: number | null) => void;
};

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [currentSamplingCount, setCurrentSamplingCount] = useState<number | null>(
    null,
  );
  const value = useMemo(
    () => ({ currentSamplingCount, setCurrentSamplingCount }),
    [currentSamplingCount],
  );

  return (
    <AppStateContext.Provider value={value}>
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) {
    throw new Error("useAppState 必须在 AppStateProvider 内使用");
  }
  return value;
}
