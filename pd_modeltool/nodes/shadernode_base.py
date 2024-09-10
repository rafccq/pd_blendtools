import bpy

from bpy.props import (
    BoolProperty, EnumProperty, StringProperty
)

DESC_BASE_SHOWPROPS = 'Show properties'

class PD_ShaderNodeBase(bpy.types.ShaderNodeCustomGroup):
    bl_idname = 'pd.nodes.pdbase'
    bl_label = ""

    def on_show_props(self, context):
        pass

    cmd: bpy.props.StringProperty()
    show_props: BoolProperty(update=on_show_props, name='show_props', default=False, description=DESC_BASE_SHOWPROPS)

    def pd_init(self, add_prev=True):
        self.node_tree = bpy.data.node_groups.new(f'.{self.bl_idname}nodetree', 'ShaderNodeTree')

        if add_prev:
            self.add_socket('prev', 'INPUT', 'NodeSocketInt')

        self.add_socket('next', 'OUTPUT', 'NodeSocketInt')

        self.use_custom_color = True
        # self.color = (0.73, 0.53, 0.22)
        self.color = (.352, .352, .352)
        # self.cmd = 0

    def add_socket(self, name, inout, socket_type):
        if bpy.app.version >= (4, 0, 0):
            self.node_tree.interface.new_socket(name, in_out=inout, socket_type=socket_type)
        else:
            self.node_tree.outputs.new(socket_type, name)

    def set_cmd(self, cmd):
        self.cmd = cmd
        self.update_ui()

    def update_ui(self): pass

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)

        if self.cmd:
            col.label(text=self.cmd)
            col.enabled = False

