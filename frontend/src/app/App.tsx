import { ToastProvider } from "../components/ToastProvider";
import { AppRouter } from "./AppRouter";
import { AppStateProvider } from "./AppState";

export function App() {
  return (
    <AppStateProvider>
      <ToastProvider>
        <AppRouter />
      </ToastProvider>
    </AppStateProvider>
  );
}
