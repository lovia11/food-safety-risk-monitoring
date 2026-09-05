"use strict";

export function defaultProductQueryState() {
  return {
    filters: {
      targetId: "",
      query: "",
      reviewStatus: "",
      effect: "",
      taskId: "",
    },
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    items: [],
    loading: false,
    error: "",
    loaded: false,
    requestToken: 0,
  };
}

export const appState = {
  currentView: "overview",
  current: null,
  history: null,
  selectedRunSnapshot: null,
  runs: [],
  selectedRun: null,
  selectedProduct: null,
  selectedImagePath: null,
  businessSnapshot: null,
  reviewLoadToken: 0,
  inspectionContextOptions: null,
  inspectionContextOptionsError: "",
  pollTimer: null,
  monitorTargets: [],
  productQuery: defaultProductQueryState(),
};

export function allRunSnapshots() {
  const unique = new Map();
  [appState.current, appState.history, appState.selectedRunSnapshot]
    .filter(Boolean)
    .forEach(snapshot => unique.set(snapshot.task.id, snapshot));
  return [...unique.values()];
}

export function findRunProduct(runId, productId) {
  const snapshot = allRunSnapshots().find(item => item.task.id === runId);
  const product = snapshot?.products.find(item => item.id === productId);
  return { snapshot, product };
}

export function clearProductSelection() {
  appState.selectedRun = null;
  appState.selectedProduct = null;
  appState.selectedImagePath = null;
  appState.businessSnapshot = null;
  appState.selectedRunSnapshot = null;
}
