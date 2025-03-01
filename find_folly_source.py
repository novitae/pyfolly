from pathlib import Path
from datetime import datetime
import os

CUSTOM_FOLLY_VERS = os.getenv("FOLLY_PY_REL_VERS")

folly_sources = [
    file for file in Path().absolute().glob("folly-source-v*")
    if file.is_dir() is True
]

if len(folly_sources):
    if CUSTOM_FOLLY_VERS:
        for source in folly_sources:
            if CUSTOM_FOLLY_VERS and source.name == CUSTOM_FOLLY_VERS:
                print(source)
                break
        else:
            raise FileNotFoundError(f"Found {len(folly_sources)}, but none matches version {CUSTOM_FOLLY_VERS}")
    else:
        if len(folly_sources) == 1:
            print(folly_sources.pop())
        else:
            dates_map: dict[datetime, Path] = {}
            for source in folly_sources:
                dates_map[datetime.strptime(source.name.removeprefix("v"), "%Y.%m.%d.%H")] = source
            print(dates_map[max(dates_map)])
else:
    raise FileNotFoundError('No folly source found.')