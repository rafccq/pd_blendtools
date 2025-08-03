from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty

from utils import pd_utils as pdu

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
    ('0', '0', 15),
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
    ('Primitive Color Alpha', 'Primitive Color Alpha', 0xa),
    ('Shade Color Alpha', 'Shade Color Alpha', 0xb),
    ('Environment Color Alpha', 'Environment Color Alpha', 0xc),
    ('LOD Fraction', 'LOD Fraction', 0xd),
    ('Primitive LOD Fraction', 'Primitive LOD Fraction', 0xe),
    ('YUV Convert K5', 'YUV Convert K5', 0xf),
    ('0', '0', 0x1f),
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
    ('1', '1', 6),
    ('0', '0', 7),
    ('Noise', 'Noise', 15),
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
    'combiner1_a_color': COMBINER_ITEMS_A,
    'combiner1_b_color': COMBINER_ITEMS_B,
    'combiner1_c_color': COMBINER_ITEMS_C,
    'combiner1_d_color': COMBINER_ITEMS_D,
    'combiner1_a_alpha': COMBINER_ITEMS_A_ALPHA,
    'combiner1_b_alpha': COMBINER_ITEMS_B_ALPHA,
    'combiner1_c_alpha': COMBINER_ITEMS_C_ALPHA,
    'combiner1_d_alpha': COMBINER_ITEMS_D_ALPHA,

    'combiner2_a_color': COMBINER_ITEMS_A,
    'combiner2_b_color': COMBINER_ITEMS_B,
    'combiner2_c_color': COMBINER_ITEMS_C,
    'combiner2_d_color': COMBINER_ITEMS_D,
    'combiner2_a_alpha': COMBINER_ITEMS_A_ALPHA,
    'combiner2_b_alpha': COMBINER_ITEMS_B_ALPHA,
    'combiner2_c_alpha': COMBINER_ITEMS_C_ALPHA,
    'combiner2_d_alpha': COMBINER_ITEMS_D_ALPHA,

}

COMBINER_PARAMWIDTHS = {
    'combiner2_d_alpha': 3,
    'combiner2_b_alpha': 3,
    'combiner2_d_color': 3,
    'combiner1_d_alpha': 3,
    'combiner1_b_alpha': 3,
    'combiner1_d_color': 3,
    'combiner2_c_alpha': 3,
    'combiner2_a_alpha': 3,
    'combiner2_b_color': 4,
    'combiner1_b_color': 4,
    'combiner2_c_color': 5,
    'combiner2_a_color': 4,
    'combiner1_c_alpha': 3,
    'combiner1_a_alpha': 3,
    'combiner1_c_color': 5,
    'combiner1_a_color': 4,
}

class MatSetCombine(PropertyGroup):
    combiner1_a_color: pdu.make_prop('combiner1_a_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_A[-1][0]))
    combiner1_b_color: pdu.make_prop('combiner1_b_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_B[-1][0]))
    combiner1_c_color: pdu.make_prop('combiner1_c_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_C[-1][0]))
    combiner1_d_color: pdu.make_prop('combiner1_d_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_D[-3][0]))
    combiner1_a_alpha: pdu.make_prop('combiner1_a_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_A_ALPHA[-1][0]))
    combiner1_b_alpha: pdu.make_prop('combiner1_b_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_B_ALPHA[-1][0]))
    combiner1_c_alpha: pdu.make_prop('combiner1_c_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_C_ALPHA[-1][0]))
    combiner1_d_alpha: pdu.make_prop('combiner1_d_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_D_ALPHA[-3][0]))

    combiner2_a_color: pdu.make_prop('combiner2_a_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_A[-1][0]))
    combiner2_b_color: pdu.make_prop('combiner2_b_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_B[-1][0]))
    combiner2_c_color: pdu.make_prop('combiner2_c_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_C[-1][0]))
    combiner2_d_color: pdu.make_prop('combiner2_d_color', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_D[-3][0]))
    combiner2_a_alpha: pdu.make_prop('combiner2_a_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_A_ALPHA[-1][0]))
    combiner2_b_alpha: pdu.make_prop('combiner2_b_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_B_ALPHA[-1][0]))
    combiner2_c_alpha: pdu.make_prop('combiner2_c_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_C_ALPHA[-1][0]))
    combiner2_d_alpha: pdu.make_prop('combiner2_d_alpha', COMBINER_ITEMS, pdu.make_id(COMBINER_ITEMS_D_ALPHA[-3][0]))

    num_cycles: IntProperty(name='num_cycles', default=1)

    set_combiner: BoolProperty(name='set_combiner', default=False)

def mat_setcombine_set(combiner, cmd):
    combiner.set_combiner = cmd != 0

    ofs = 0
    for name, w in COMBINER_PARAMWIDTHS.items():
        mask = (1 << w) - 1
        value = cmd & mask
        cmd >>= w

        items = COMBINER_ITEMS[name]
        ofs += w
        propval = pdu.item_from_value(items, value, -1)
        setattr(combiner, name, pdu.make_id(propval))

def mat_setcombine_draw(combiner, layout, context):
    box = layout.box()

    draw_combiner(combiner, box, 1)

    if combiner.num_cycles == 2:
        pdu.ui_separator(box, type='LINE')
        draw_combiner(combiner, box, 2)

def draw_combiner(combiner, layout, cycle):
    if combiner.num_cycles == 2:
        layout.label(text=f'Cycle {cycle}')

    box = layout.box()
    box.prop(combiner, 'set_combiner', text='Color Combiner (Color = (A - B) * C + D)')
    container = box.row().split(factor=0.45)
    container.enabled = combiner.set_combiner

    draw_combiner_props(combiner, container, 'color', cycle)
    draw_combiner_props(combiner, container, 'alpha', cycle)

def draw_combiner_props(combiner, container, channel, cycle=1):
    col = None
    alpha = channel == 'alpha'

    for name in ['a', 'b', 'c', 'd']:
        label = name.upper() + (' Alpha' if alpha else '')
        a = f'_alpha' if alpha else f'_color'

        col = col if col else container.column()
        row = col.row().split(factor=0.25 if alpha else 0.1)
        row.label(text=f'{label}:')
        row.prop(combiner, f'combiner{cycle}_{name}{a}', text='')

def combiner_command(combparams):
    if not combparams: return 0

    ofs, cmd = 0, 0
    for name, w in COMBINER_PARAMWIDTHS.items():
        propval = combparams[name]
        mask = (1 << w) - 1
        cmd |= (propval & mask) << ofs
        ofs += w

    cmd = (0xfc << 8*7) | cmd
    return cmd

