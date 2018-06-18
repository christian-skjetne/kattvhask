import logging
import sys

import coloredlogs


def init(loglevel=logging.DEBUG):
    fmt = '%(asctime)23s%(levelname)9s %(name)30s: %(message)s'

    field_style_override = coloredlogs.DEFAULT_FIELD_STYLES
    field_style_override['levelname'] = {"color": "magenta", "bold": True}

    level_style_override = coloredlogs.DEFAULT_LEVEL_STYLES
    level_style_override['debug'] = {"color": "cyan"}

    coloredlogs.install(level=loglevel,
                        fmt=fmt,
                        level_styles=level_style_override,
                        field_styles=field_style_override,
                        stream=sys.stdout)
