# Lint as: python3
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for equity instruments."""

from typing import List, Tuple

import tensorflow.compat.v2 as tf

from tf_quant_finance import datetime as dateslib
from tf_quant_finance.experimental.pricing_platform.framework.core import processed_market_data as pmd
from tf_quant_finance.experimental.pricing_platform.framework.market_data import volatility_surface
from tf_quant_finance.experimental.pricing_platform.framework.rate_instruments import cashflow_streams


def process_equities(
    equities: List[str]
    ) -> Tuple[
        List[str], List[int]]:
  """Extracts unique volatility surfaces and computes an integer mask.

  #### Example
  ```python
  process_equities(["GOOG", "MSFT", "GOOG"])
  # Returns
  (['MSFT', 'GOOG'], [1, 0, 1])
  ```

  Args:
    equities: A list of equity names.

  Returns:
    A list of unique equities in `equities` and a list of integers which is
    the mask of `equities`.
  """
  equity_list = cashflow_streams.to_list(equities)
  equity_hash = [hash(equity_type) for equity_type in equity_list]
  hash_equities = {
      hash(equity_type): equity_type for equity_type in equity_list}
  mask, mask_map, num_unique_equities = cashflow_streams.create_mask(
      equity_hash)
  equity_types = [
      hash_equities[mask_map[i]]
      for i in range(num_unique_equities)]
  return equity_types, mask


def get_vol_surface(
    equity_types: List[str],
    market: pmd.ProcessedMarketData,
    mask: List[int]) -> volatility_surface.VolatilitySurface:
  """Builds a batched discount curve.

  Given a list of discount curve an integer mask, creates a discount curve
  object to compute discount factors against the list of discount curves.

  #### Example
  ```none
  curve_types = ["GOOG", "MSFT"]
  # A mask to price a batch of 7 instruments with the corresponding discount
  # curves ["GOOG", "MSFT", "MSFT", "MSFT" "GOOG", "GOOG"].
  mask = [0, 1, 1, 1, 0, 0]
  market = MarketDataDict(...)
  get_vol_surface(curve_types, market, mask)
  # Returns a VolatilitySurface object that can compute a volatilities for a
  # batch of 6 expiry dates and strikes.
  ```

  Args:
    equity_types: A list of equity types.
    market: An instance of the processed market data.
    mask: An integer mask.

  Returns:
    An instance of `VolatilitySurface`.
  """
  vols = market.volatility_surface(equity_types)
  expiries = vols.node_expiries().ordinal()
  strikes = vols.node_strikes()
  volatilities = vols.node_volatilities()
  prepare_strikes = tf.gather(strikes, mask)
  prepare_vols = tf.gather(volatilities, mask)
  prepare_expiries = dateslib.dates_from_ordinals(
      tf.gather(expiries, mask))
  # All curves are assumed to have the same interpolation method
  # TODO(b/168411153): Extend to the case with multiple curve configs.
  vol_surface = volatility_surface.VolatilitySurface(
      valuation_date=market.date,
      expiries=prepare_expiries,
      strikes=prepare_strikes,
      volatilities=prepare_vols,
      daycount_convention=vols.daycount_convention)
  return vol_surface
