import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { getSamplingList } from "../api/sampling";

type AppStateValue = {
  currentSamplingCount: number | null;
  setCurrentSamplingCount: (count: number | null) => void;
  refreshSamplingCount: () => Promise<void>;
};

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [currentSamplingCount, setCurrentSamplingCount] = useState<number | null>(
    null,
  );
  const refreshSamplingCount = useCallback(async () => {
    try {
      const result = await getSamplingList();
      setCurrentSamplingCount(result.count);
    } catch {
      setCurrentSamplingCount(null);
    }
  }, []);
  useEffect(() => {
    void refreshSamplingCount();
  }, [refreshSamplingCount]);
  const value = useMemo(
    () => ({ currentSamplingCount, setCurrentSamplingCount, refreshSamplingCount }),
    [currentSamplingCount, refreshSamplingCount],
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
