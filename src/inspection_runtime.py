"""D6 integration for D5 recommendations and their file contracts.

This module only wires the existing DataStore, ProductInspectionContext, and
InspectionRecommendationBuilder together.  It intentionally contains no D1-D5
matching, knowledge, applicability, or recommendation rules.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.data_store import DataStore
from src.inspection_applicability import ProductInspectionContext
from src.inspection_recommendation import InspectionRecommendationBuilder
from src.runtime import iso_now, read_json, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSPECTION_CONFIG_PATH = PROJECT_ROOT / "config" / "inspection_reference.json"
DEFAULT_RISK_SUBSTANCE_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "risk_substance_reference.json"
)
INSPECTION_CONTEXT_FILE = "inspection_context.json"
INSPECTION_RECOMMENDATION_FILE = "inspection_recommendation.json"
INSPECTION_RECOMMENDATION_ERROR_FILE = "inspection_recommendation_error.json"


class InspectionContextValidationError(ValueError):
    """An inspection context file or public update is invalid."""


class InspectionAnalysisUnavailableError(RuntimeError):
    """Phase 3 has not produced analysis.json for the selected product."""


def database_path_for_output_root(output_root: Path) -> Path:
    """Follow Local API's existing ``<output parent>/data/app.db`` convention."""

    return output_root.resolve().parent / "data" / "app.db"


def bootstrap_inspection_references(
    store: DataStore,
    inspection_config: Path = DEFAULT_INSPECTION_CONFIG_PATH,
    risk_substance_config: Path = DEFAULT_RISK_SUBSTANCE_CONFIG_PATH,
) -> dict[str, dict[str, int]]:
    """Initialize and idempotently import D5's two Reference dependencies."""

    if not inspection_config.is_file():
        raise FileNotFoundError(f"Inspection数据集不存在：{inspection_config}")
    if not risk_substance_config.is_file():
        raise FileNotFoundError(
            f"Risk-Substance数据集不存在：{risk_substance_config}"
        )
    store.initialize()
    return {
        "inspection": store.import_inspection_config(inspection_config),
        "risk_substance": store.import_risk_substance_config(
            risk_substance_config
        ),
    }


def _context_from_mapping(payload: Mapping[str, Any]) -> ProductInspectionContext:
    try:
        return ProductInspectionContext(
            product_category=payload.get("product_category"),
            product_form=payload.get("product_form"),
            confirmed_ingredient_contexts=payload.get(
                "confirmed_ingredient_contexts", []
            ),
            context_evidence=payload.get("context_evidence", []),
        )
    except (TypeError, ValueError) as exc:
        raise InspectionContextValidationError(str(exc)) from exc


def unknown_product_context() -> ProductInspectionContext:
    return ProductInspectionContext(
        product_category=None,
        product_form=None,
        confirmed_ingredient_contexts=[],
        context_evidence=[],
    )


def load_product_inspection_context(product_root: Path) -> ProductInspectionContext:
    """Load an explicit context file, or return the required unknown context."""

    context_path = product_root.resolve() / INSPECTION_CONTEXT_FILE
    if not context_path.is_file():
        return unknown_product_context()
    payload = read_json(context_path)
    if not isinstance(payload, Mapping):
        raise InspectionContextValidationError(
            "inspection_context.json必须包含JSON对象"
        )
    return _context_from_mapping(payload)


def validate_context_update(payload: Any) -> dict[str, Any]:
    """Validate human input without changing exact Reference strings."""

    if not isinstance(payload, dict):
        raise InspectionContextValidationError("请求体必须是JSON对象")

    def optional_exact_string(field: str) -> str | None:
        value = payload.get(field)
        if value is None:
            return None
        if not isinstance(value, str):
            raise InspectionContextValidationError(f"{field}必须是字符串或null")
        if not value:
            raise InspectionContextValidationError(f"{field}为空时必须使用null")
        if value != value.strip():
            raise InspectionContextValidationError(
                f"{field}不能包含首尾空白；请按Reference选项原样提交"
            )
        return value

    ingredients = payload.get("confirmed_ingredient_contexts", [])
    if not isinstance(ingredients, list):
        raise InspectionContextValidationError(
            "confirmed_ingredient_contexts必须是数组"
        )
    unique_ingredients: list[str] = []
    seen: set[str] = set()
    for value in ingredients:
        if not isinstance(value, str) or not value:
            raise InspectionContextValidationError(
                "confirmed_ingredient_contexts必须只包含非空字符串"
            )
        if value != value.strip():
            raise InspectionContextValidationError(
                "ingredient context不能包含首尾空白；请按Reference选项原样提交"
            )
        if value not in seen:
            unique_ingredients.append(value)
            seen.add(value)

    return {
        "product_category": optional_exact_string("product_category"),
        "product_form": optional_exact_string("product_form"),
        "confirmed_ingredient_contexts": unique_ingredients,
    }


def human_confirmed_context(payload: Any) -> ProductInspectionContext:
    """Create server-owned provenance for an accepted public context update."""

    values = validate_context_update(payload)
    confirmed_at = iso_now()
    evidence: list[dict[str, Any]] = []
    for field in ("product_category", "product_form"):
        value = values[field]
        if value is not None:
            evidence.append(
                {
                    "source_type": "human_confirmed",
                    "source_path": "local_web",
                    "field": field,
                    "value": value,
                    "confirmed_at": confirmed_at,
                }
            )
    for value in values["confirmed_ingredient_contexts"]:
        evidence.append(
            {
                "source_type": "human_confirmed",
                "source_path": "local_web",
                "field": "confirmed_ingredient_contexts",
                "value": value,
                "confirmed_at": confirmed_at,
            }
        )
    return ProductInspectionContext(
        **values,
        context_evidence=evidence,
    )


class InspectionRuntime:
    """Generate D5 files from explicit product artifacts and Reference index."""

    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.builder = InspectionRecommendationBuilder(store)

    @classmethod
    def create(
        cls,
        output_root: Path,
        *,
        database_path: Path | None = None,
        inspection_config: Path = DEFAULT_INSPECTION_CONFIG_PATH,
        risk_substance_config: Path = DEFAULT_RISK_SUBSTANCE_CONFIG_PATH,
    ) -> "InspectionRuntime":
        store = DataStore(
            database_path or database_path_for_output_root(output_root),
            output_root,
        )
        bootstrap_inspection_references(
            store,
            inspection_config,
            risk_substance_config,
        )
        return cls(store)

    @classmethod
    def from_store(
        cls,
        store: DataStore,
        *,
        inspection_config: Path = DEFAULT_INSPECTION_CONFIG_PATH,
        risk_substance_config: Path = DEFAULT_RISK_SUBSTANCE_CONFIG_PATH,
    ) -> "InspectionRuntime":
        bootstrap_inspection_references(
            store,
            inspection_config,
            risk_substance_config,
        )
        return cls(store)

    def generate(self, product_root: Path) -> dict[str, Any]:
        product_root = product_root.resolve()
        analysis_path = product_root / "analysis.json"
        if not analysis_path.is_file():
            raise InspectionAnalysisUnavailableError(
                "商品尚无analysis.json，不能生成抽检辅助建议"
            )
        analysis = read_json(analysis_path)
        if not isinstance(analysis, Mapping):
            raise InspectionAnalysisUnavailableError("analysis.json必须包含JSON对象")
        context = load_product_inspection_context(product_root)
        result = self.builder.build(analysis, context).to_dict()
        write_json(product_root / INSPECTION_RECOMMENDATION_FILE, result)
        (product_root / INSPECTION_RECOMMENDATION_ERROR_FILE).unlink(
            missing_ok=True
        )
        return result

    @staticmethod
    def record_error(product_root: Path, exc: BaseException) -> dict[str, Any]:
        payload = {
            "status": "error",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "updated_at": iso_now(),
        }
        product_root = product_root.resolve()
        (product_root / INSPECTION_RECOMMENDATION_FILE).unlink(missing_ok=True)
        write_json(product_root / INSPECTION_RECOMMENDATION_ERROR_FILE, payload)
        return payload

    def update_human_context(
        self, product_root: Path, payload: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        product_root = product_root.resolve()
        if not (product_root / "analysis.json").is_file():
            raise InspectionAnalysisUnavailableError(
                "商品尚无analysis.json，不能保存Context并重新评估"
            )
        context = human_confirmed_context(payload)
        write_json(product_root / INSPECTION_CONTEXT_FILE, context.to_dict())
        return context.to_dict(), self.generate(product_root)
