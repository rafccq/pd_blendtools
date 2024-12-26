from bpy.props import (
    BoolProperty, EnumProperty, IntProperty
)

from nodes.nodeutils import make_prop, make_id, item_from_value
from .shadernode_base import PD_ShaderNodeBase


COMBINER_ITEMS_A = [
    ('Combined Color', 'Combined Color', 0),
    ('Texture 0 Color', 'Texture 0 Color', 1),
    ('Texture 1 Color', 'Texture 1 Color', 2),
    ('Primitive Color', 'Primitive Color', 3),
    ('Shade Color', 'Shade Color', 4),
    ('Environment Color', 'Environment Color', 5),
    ('1', '1', 6),
    ('Noise', 'Noise', 7),
    ('0', '0', 8),
]

COMBINER_ITEMS_B = [
    ('Combined Color', 'Combined Color', 0),
    ('Texture 0 Color', 'Texture 0 Color', 1),
    ('Texture 1 Color', 'Texture 1 Color', 2),
    ('Primitive Color', 'Primitive Color', 3),
    ('Shade Color', 'Shade Color', 4),
    ('Environment Color', 'Environment Color', 5),
    ('Chroma Key Center', 'Chroma Key Center', 6),
    ('YUV Convert K4', 'YUV Convert K4', 7),
    ('0', '0', 8),
]

COMBINER_ITEMS_C = [
    ('Combined Color', 'Combined Color', 0),
    ('Texture 0 Color', 'Texture 0 Color', 1),
    ('Texture 1 Color', 'Texture 1 Color', 2),
    ('Primitive Color', 'Primitive Color', 3),
    ('Shade Color', 'Shade Color', 4),
    ('Environment Color', 'Environment Color', 5),
    ('Chroma Key Scale', 'Chroma Key Scale', 6),
    ('Combined Color Alpha', 'Combined Color Alpha', 7),
    ('Texture 0 Alpha', 'Texture 0 Alpha', 8),
    ('Texture 1 Alpha', 'Texture 1 Alpha', 9),
    ('Primitive Color Alpha', 'Primitive Color Alpha', 10),
    ('Shade Color Alpha', 'Shade Color Alpha', 11),
    ('Environment Color Alpha', 'Environment Color Alpha', 12),
    ('LOD Fraction', 'LOD Fraction', 13),
    ('Primitive LOD Fraction', 'Primitive LOD Fraction', 14),
    ('YUV Convert K5', 'YUV Convert K5', 15),
    ('0', '0', 16),
]

COMBINER_ITEMS_D = [
    ('Combined Color', 'Combined Color', 0),
    ('Texture 0 Color', 'Texture 0 Color', 1),
    ('Texture 1 Color', 'Texture 1 Color', 2),
    ('Primitive Color', 'Primitive Color', 3),
    ('Shade Color', 'Shade Color', 4),
    ('Environment Color', 'Environment Color', 5),
    ('1', '1', 6),
    ('0', '0', 7),
]

COMBINER_ITEMS_A_ALPHA = [
    ('Combined Color Alpha', 'Combined Color Alpha', 0),
    ('Texture 0 Alpha', 'Texture 0 Alpha', 1),
    ('Texture 1 Alpha', 'Texture 1 Alpha', 2),
    ('Primitive Color Alpha', 'Primitive Color Alpha', 3),
    ('Shade Color Alpha', 'Shade Color Alpha', 4),
    ('Environment Color Alpha', 'Environment Color Alpha', 5),
    ('1', '1', 6),
    ('0', '0', 7),
]

COMBINER_ITEMS_B_ALPHA = [
    ('Combined Color Alpha', 'Combined Color Alpha', 0),
    ('Texture 0 Color Alpha', 'Texture 0 Color Alpha', 1),
    ('Texture 1 Color Alpha', 'Texture 1 Color Alpha', 2),
    ('Primitive Color Alpha', 'Primitive Color Alpha', 3),
    ('Shade Color Alpha', 'Shade Color Alpha', 4),
    ('Environment Color Alpha', 'Environment Color Alpha', 5),
    ('0', '0', 8),
]

COMBINER_ITEMS_C_ALPHA = [
    ('LOD Fraction', 'LOD Fraction', 0),
    ('Texture 0 Alpha', 'Texture 0 Alpha', 1),
    ('Texture 1 Alpha', 'Texture 1 Alpha', 2),
    ('Primitive Color Alpha', 'Primitive Color Alpha', 3),
    ('Shade Color Alpha', 'Shade Color Alpha', 4),
    ('Environment Color Alpha', 'Environment Color Alpha', 5),
    ('Primitive LOD Fraction', 'Primitive LOD Fraction', 6),
    ('0', '0', 7),
]

COMBINER_ITEMS_D_ALPHA = [
    ('Combined Color Alpha', 'Combined Color Alpha', 0),
    ('Texture 0 Alpha', 'Texture 0 Alpha', 1),
    ('Texture 1 Alpha', 'Texture 1 Alpha', 2),
    ('Primitive Color Alpha', 'Primitive Color Alpha', 3),
    ('Shade Color Alpha', 'Shade Color Alpha', 4),
    ('Environment Color Alpha', 'Environment Color Alpha', 5),
    ('1', '1', 6),
    ('0', '0', 7),
]

COMBINER_ITEMS = {
    'combiner_a_color1': COMBINER_ITEMS_A,
    'combiner_b_color1': COMBINER_ITEMS_B,
    'combiner_c_color1': COMBINER_ITEMS_C,
    'combiner_d_color1': COMBINER_ITEMS_D,
    'combiner_a_alpha1': COMBINER_ITEMS_A_ALPHA,
    'combiner_b_alpha1': COMBINER_ITEMS_B_ALPHA,
    'combiner_c_alpha1': COMBINER_ITEMS_C_ALPHA,
    'combiner_d_alpha1': COMBINER_ITEMS_D_ALPHA,

    'combiner_a_color2': COMBINER_ITEMS_A,
    'combiner_b_color2': COMBINER_ITEMS_B,
    'combiner_c_color2': COMBINER_ITEMS_C,
    'combiner_d_color2': COMBINER_ITEMS_D,
    'combiner_a_alpha2': COMBINER_ITEMS_A_ALPHA,
    'combiner_b_alpha2': COMBINER_ITEMS_B_ALPHA,
    'combiner_c_alpha2': COMBINER_ITEMS_C_ALPHA,
    'combiner_d_alpha2': COMBINER_ITEMS_D_ALPHA,

}

COMBINER_PARAMWIDTHS = {
    'combiner_d_alpha2': 3,
    'combiner_b_alpha2': 3,
    'combiner_d_color2': 3,
    'combiner_d_alpha1': 3,
    'combiner_b_alpha1': 3,
    'combiner_d_color1': 3,
    'combiner_c_alpha2': 3,
    'combiner_a_alpha2': 3,
    'combiner_b_color2': 4,
    'combiner_b_color1': 4,
    'combiner_c_color2': 5,
    'combiner_a_color2': 4,
    'combiner_c_alpha1': 3,
    'combiner_a_alpha1': 3,
    'combiner_c_color1': 5,
    'combiner_a_color1': 4,
}

class PD_ShaderNodeSetCombine(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.setcombine'
    bl_label = "SetCombine"
    bl_icon = 'IMAGE_ZDEPTH'

    min_width = 210

    def on_update(self, context):
        ofs, cmd = 0, 0
        for name, w in COMBINER_PARAMWIDTHS.items():
            propval = self.enum_value(name)

            mask = (1 << w) - 1
            cmd |= (propval & mask) << ofs
            ofs += w

        self.cmd = f'FC{cmd:014X}'
        # print(f'cmd = {self.cmd}')

    combiner_a_color1: make_prop('combiner_a_color1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_A[-1][0]), on_update)
    combiner_b_color1: make_prop('combiner_b_color1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_B[-1][0]), on_update)
    combiner_c_color1: make_prop('combiner_c_color1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_C[-1][0]), on_update)
    combiner_d_color1: make_prop('combiner_d_color1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_D[-3][0]), on_update)
    combiner_a_alpha1: make_prop('combiner_a_alpha1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_A_ALPHA[-1][0]), on_update)
    combiner_b_alpha1: make_prop('combiner_b_alpha1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_B_ALPHA[-1][0]), on_update)
    combiner_c_alpha1: make_prop('combiner_c_alpha1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_C_ALPHA[-1][0]), on_update)
    combiner_d_alpha1: make_prop('combiner_d_alpha1', COMBINER_ITEMS, make_id(COMBINER_ITEMS_D_ALPHA[-3][0]), on_update)

    combiner_a_color2: make_prop('combiner_a_color2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_A[-1][0]), on_update)
    combiner_b_color2: make_prop('combiner_b_color2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_B[-1][0]), on_update)
    combiner_c_color2: make_prop('combiner_c_color2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_C[-1][0]), on_update)
    combiner_d_color2: make_prop('combiner_d_color2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_D[-3][0]), on_update)
    combiner_a_alpha2: make_prop('combiner_a_alpha2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_A_ALPHA[-1][0]), on_update)
    combiner_b_alpha2: make_prop('combiner_b_alpha2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_B_ALPHA[-1][0]), on_update)
    combiner_c_alpha2: make_prop('combiner_c_alpha2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_C_ALPHA[-1][0]), on_update)
    combiner_d_alpha2: make_prop('combiner_d_alpha2', COMBINER_ITEMS, make_id(COMBINER_ITEMS_D_ALPHA[-3][0]), on_update)

    num_cycles: IntProperty(name='num_cycles', default=1)

    def init(self, _context):
        self.pd_init()

    def post_init(self):
        self.init_num_cycles()

    def update_ui(self):
        cmd = int(f'0x{self.cmd}', 16)

        ofs = 0
        for name, w in COMBINER_PARAMWIDTHS.items():
            mask = (1 << w) - 1
            value = cmd & mask
            cmd >>= w

            items = COMBINER_ITEMS[name]
            ofs += w
            propval = item_from_value(items, value, -1)
            setattr(self, name, make_id(propval))


    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)
        box = layout.box()

        self.draw_combiner(box, True, 1)

        if self.num_cycles == 2:
            box.separator(type='LINE')
            self.draw_combiner(box, True, 2)

    def draw_buttons_ext(self, _context, layout):
        self.draw_combiner(layout, False, 1)

        if self.num_cycles == 2:
            layout.separator(type='LINE')
            self.draw_combiner(layout, False, 2)

    def draw_combiner(self, layout, col_layout, cycle):
        if self.num_cycles == 2:
            layout.label(text=f'Cycle {cycle}')

        if col_layout:
            container = layout.column()
        else:
            box = layout.box()
            box.label(text='Color = (A - B) * C + D')
            container = box.row().split(factor=0.45)

        self.draw_combiner_props(container, col_layout, False, cycle)
        self.draw_combiner_props(container, col_layout, True, cycle)

    def draw_combiner_props(self, container, col_layout, alpha, cycle=1):
        col = None

        for name in ['a', 'b', 'c', 'd']:
            label = name.upper() + (' Alpha' if alpha else '')
            a = f'_alpha{cycle}' if alpha else f'_color{cycle}'

            if col_layout:
                container.prop(self, f'combiner_{name}{a}', text=label)
            else:
                col = col if col else container.column()
                row = col.row().split(factor=0.25 if alpha else 0.1)
                row.label(text=f'{label}:')
                row.prop(self, f'combiner_{name}{a}', text='')

    def set_num_cycles(self, num_cycles):
        self.num_cycles = num_cycles
