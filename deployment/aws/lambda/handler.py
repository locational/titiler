"""AWS Lambda handler."""

from fastapi import HTTPException, Query
from rio_tiler.colormap import cmap, parse_color
import matplotlib
import numpy
from typing import Dict, Optional
from enum import Enum
import json
from fastapi import FastAPI
from titiler.core.factory import TilerFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
import logging

from mangum import Mangum

# from titiler.application.main import app

"""dependencies.

app/dependencies.py

"""


ColorMapName = Enum(  # type: ignore
    "ColorMapName", [(a, a) for a in sorted(cmap.list())]
)


class ColorMapType(str, Enum):
    """Colormap types."""

    explicit = "explicit"
    linear = "linear"


def ColorMapParams(
    colormap_name: ColorMapName = Query(None, description="Colormap name"),
    colormap: str = Query(None, description="JSON encoded custom Colormap"),
    colormap_type: ColorMapType = Query(ColorMapType.explicit, description="User input colormap type."),
) -> Optional[Dict]:
    """Colormap Dependency."""
    if colormap_name:
        return cmap.get(colormap_name.value)

    if colormap:
        try:
            cm = json.loads(
                colormap,
                object_hook=lambda x: {int(k): parse_color(v) for k, v in x.items()},
            )
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Could not parse the colormap value."
            )

        if colormap_type == ColorMapType.linear:
            # input colormap has to start from 0 to 255 ?
            cm = matplotlib.colors.LinearSegmentedColormap.from_list(
                'custom',
                [
                    (k / 255, matplotlib.colors.to_hex([v / 255 for v in rgba]))
                    for (k, rgba) in cm.items()
                ],
                256,
            )
            x = numpy.linspace(0, 1, 256)
            cmap_vals = cm(x)[:, :]
            cmap_uint8 = (cmap_vals * 255).astype('uint8')
            cm = {idx: value.tolist() for idx, value in enumerate(cmap_uint8)}

        return cm

    return None


"""app.

app/main.py

"""


app = FastAPI(title="My simple app with custom TMS")

cog = TilerFactory(colormap_dependency=ColorMapParams)
app.include_router(cog.router, tags=["Cloud Optimized GeoTIFF"])
add_exception_handlers(app, DEFAULT_STATUS_CODES)


logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

handler = Mangum(app, lifespan="auto", log_level="error")
