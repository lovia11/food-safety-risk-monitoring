import { Save } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import type {
  InspectionContextOptions,
  ProductContext,
} from "../api/contracts";
import { getInspectionContextOptions } from "../api/products";
import { LoadingState } from "./LoadingState";

type ProductContextFormProps = {
  context: ProductContext;
  saving: boolean;
  onSave: (context: {
    product_category: string | null;
    product_form: string | null;
    confirmed_ingredient_contexts: string[];
  }) => Promise<void>;
};

export function ProductContextForm({
  context,
  saving,
  onSave,
}: ProductContextFormProps) {
  const [options, setOptions] = useState<InspectionContextOptions | null>(null);
  const [error, setError] = useState("");
  const [category, setCategory] = useState(context.product_category || "");
  const [form, setForm] = useState(context.product_form || "");
  const [ingredients, setIngredients] = useState(
    context.confirmed_ingredient_contexts,
  );

  useEffect(() => {
    setCategory(context.product_category || "");
    setForm(context.product_form || "");
    setIngredients(context.confirmed_ingredient_contexts);
  }, [context]);

  useEffect(() => {
    const controller = new AbortController();
    getInspectionContextOptions(controller.signal)
      .then(setOptions)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "上下文选项加载失败");
        }
      });
    return () => controller.abort();
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await onSave({
      product_category: category || null,
      product_form: form || null,
      confirmed_ingredient_contexts: ingredients,
    });
  };

  return (
    <section className="detail-section context-form-section">
      <h3>补充商品信息</h3>
      <p className="section-description">
        仅在方法适用性确实需要时填写；无法从页面确认的信息请保持“无法确认”。
      </p>
      {!options && !error ? (
        <LoadingState label="正在加载真实可选值" />
      ) : error ? (
        <div className="inline-message" data-tone="danger">{error}</div>
      ) : (
        <form className="context-form" onSubmit={submit}>
          <label>
            商品类别
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="">无法确认</option>
              {options?.product_categories.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            产品形态
            <select value={form} onChange={(event) => setForm(event.target.value)}>
              <option value="">无法确认</option>
              {options?.product_forms.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <label className="context-ingredients">
            已确认配料/原料信息
            <select
              multiple
              value={ingredients}
              onChange={(event) =>
                setIngredients(
                  Array.from(event.target.selectedOptions, (option) => option.value),
                )
              }
            >
              {options?.ingredient_contexts.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
            <small>可按 Ctrl 或 Command 多选；未确认时不选择。</small>
          </label>
          <button type="submit" className="primary-button" disabled={saving}>
            <Save size={15} /> {saving ? "正在保存并重算" : "保存并重新评估"}
          </button>
        </form>
      )}
    </section>
  );
}
