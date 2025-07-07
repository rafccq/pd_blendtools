import os
import math

import bpy
from bpy.types import Operator
import bmesh
from bpy.props import IntProperty, StringProperty, BoolProperty, EnumProperty
from bpy_extras import view3d_utils
from mathutils import Vector
import aud

from pd_data.decl_setupfile import OBJTYPE_LINKLIFTDOOR
from pd_data.pd_padsfile import *
from pd_data import romdata as rom, pd_padsfile as pdpads
from pd_import import setup_import as stpi
import pd_blendprops as pdprops
from utils import pd_utils as pdu

class PDTOOLS_OT_SetupLiftCreateStop(Operator):
    bl_idname = "pdtools.op_setup_lift_create_stop"
    bl_label = "PD: Create Stop"
    bl_description = "Create a lift stop"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name='index', default=0, options={'LIBRARY_EDITABLE'})

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift

        name = f'{bl_obj.name} stop{self.index+1}'
        bl_stop = pdu.new_empty_obj(name, bl_obj, dsize=50, dtype='CIRCLE')
        bl_stop.pd_obj.type = pdprops.PD_PROP_LIFT_STOP
        bl_stop.scale = Vector([1/sc for sc in bl_obj.scale])

        if self.index == 0:
            pd_lift.stop1 = bl_stop
        elif self.index == 1:
            pd_lift.stop2 = bl_stop
        elif self.index == 2:
            pd_lift.stop3 = bl_stop
        elif self.index == 3:
            pd_lift.stop4 = bl_stop

        return {'FINISHED'}


class PDTOOLS_OT_SetupWaypointAddNeighbour(Operator):
    bl_idname = "pdtools.op_setup_waypoint_addneighbour"
    bl_label = 'Add Neighbour'
    bl_description = 'Click on waypoints to add a neighbor. Right click or esc to exit'

    @staticmethod
    def raycast(context, event):
        scn = context.scene
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y

        # get the ray from the viewport and mouse
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

        ray_target = ray_origin + view_vector

        def obj_ray_cast(obj, matrix):
            # get the ray relative to the object
            matrix_inv = matrix.inverted()
            ray_origin_obj = matrix_inv @ ray_origin
            ray_target_obj = matrix_inv @ ray_target
            ray_direction_obj = ray_target_obj - ray_origin_obj

            # cast the ray
            success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

            if success:
                return location, normal, face_index
            else:
                return None, None, None

        # cast rays and find the closest object
        best_length_squared = -1.0
        picked_obj = None

        coll = bpy.data.collections['Waypoints']
        for obj in coll.objects:
            if obj.pd_obj.type != pdprops.PD_OBJTYPE_WAYPOINT: continue

            M = obj.matrix_world
            hit, normal, face_index = obj_ray_cast(obj, M)

            if hit is None: continue

            hit_world = M @ hit
            scn.cursor.location = hit_world
            length_squared = (hit_world - ray_origin).length_squared
            if picked_obj is None or length_squared < best_length_squared:
                best_length_squared = length_squared
                picked_obj = obj

        if picked_obj is not None:
            sel_obj = context.active_object
            # clicked on the waypoint already selected: skip
            if sel_obj == picked_obj:
                return

            stu.wp_addneighbour(sel_obj, picked_obj)
            stu.wp_addneighbour(picked_obj, sel_obj)

    def modal(self, context, event):
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.raycast(context, event)
            return {'RUNNING_MODAL'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}


class PDTOOLS_OT_SetupWaypointRemoveNeighbour(Operator):
    bl_idname = "pdtools.op_setup_waypoint_removeneighbour"
    bl_label = "PD: Remove Neighbour"
    bl_description = "Remove the selected neighbour (will remove from both waypoints)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_waypoint = bl_obj.pd_waypoint

        pd_neighbours_coll = pd_waypoint.neighbours_coll
        index = pd_waypoint.active_neighbour_idx
        pd_neighbour = pd_neighbours_coll[index]
        padnum = pd_neighbour.padnum
        pd_neighbours_coll.remove(index)

        bl_neighbour = context.scene['waypoints'][str(padnum)]
        pd_neighbour = bl_neighbour.pd_waypoint
        pdu.waypoint_remove_neighbour(pd_neighbour, pd_waypoint.padnum)

        pdu.redraw_ui()
        return {'FINISHED'}


class PDTOOLS_OT_SetupWaypointCreate(Operator):
    bl_idname = "pdtools.op_setup_waypoint_create"
    bl_label = "Create Waypoint"
    bl_description = "Create a new waypoint"
    bl_options = {'REGISTER', 'UNDO'}

    group_enum: EnumProperty(name="group_enum", description="Waypoint Group", items=pdprops.get_groupitems)

    def invoke(self, context, _event):
        obj = context.active_object
        if pdu.pdtype(obj) == pdprops.PD_OBJTYPE_WAYGROUP:
            self.group_enum = obj.name

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=150)

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, 'group_enum', text='')

    def execute(self, context):
        groupname = self.group_enum
        if groupname == pdprops.NEWGROUP:
            groupnum, bl_group = pdu.waypoint_newgroup()
        else:
            groups = [g[0] for g in pdprops.get_groupitems(context.scene, context)]
            groupnum = groups.index(self.group_enum)

        wp_coll = bpy.data.collections['Waypoints']
        pad_id = 1 + max([wp.pd_waypoint.id for wp in wp_coll.objects])

        pos = pdu.get_view_location()
        bl_waypoint = stpi.create_waypoint(pad_id, pos, groupnum)
        pdu.select_obj(bl_waypoint)
        return {'FINISHED'}


class PDTOOLS_OT_SetupWaypointDelete(Operator):
    bl_idname = "pdtools.op_setup_waypoint_delete"
    bl_label = "PD: Delete Waypoint"
    bl_description = "Delete this waypoint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        waypoints = scn['waypoints']

        bl_waypoint = context.active_object
        pd_waypoint = bl_waypoint.pd_waypoint
        padnum = pd_waypoint.padnum

        neighbours_coll = pd_waypoint.neighbours_coll
        for neighbour in neighbours_coll:
            bl_neighbour = waypoints[str(neighbour.padnum)]
            pd_neighbour = bl_neighbour.pd_waypoint
            pdu.waypoint_remove_neighbour(pd_neighbour, padnum)

        del waypoints[str(padnum)]
        bpy.data.objects.remove(bl_waypoint)
        return {'FINISHED'}


class PDTOOLS_OT_SetupWaypointCreateFromMesh(Operator):
    bl_idname = "pdtools.op_setup_waypoint_createfrommesh"
    bl_label = "Create Waypoint From Mesh"
    bl_description = "Creates waypoints from the mesh vertices and edges"
    bl_options = {'REGISTER', 'UNDO'}

    group_enum: EnumProperty(name="group_enum", description="Waypoint Group", items=pdprops.get_groupitems)
    keep_mesh: BoolProperty(name="keep_mesh", default=True, description="Do Not Delete The Mesh")

    def draw(self, context):
        layout = self.layout
        row = layout.row().split(factor=0.4)
        row.prop(self, 'group_enum', text='')
        row.prop(self, 'keep_mesh', text='Keep The Mesh')

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def create(self, context):
        bl_obj = context.active_object
        bm = bmesh.new()
        bm.from_mesh(bl_obj.data)

        pos = bl_obj.matrix_world.translation

        wp_coll = bpy.data.collections['Waypoints']
        padnum = 1 + max([wp.pd_waypoint.padnum for wp in wp_coll.objects])

        groupname = self.group_enum
        if groupname == pdprops.NEWGROUP:
            groupnum, bl_group = pdu.waypoint_newgroup()
            groupname = bl_group.name
        else:
            groups = [g[0] for g in pdprops.get_groupitems(context.scene, context)]
            groupnum = groups.index(self.group_enum)

        waypoints = []
        for v in bm.verts:
            bl_waypoint = stpi.create_waypoint(padnum, pos + v.co, groupnum)
            pd_waypoint = bl_waypoint.pd_waypoint
            pd_waypoint.padnum = padnum
            pd_waypoint.groupnum = groupnum
            pd_waypoint.group_enum = groupname
            waypoints.append(bl_waypoint)
            padnum += 1

        for e in bm.edges:
            v0, v1 = e.verts
            bl_waypoint0 = waypoints[v0.index]
            bl_waypoint1 = waypoints[v1.index]

            stu.wp_addneighbour(bl_waypoint0, bl_waypoint1)
            stu.wp_addneighbour(bl_waypoint1, bl_waypoint0)

        bm.free()

        if not self.keep_mesh:
            bpy.data.objects.remove(bl_obj)

        if waypoints:
            pdu.select_obj(waypoints[-1])

    def execute(self, context):
        self.create(context)
        pdu.redraw_ui()
        return {'FINISHED'}


class PDTOOLS_OT_SetupWaypointCreateNeighbours(Operator):
    bl_idname = "pdtools.op_setup_waypoint_createneighbours"
    bl_label = "Create Neighbours"
    bl_description = "Create waypoint neighbours around this waypoint"
    bl_options = {'REGISTER', 'UNDO'}

    num: IntProperty(name="num", default=1, min=0, description="Number Of Neighbours")
    distance: IntProperty(name="distance", default=100, min=0, description="Number Of Neighbours")

    def draw(self, _context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'num', text='Number')
        col.prop(self, 'distance', text='Distance')

    def execute(self, context):
        bl_waypoint = context.active_object
        pd_waypoint = bl_waypoint.pd_waypoint
        objpos = bl_waypoint.matrix_world.translation

        wp_coll = bpy.data.collections['Waypoints']
        padnum = 1 + max([wp.pd_waypoint.padnum for wp in wp_coll.objects])
        groupnum = pd_waypoint.groupnum
        groupname = pdu.group_name(groupnum)
        bl_group = bpy.data.objects[groupname]

        angle = 0
        for i in range(self.num):
            r = self.distance
            p = (r * math.cos(angle), r * math.sin(angle), 0)
            pos = objpos + Vector(p)

            bl_neighbour = stpi.create_waypoint(padnum, pos, bl_group, False)
            pd_neighbour = bl_neighbour.pd_waypoint
            pd_neighbour.padnum = padnum
            pd_neighbour.groupnum = groupnum
            pd_neighbour.group_enum = groupname

            stu.wp_addneighbour(bl_waypoint, bl_neighbour)
            stu.wp_addneighbour(bl_neighbour, bl_waypoint)

            angle += 2*math.pi / self.num
            padnum += 1

        return {'FINISHED'}

    def invoke(self, context, _event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=150)


class PDTOOLS_OT_SetupLiftRemoveStop(Operator):
    bl_idname = "pdtools.op_setup_lift_remove_stop"
    bl_label = "PD: Remove Stop"
    bl_description = "Remove the selected lift stop"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name='index', default=0, options={'LIBRARY_EDITABLE'})

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift
        stops = [pd_lift.stop1, pd_lift.stop2, pd_lift.stop3, pd_lift.stop4]
        stop = stops[self.index]

        bpy.data.objects.remove(stop, do_unlink=True)

        return {'FINISHED'}


class PDTOOLS_OT_SetupInterlinkCreate(Operator):
    bl_idname = "pdtools.op_setup_interlink_create"
    bl_label = "PD: Create Interlink Object"
    bl_description = "Create interlink object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift
        pd_interlinks = pd_lift.interlinks

        interlink = pd_interlinks.add()
        interlink.name = f'{bl_obj.name} Interlink {len(pd_interlinks)}'
        interlink.controlled = bl_obj
        interlink.pd_obj.type = OBJTYPE_LINKLIFTDOOR | pdprops.PD_OBJTYPE_PROP
        return {'FINISHED'}


class PDTOOLS_OT_SetupInterlinkRemove(Operator):
    bl_idname = "pdtools.op_setup_interlink_remove"
    bl_label = "PD: Remove Interlink Object"
    bl_description = "Remove the selected interlink object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift
        pd_interlinks = pd_lift.interlinks

        if len(pd_interlinks) == 0: return {'FINISHED'}

        pd_interlinks.remove(pd_lift.active_interlink_idx)

        return {'FINISHED'}


class PDTOOLS_OT_SetupDoorSelectSibling(Operator):
    bl_idname = "pdtools.door_select_sibling"
    bl_label = "Select Sibling"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bl_door = context.active_object
        bl_sibling = bl_door.pd_door.sibling
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = bl_sibling
        bl_sibling.select_set(True)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


def grid(obj, layout, propname, array, flagsfilter, flagstoggle, multiple=True):
    layout.scale_y = .8

    if multiple:
        items = [e[0][0] if len(e[0]) < 2 else f'{e[0][0]} (+)' for e in array]
    else:
        items = [e[0] for e in array]

    for idx, item in enumerate(items):
        if len(flagsfilter) == 0 or flagsfilter in item.lower():
            layout.prop(obj, propname, index=idx, text=item, toggle=flagstoggle)


class PDTOOLS_OT_SetupObjEditFlags(bpy.types.Operator):
    bl_label = "Flags"
    bl_idname = "pdtools.setupobj_editflags"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ""

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=650)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        bl_obj = context.active_object
        pd_obj = bl_obj.pd_prop

        layout = self.layout
        scn = context.scene

        row = layout.row().split(factor=0.07)
        row.label(text='Filter:')
        row = row.row().split(factor=0.2)
        row.prop(scn, "flags_filter", text='', expand=True)

        row = row.row().split(factor=0.05)
        row.prop(scn, "flags_toggle", text='', icon='OPTIONS')

        row = layout.row().split(factor=0.07)
        row.label(text='Values:')
        row = row.row().split(factor=0.825)
        row = row.row()
        row.prop(pd_obj, "flags1_packed", text='')

        row = row.row()
        row.prop(pd_obj, "flags2_packed", text='')

        row = row.row()
        row.prop(pd_obj, "flags3_packed", text='')

        row = row.row()
        row.context_pointer_set(name='flags_op', data=self)

        row = layout.row()
        col = row.column()
        grid(pd_obj, col, 'flags1', pdprops.OBJ_FLAGS1, scn.flags_filter, scn.flags_toggle)

        col = row.column()
        grid(pd_obj, col, 'flags2', pdprops.OBJ_FLAGS2, scn.flags_filter, scn.flags_toggle)

        col = row.column()
        grid(pd_obj, col, 'flags3', pdprops.OBJ_FLAGS3, scn.flags_filter, scn.flags_toggle)



class PDTOOLS_OT_SetupObjEditPadFlags(bpy.types.Operator):
    bl_label = "Edit Pad"
    bl_idname = "pdtools.setupobj_editpadflags"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ""

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=220)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        bl_obj = context.active_object
        if not bl_obj: return

        # pd_obj = bl_obj.pd_obj
        objtype = pdu.pdtype(bl_obj)
        pad = bl_obj.pd_prop.pad

        layout = self.layout
        scn = context.scene

        layout.label(text='Pad Flags')

        row = layout.row()
        row = row.row()
        row.prop(pad, "flags_packed", text='Value')
        row.prop(pad, "lift", text='Lift')

        pdu.ui_separator(layout, type='LINE')

        row = layout.row()
        col = row.column()
        for item in pdprops.PAD_FLAGS_EDIT:
            layout.prop(pad, 'flags', index=item[1], text=item[0], toggle=scn.flags_toggle)


class PDTOOLS_OT_SetupDoorPlaySound(Operator):
    bl_idname = "pdtools.door_play_sound"
    bl_label = ""

    open: BoolProperty(name='open', default=True, options={'LIBRARY_EDITABLE'})
    soundnum: StringProperty(name='soundnum', options={'LIBRARY_EDITABLE'})

    @classmethod
    def description(cls, context, _properties):
        close = hasattr(context, 'doorclose')
        return 'Play: Door Close' if close else 'Play: Door Open'

    def execute(self, _context):
        blend_dir = os.path.dirname(bpy.data.filepath) # TODO propertly get the sound dir
        device = aud.Device()
        device.stopAll()
        openclose = 'OPEN' if self.open else 'CLOSE'
        name = f'{self.soundnum}{openclose}'
        sound = aud.Sound(f'{blend_dir}/sounds/{name}.ogg')
        sound_buffered = aud.Sound.cache(sound)
        device.play(sound_buffered)
        return {'FINISHED'}


class PDTOOLS_OT_SetupObjectCreate(Operator):
    bl_idname = "pdtools.op_setup_object_create"
    bl_label = 'Create Object'
    bl_description = 'Click on the viewport to create an object'

    created_objs = []

    def raycast(self, context, event):
        scn = context.scene
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y

        # get the ray from the viewport and mouse
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

        ray_target = ray_origin + view_vector

        best_length_squared = -1.0
        picked_obj = None
        hit_pos = None

        coll = bpy.data.collections['Rooms']
        for obj in coll.objects:
            if obj.pd_obj.type != pdprops.PD_OBJTYPE_ROOMBLOCK: continue
            if obj.pd_room.blocktype == pdprops.BLOCKTYPE_BSP: continue

            M = obj.matrix_world
            hit, normal, face_index = pdu.obj_ray_cast(obj, M, ray_origin, ray_target)

            if hit is None: continue

            hit_world = M @ hit
            scn.cursor.location = hit_world
            length_squared = (hit_world - ray_origin).length_squared
            if picked_obj is None or length_squared < best_length_squared:
                best_length_squared = length_squared
                picked_obj = obj
                hitpos = hit_world

        if hitpos:
            bl_obj = self.create_obj(hitpos, picked_obj)
            if bl_obj:
                dim = bl_obj.dimensions
                d = dim.y
                bl_obj.location.z = hitpos.z + d * 0.5 + 1
                self.created_objs.append(bl_obj)

    def next_pad(self, coll_name, type):
        pad = -1
        coll = bpy.data.collections[coll_name].objects
        for obj in coll:
            if obj.pd_obj.type == type:
                pad = max(pad, obj.pd_prop.pad.padnum)

        return pad + 1

    def create_obj(self, pos, picked_obj):
        scn = bpy.context.scene
        sel_type = scn['pd_obj_type']

        bpy.context.view_layer.objects.active = None

        pos = Vec3(pos.y, pos.z, pos.x)
        bbox = Bbox(-10, 10, -10, 10, -10, 10)
        up, look, normal = Vec3(0,1,0), Vec3(1,0,0), Vec3(0,0,1)
        flags = 0 if sel_type == pdprops.PD_PROP_WEAPON else PADFLAG_HASBBOXDATA
        header = pdpads.pad_makeheader(flags, picked_obj.pd_room.roomnum, 0)

        pad = pdpads.Pad(pos, look, up, normal, bbox, header)

        pdtype = sel_type & 0xff00
        if pdtype == pdprops.PD_OBJTYPE_PROP:
            modelnum = scn.pd_modelnames_idx
            padnum = self.next_pad('Props', sel_type)

            flags = 0

            if sel_type == pdprops.PD_PROP_LIFT:
                flags = pdprops.OBJFLAG_XTOPADBOUNDS | pdprops.OBJFLAG_YTOPADBOUNDS | pdprops.OBJFLAG_ZTOPADBOUNDS

            prop_base = {
                'pad': padnum,
                'type': sel_type & 0xff,
                'modelnum': modelnum,
                'flags': flags,
                'flags2': 0,
                'flags3': 0,
                'extrascale': 0x100,
                'maxdamage': 0x03e8,
                'floorcol': 0,
            }

            romdata = rom.load()
            basic_objs = [
                pdprops.PD_PROP_STANDARD,
                pdprops.PD_PROP_GLASS,
                pdprops.PD_PROP_MULTIAMMOCRATE,
            ]
            if sel_type in basic_objs:
                return stpi.setup_create_obj({}, prop_base, romdata, pad)
            elif sel_type == pdprops.PD_PROP_WEAPON:
                prop = {'weaponnum': 0}
                return stpi.setup_create_obj(prop, prop_base, romdata, pad)
            elif sel_type == pdprops.PD_PROP_TINTEDGLASS:
                prop = {
                    'opadist': 0,
                    'xludist': 0,
                }
                return stpi.setup_create_obj(prop, prop_base, romdata, pad)
            elif sel_type == pdprops.PD_PROP_LIFT:
                prop = {
                    'accel'   : 0x0000071C,
                    'maxspeed': 0x0010AAAA,
                    'pads': [],
                }
                bbox = Bbox(-100, 100, -100, 100, -100, 100)
                pad = pdpads.Pad(pos, look, up, normal, bbox, header)
                return stpi.setup_create_obj(prop, prop_base, romdata, pad)
            elif sel_type == pdprops.PD_PROP_DOOR:
                return self.create_door(prop_base, pos, romdata)
        elif pdtype == pdprops.PD_OBJTYPE_INTRO:
            padnum = self.next_pad('Intro', sel_type)
            ofs = 0 if pdtype == pdprops.PD_INTRO_CASE else 24
            pos = Vec3(pos.x, pos.y + ofs, pos.z)
            pad = pdpads.Pad(pos, look, up, normal, bbox, 0)
            return stpi.create_intro_obj(scn.pd_obj_type, pad, padnum, sel_type)

        return None

    def create_door(self, prop_base, pos, romdata):
        prop = {
            'doortype': 0x0,
            'soundtype': 0x0,
            'laserfade': 0x0,
            'doorflags': 0x0,
            'keyflags': 0x0,
            'maxfrac': 0xE666,
            'perimfrac': 0x010000,
            'accel': 0x3333,
            'decel': 0x4000,
            'maxspeed': 0x1333,
            'autoclosetime': 0x0384,
        }
        bbox = Bbox(-6, 6, -50, 50, -100, 100)
        up, look, normal = Vec3(0,1,0), Vec3(1,0,0), Vec3(0,0,1)
        pos = Vec3(pos.x, pos.y + 100, pos.z)
        pad = pdpads.Pad(pos, look, up, normal, bbox, 0)
        return stpi.setup_create_door(prop, prop_base, romdata, pad, False)

    def done(self):
        pdu.select_objects(self.created_objs)
        pdu.redraw_ui()

    def modal(self, context, event):
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.raycast(context, event)
            return {'RUNNING_MODAL'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.done()
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
            self.created_objs.clear()
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

classes = [
    PDTOOLS_OT_SetupObjEditFlags,
    PDTOOLS_OT_SetupObjEditPadFlags,
    PDTOOLS_OT_SetupLiftCreateStop,
    PDTOOLS_OT_SetupLiftRemoveStop,
    PDTOOLS_OT_SetupInterlinkCreate,
    PDTOOLS_OT_SetupInterlinkRemove,
    PDTOOLS_OT_SetupDoorSelectSibling,
    PDTOOLS_OT_SetupDoorPlaySound,
    PDTOOLS_OT_SetupWaypointAddNeighbour,
    PDTOOLS_OT_SetupWaypointRemoveNeighbour,
    PDTOOLS_OT_SetupWaypointCreateFromMesh,
    PDTOOLS_OT_SetupWaypointCreateNeighbours,
    PDTOOLS_OT_SetupWaypointCreate,
    PDTOOLS_OT_SetupWaypointDelete,
    PDTOOLS_OT_SetupObjectCreate,
]

register, unregister = bpy.utils.register_classes_factory(classes)
