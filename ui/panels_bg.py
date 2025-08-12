import bpy
from bpy.types import Panel

from utils import pd_utils as pdu
import pd_blendprops as pdprops


class PDTOOLS_PT_Room(Panel):
    bl_label = 'Room'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return pdu.pdtype(obj) in [pdprops.PD_OBJTYPE_ROOM, pdprops.PD_OBJTYPE_ROOMBLOCK]

    def draw(self, context):
        bl_obj = context.object
        scn = context.scene
        layout = self.layout

        isroom = pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOM

        pd_room = bl_obj.pd_room

        box = layout.box()
        name = 'Room' if isroom else 'Block'
        num = pd_room.roomnum if isroom else pd_room.blocknum

        if isroom:
            box.label(text=f'{name} {num:02X}', icon='OBJECT_DATA')
            row = box.row()
            op = row.operator('pdtools.op_room_create_block', text=f'Create Block')
            op.blocklinking = 'child'
        else:
            row = box.row()
            row.alignment = 'LEFT'
            row.emboss = 'NONE'
            row.label(text='', icon='OBJECT_DATA')
            row.operator('pdtools.op_room_select_room', text=f'Room {pd_room.roomnum:02X}')
            row.label(text='', icon='RIGHTARROW')
            row.label(text=f'{name} {num}')

            box.label(text=f'Type: {pd_room.blocktype}', icon='LOCKED')
            row = box.row()
            row.prop(pd_room, 'layer', text='Layer')
            row.enabled = False
            box.prop(pd_room, 'parent', text='Parent')

            row = box.row()
            row.prop(pd_room, 'next', text='Next')
            row.enabled = False

            op = box.operator('pdtools.op_room_create_block', text=f'Create Sibling Block')
            op.blocklinking = 'sibling'
            op.layer = pd_room.layer

            room = pd_room.room.pd_room
            can_delete = room.first_opa.pd_room != pd_room
            if pd_room.blocktype == pdprops.BLOCKTYPE_DL:
                row = box.row()
                op = row.operator('pdtools.op_room_block_delete', text=f'Delete Block')
                row.enabled = can_delete

            if pd_room.blocktype == pdprops.BLOCKTYPE_BSP:
                op = box.operator('pdtools.op_room_create_block', text=f'Create Child Block')
                op.blocklinking = 'child'
                op.layer = pd_room.layer

                row = box.row()
                row.operator('pdtools.op_room_block_delete', text=f'Delete Block')
                row.enabled = can_delete

                pdu.ui_separator(box, type='LINE')
                box.label(text='BSP Position:')
                box.prop(pd_room, 'bsp_pos', text='')

                box.label(text='BSP Normal:')
                box.prop(pd_room, 'bsp_normal', text='')
                row = box.row()
                for idx, t in enumerate(['X', 'Y', 'Z']):
                    row.prop(pd_room, 'bsp_normal', index = idx, text=t)
                row = box.row()
                row.prop(scn, 'pd_bspwidth', text='Width (View Only)')


class PDTOOLS_PT_Portal(Panel):
    bl_label = 'PD Portal'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return pdu.pdtype(obj) == pdprops.PD_OBJTYPE_PORTAL

    def draw(self, context):
        obj = context.object
        layout = self.layout

        props_portal = obj.pd_portal

        box = layout.box()
        box.label(text=f'{obj.pd_obj.name}', icon='OBJECT_DATA')
        box.prop(props_portal, 'room1', text='room 1')
        box.prop(props_portal, 'room2', text='room 2')
        box.operator("pdtools.portal_find_rooms", text = "Auto Find")


class PDTOOLS_PT_RoomTools(Panel):
    bl_label = 'Room Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        scn = context.scene
        layout = self.layout

        col = layout.column()
        container = col.split(factor=.5)
        container.label(text=f'Go To Room')
        container.prop(scn, 'pd_room_goto', text='')

        sel = context.selected_objects
        nsel = len(sel)
        isroom = lambda o: pdu.pdtype(o) == pdprops.PD_OBJTYPE_ROOMBLOCK

        bl_obj = context.active_object
        pdtype = pdu.pdtype(bl_obj)

        row = col.row()
        row = row.split(factor=0.5)
        col = row.column()
        col.operator('pdtools.room_split_by_portal', text='Split By Portal')
        portalselected = context.scene.pd_portal is not None
        col.enabled = isroom(bl_obj) and portalselected
        row.prop(scn, 'pd_portal', text='')

        row = layout.column()
        row.operator('pdtools.op_room_select_all_blocks', text='Select All Blocks In Room')
        row.enabled = nsel == 1 and pdtype in [pdprops.PD_OBJTYPE_ROOM, pdprops.PD_OBJTYPE_ROOMBLOCK]

        row = layout.column()
        row.operator('pdtools.op_room_create', text='Create Room')
        row.enabled = pdu.get_mode(context) in ['', 'OBJECT']


classes = [
    PDTOOLS_PT_Portal,
    PDTOOLS_PT_Room,
    PDTOOLS_PT_RoomTools,
]

register, unregister = bpy.utils.register_classes_factory(classes)
