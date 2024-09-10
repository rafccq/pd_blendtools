from bpy.props import (
    EnumProperty
)

def enum_name(prefix, name):
    name = name.replace(' ', '').lower()
    return f'{prefix}_{name}'

def make_items(prefix, items):
    return [(enum_name(prefix, name), name, desc, val) for (name, desc, val) in items]

def make_prop(name, config, default, callback_update):
    items = config[name]
    return EnumProperty(
        items=make_items(name, items),
        name=name,
        default=f'{name}_{default}',
        update=callback_update
        # set=callback_update
    )

