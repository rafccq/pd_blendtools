from bpy.props import (
    EnumProperty
)

def make_id(name):
    for c in [' ', '(', ')', '[', ']', '{', '}', '.', '?', '/']:
        name = name.replace(c, '')
    return name.lower()

def make_prop(name, config, default, callback_update=None) -> EnumProperty:
    items = config[name]
    return EnumProperty(
        items=[(make_id(name), name, desc, '', val) for (name, desc, val) in items],
        name=name,
        default=f'{default}',
        update=callback_update
    )

def item_from_value(items, value, default_idx=0):
   default = items[default_idx]
   return next(filter(lambda e: e[2] == value, items), default)[0]
