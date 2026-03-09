import datetime
from zoneinfo import ZoneInfo

CN_TZ = ZoneInfo("Asia/Shanghai")
US_TZ = ZoneInfo("America/New_York")
HK_TZ = ZoneInfo("Asia/Hong_Kong")

symbol_suffix_region_map = {
    "SH": "CN",
    "SZ": "CN",
    "BJ": "CN",
    "US": "US",
    "HK": "HK",
    "SHF": "CN",
    "DCE": "CN",
    "ZCE": "CN",
    "CFX": "CN",
    "INE": "CN",
    "GFE": "CN",
}

region_timezone_map = {
    "CN": CN_TZ,
    "US": US_TZ,
    "HK": HK_TZ,
}


def get_instrument_region(symbol: str):
    return symbol_suffix_region_map.get(
        symbol.rsplit(".", 1)[-1],
    )


def get_region_timezone(region: str):
    return region_timezone_map.get(region)


def instrument_timestamp_to_datetime(symbol: str, timestamp: int, unit="ms"):
    tz = get_region_timezone(get_instrument_region(symbol))
    if tz is None:
        return None

    dt = (
        datetime.datetime.fromtimestamp(timestamp / 1000, tz)
        if unit == "ms"
        else datetime.datetime.fromtimestamp(timestamp, tz)
    )
    return dt


def instrument_timestamp_to_trade_date(symbol: str, timestamp: int, unit="ms"):
    dt = instrument_timestamp_to_datetime(symbol, timestamp, unit)
    return dt.strftime("%Y-%m-%d")


def instrument_timestamp_to_trade_time(symbol: str, timestamp: int, unit="ms"):
    dt = instrument_timestamp_to_datetime(symbol, timestamp, unit)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
