"""Construct :class:`DataSource` implementations by registered kind id."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pa_agent.data.base import DataSource
from pa_agent.data.market_defaults import (
    A_SHARE_DEFAULT_SYMBOL,
    GOLD_MT5_SYMBOL,
    GOLD_TV_SYMBOL,
)
from pa_agent.data.registry import DataSourceBuilder, DataSourceRegistry, DataSourceSpec
from pa_agent.extensions import discover_data_source_extensions

if TYPE_CHECKING:
    from pa_agent.config.settings import Settings

DataSourceKind = Literal[
    "mt5",
    "tradingview",
    "akshare",
    "eastmoney",
    "tushare",
    "yfinance",
]

_REGISTRY = DataSourceRegistry()


def _build_mt5(_settings: Settings | None) -> DataSource:
    from pa_agent.data.mt5 import MT5Source

    return MT5Source()


def _build_tradingview(_settings: Settings | None) -> DataSource:
    from pa_agent.data.tradingview import TradingViewSource

    return TradingViewSource()


def _build_akshare(_settings: Settings | None) -> DataSource:
    from pa_agent.data.akshare_source import AkShareSource

    return AkShareSource()


def _build_eastmoney(_settings: Settings | None) -> DataSource:
    from pa_agent.data.eastmoney_source import EastMoneySource

    return EastMoneySource()


def _build_tushare(settings: Settings | None) -> DataSource:
    if settings is None:
        from pa_agent.config.paths import SETTINGS_JSON_PATH
        from pa_agent.config.settings import load_settings

        settings = load_settings(SETTINGS_JSON_PATH)

    from pa_agent.data.tushare_source import TushareSource

    return TushareSource(settings=settings)


def _build_yfinance(_settings: Settings | None) -> DataSource:
    from pa_agent.data.yfinance_source import YFinanceSource

    return YFinanceSource()


def _register_builtin_sources() -> None:
    """Register built-ins without importing their optional dependencies."""
    for spec in (
        DataSourceSpec("mt5", "MT5", GOLD_MT5_SYMBOL, _build_mt5, visible=True),
        DataSourceSpec(
            "tradingview", "TradingView", GOLD_TV_SYMBOL, _build_tradingview, visible=True
        ),
        DataSourceSpec("akshare", "AkShare", A_SHARE_DEFAULT_SYMBOL, _build_akshare),
        DataSourceSpec("eastmoney", "东方财富", A_SHARE_DEFAULT_SYMBOL, _build_eastmoney),
        DataSourceSpec("tushare", "Tushare(A股)", A_SHARE_DEFAULT_SYMBOL, _build_tushare),
        DataSourceSpec("yfinance", "YFinance", "GC=F", _build_yfinance),
    ):
        _REGISTRY.register(spec)


_register_builtin_sources()
discover_data_source_extensions(_REGISTRY)

# Compatibility snapshot for existing GUI callers. New integrations should use
# ``data_source_choices()`` so runtime registrations are visible dynamically.
DATA_SOURCE_CHOICES: tuple[tuple[DataSourceKind, str], ...] = _REGISTRY.choices()  # type: ignore[assignment]
_HIDDEN_KINDS: frozenset[DataSourceKind] = frozenset(
    spec.kind for spec in _REGISTRY.specs() if not spec.visible
)
_DEFAULT_SYMBOLS: dict[DataSourceKind, str] = {
    spec.kind: spec.default_symbol for spec in _REGISTRY.specs()
}


def default_tradingview_exchange() -> str:
    """Empty string = UI «(自动)» — probe all TV preset venues."""
    return ""


def normalize_data_source_kind(kind: str | None) -> DataSourceKind:
    """Return a supported data-source kind, defaulting to MT5."""
    spec = _REGISTRY.get(kind) if kind is not None else None
    if spec is not None:
        return spec.kind  # type: ignore[return-value]
    return "mt5"


def data_source_label(kind: str | None) -> str:
    """Human-readable label for *kind*."""
    normalized = normalize_data_source_kind(kind)
    spec = _REGISTRY.get(normalized)
    return spec.label if spec is not None else "MT5"


def default_symbol_for_kind(kind: str | None) -> str:
    normalized = normalize_data_source_kind(kind)
    spec = _REGISTRY.get(normalized)
    return spec.default_symbol if spec is not None else GOLD_MT5_SYMBOL


def data_source_choices() -> tuple[tuple[str, str], ...]:
    """Return UI-visible sources, including runtime registrations."""
    return _REGISTRY.choices()


def register_data_source(
    kind: str,
    *,
    label: str,
    default_symbol: str,
    builder: DataSourceBuilder,
    visible: bool = False,
    replace: bool = False,
) -> None:
    """Register a custom data source without editing this factory."""
    _REGISTRY.register(
        DataSourceSpec(
            kind=kind,
            label=label,
            default_symbol=default_symbol,
            builder=builder,
            visible=visible,
        ),
        replace=replace,
    )


def unregister_data_source(kind: str) -> DataSourceSpec | None:
    """Remove a runtime data source registration."""
    return _REGISTRY.unregister(kind)


def create_data_source(kind: str | None, settings: Settings | None = None) -> DataSource:
    """Instantiate a fresh data source for *kind* (not connected).

    ``settings`` is injected by callers that already hold the loaded
    :class:`Settings` (``app_context.bootstrap`` and the GUI data-source
    switch). Only the Tushare source needs it (for its API token); when a
    caller omits it, the Tushare branch lazily loads ``settings.json`` as a
    fallback so standalone/programmatic construction still works.
    """
    normalized = normalize_data_source_kind(kind)
    spec = _REGISTRY.get(normalized)
    if spec is None:
        spec = _REGISTRY.get("mt5")
    assert spec is not None
    return spec.builder(settings)
