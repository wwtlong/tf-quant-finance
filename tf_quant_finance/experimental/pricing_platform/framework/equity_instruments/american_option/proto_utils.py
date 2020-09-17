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
"""Utilities for proto processing."""
import hashlib
import json

from typing import Any, List, Dict, Tuple

from tf_quant_finance.experimental.pricing_platform.framework.core import business_days
from tf_quant_finance.experimental.pricing_platform.framework.core import currencies
from tf_quant_finance.experimental.pricing_platform.framework.core import types
from tf_quant_finance.experimental.pricing_platform.framework.rate_instruments import utils as instrument_utils
from tf_quant_finance.experimental.pricing_platform.instrument_protos import american_equity_option_pb2 as american_option_pb2


# TODO(b/168411151): extract the non-cryptographic hasher to the common
# utilities
def _hasher(obj):
  h = hashlib.md5(json.dumps(obj).encode())
  return h.hexdigest()


def _get_hash(
    american_option_proto: american_option_pb2.AmericanEquityOption
    ) -> Tuple[int, types.CurrencyProtoType]:
  """Computes hash key for the batching strategy."""
  currency = currencies.from_proto_value(american_option_proto.currency)
  bank_holidays = american_option_proto.bank_holidays
  business_day_convention = american_option_proto.business_day_convention
  h = _hasher(tuple([bank_holidays] + [business_day_convention]))
  return h, currency


def group_protos(
    proto_list: List[american_option_pb2.AmericanEquityOption],
    american_option_config: "AmericanOptionConfig" = None
    ) -> Dict[str, List["AmericanOption"]]:
  """Creates a dictionary of grouped protos."""
  del american_option_config  # not used for now
  grouped_options = {}
  for american_option in proto_list:
    h, _ = _get_hash(american_option)
    if h in grouped_options:
      grouped_options[h].append(american_option)
    else:
      grouped_options[h] = [american_option]
  return grouped_options


def from_protos(
    proto_list: List[american_option_pb2.AmericanEquityOption],
    american_option_config: "AmericanOptionConfig" = None
    ) -> Dict[str, Any]:
  """Creates a dictionary of preprocessed swap data."""
  prepare_fras = {}
  for am_option_proto in proto_list:
    short_position = am_option_proto.short_position
    h, currency = _get_hash(am_option_proto)
    expiry_date = am_option_proto.expiry_date
    expiry_date = [expiry_date.year,
                   expiry_date.month,
                   expiry_date.day]
    equity = am_option_proto.equity
    contract_amount = instrument_utils.decimal_to_double(
        am_option_proto.contract_amount)
    business_day_convention = business_days.convention_from_proto_value(
        am_option_proto.business_day_convention)
    strike = instrument_utils.decimal_to_double(am_option_proto.strike)
    calendar = business_days.holiday_from_proto_value(
        am_option_proto.bank_holidays)
    settlement_days = am_option_proto.settlement_days
    is_call_option = am_option_proto.is_call_option
    name = am_option_proto.metadata.id
    instrument_type = am_option_proto.metadata.instrument_type
    if h not in prepare_fras:
      prepare_fras[h] = {"short_position": [short_position],
                         "currency": currency,
                         "expiry_date": [expiry_date],
                         "equity": [equity],
                         "contract_amount": [contract_amount],
                         "business_day_convention": business_day_convention,
                         "calendar": calendar,
                         "strike": [strike],
                         "is_call_option": [is_call_option],
                         "settlement_days": [settlement_days],
                         "american_option_config": american_option_config,
                         "batch_names": [[name, instrument_type]]}
    else:
      prepare_fras[h]["short_position"].append(short_position)
      prepare_fras[h]["expiry_date"].append(expiry_date)
      prepare_fras[h]["equity"].append(equity)
      prepare_fras[h]["contract_amount"].append(contract_amount)
      prepare_fras[h]["strike"].append(strike)
      prepare_fras[h]["is_call_option"].append(is_call_option)
      prepare_fras[h]["settlement_days"].append(settlement_days)
      prepare_fras[h]["batch_names"].append([name, instrument_type])
  return prepare_fras

