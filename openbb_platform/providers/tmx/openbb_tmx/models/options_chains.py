"""TMX Options Chains Model."""

# pylint: disable=unused-argument
from datetime import (
    date as dateType,
    datetime,
)
from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.options_chains import (
    OptionsChainsData,
    OptionsChainsQueryParams,
)
from openbb_core.provider.utils.descriptions import (
    QUERY_DESCRIPTIONS,
)
from pydantic import Field, field_validator


class TmxOptionsChainsQueryParams(OptionsChainsQueryParams):
    """TMX Options Chains Query.

    Source: https://www.Tmx.com/
    """

    date: Optional[dateType] = Field(
        description=QUERY_DESCRIPTIONS.get("date", ""),
        default=None,
    )
    use_cache: bool = Field(
        default=True,
        description="Caching is used to validate the supplied ticker symbol, or if a historical EOD chain is requested."
        + " To bypass, set to False.",
    )


class TmxOptionsChainsData(OptionsChainsData):
    """TMX Options Chains Data."""

    transactions: Optional[int] = Field(
        description="Number of transactions for the contract.", default=None
    )
    total_value: Optional[float] = Field(
        description="Total value of the transactions.", default=None
    )
    settlement_price: Optional[float] = Field(
        description="Settlement price on that date.", default=None
    )

    @field_validator("expiration", mode="before", check_fields=False)
    @classmethod
    def date_validate(cls, v):  # pylint: disable=E0213
        """Return the datetime object from the date string"""
        return datetime.strptime(v, "%Y-%m-%d")


class TmxOptionsChainsFetcher(
    Fetcher[
        TmxOptionsChainsQueryParams,
        List[TmxOptionsChainsData],
    ]
):
    """TMX Options Chains Fetcher."""

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> TmxOptionsChainsQueryParams:
        """Transform the query."""
        return TmxOptionsChainsQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: TmxOptionsChainsQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Return the data."""
        # pylint: disable=import-outside-toplevel
        from openbb_tmx.models.equity_quote import TmxEquityQuoteFetcher
        from openbb_tmx.utils.helpers import download_eod_chains, get_current_options
        from pandas import DataFrame

        results: List = []
        chains = DataFrame()
        if query.date is not None:
            chains = await download_eod_chains(
                symbol=query.symbol, date=query.date, use_cache=query.use_cache
            )
        else:
            chains = await get_current_options(query.symbol, use_cache=query.use_cache)
            underlying_quote = await TmxEquityQuoteFetcher.fetch_data(
                {"symbol": query.symbol}, credentials
            )
            underlying_price = underlying_quote[0].last_price
            if underlying_price and not chains.empty:
                chains["underlying_price"] = underlying_price
                chains["underlying_symbol"] = query.symbol + ":CA"

        if not chains.empty:
            results = chains.to_dict(orient="records")

        return results

    @staticmethod
    def transform_data(
        query: TmxOptionsChainsQueryParams,
        data: List[Dict],
        **kwargs: Any,
    ) -> List[TmxOptionsChainsData]:
        """Transform the data and validate the model."""
        return [TmxOptionsChainsData.model_validate(d) for d in data]
