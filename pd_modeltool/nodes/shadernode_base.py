import bpy

from bpy.props import (
    BoolProperty, EnumProperty, StringProperty
)

DESC_BASE_SHOWPROPS = 'Show properties'

class PD_ShaderNodeBase(bpy.types.ShaderNodeCustomGroup):
    bl_idname = 'pd.nodes.pdbase'
    bl_label = ""

    min_width = 0

    def on_show_props(self, context):
        pass

    cmd: bpy.props.StringProperty()
    show_props: BoolProperty(name='show_props', default=False, description=DESC_BASE_SHOWPROPS, update=on_show_props)

    def pd_init(self, add_prev=True, color=None):
        self.node_tree = bpy.data.node_groups.new(f'.{self.bl_idname}nodetree', 'ShaderNodeTree')

        if add_prev:
            self.add_socket('prev', 'INPUT', 'NodeSocketInt')

        self.add_socket('next', 'OUTPUT', 'NodeSocketInt')

        self.use_custom_color = True
        # self.color = (0.73, 0.53, 0.22)
        self.color = color if color else (.352, .352, .352)

    def add_socket(self, name, inout, socket_type):
        if bpy.app.version >= (4, 0, 0):
            self.node_tree.interface.new_socket(name, in_out=inout, socket_type=socket_type)
        else:
            self.node_tree.outputs.new(socket_type, name)

    def set_cmd(self, cmd):
        self.cmd = cmd
        self.update_ui()

    # updates the UI elements based on the command
    def update_ui(self): pass

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)

        if self.cmd:
            cmd = self.cmd
            txt = f'{cmd[:8]} {cmd[8:]}'
            col.label(text=txt)
            col.enabled = False

    def enum_value(self, enum_name):
        if enum_name in self: return self[enum_name]

        prop = self.bl_rna.properties[enum_name]
        items = prop.enum_items
        default = items.get(prop.default)
        return items.get(enum_name, default).value

    # used by othermodeH and setcombine
    def set_num_cycles(self, num_cycles): pass

    # goes up the chain searching for a setothermodeH node, then sets num_cycles if found
    def init_num_cycles(self):
        self['num_cycles'] = 1
        node = self
        while node:
            if len(node.inputs) == 0: break

            node = node.inputs[0].links[0].from_node
            if node.bl_idname == 'pd.nodes.setothermodeH': # TMP TODO add const
                self['num_cycles'] = 2 if node['g_mdsft_cycletype'] == 1 else 1
                break

    def post_init(self): pass

    def get_cmd(self): return self.cmd
