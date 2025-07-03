import os
import traceback
import math
import time

import bpy
from bpy.types import Operator, WorkSpaceTool
import gpu
import bmesh
from gpu_extras.batch import batch_for_shader
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty, EnumProperty
from bl_ui import space_toolsystem_common
from bpy_extras import view3d_utils
from mathutils import Vector
import aud

from utils import (
    bg_utils as bgu
)
from pd_data.decl_setupfile import OBJTYPE_LINKLIFTDOOR
from mtxpalette_panel import gen_icons
from model_info import ModelNames, ModelStates
from pd_blendprops import LEVELNAMES
from pd_data.pd_padsfile import *
from pd_data import romdata as rom, pd_padsfile as pdpads
from pd_import import (
    model_import as mdi,
    bg_import as bgi,
    tiles_import as tlimp,
    setup_import as stpi,
)
from pd_export import (
    pads_export as pde,
    tiles_export as tle,
    setup_export as stpe,
    bg_export as bge,
    model_export as mde
)
import pd_addonprefs as pda
import pd_blendprops as pdprops

STEP_BG = 'STEP_BG'
STEP_SETUP = 'STEP_SETUP'
STEP_TILES = 'STEP_TILES'
TILE_BATCH_SIZE = 100

list_bgs = []
list_setups = []
list_pads = []
list_tiles = []

class PDTOOLS_OT_LoadRom(Operator, ImportHelper):
    bl_idname = "pdtools.load_rom"
    bl_label = "Load Rom"
    bl_description = "Load a PD rom, accepted versions: NTSC"

    filter_glob: bpy.props.StringProperty(
        default="*.z64",
    )

    def execute(self, context):
        PDTOOLS_OT_LoadRom.load_rom(context, self.filepath)
        return {'FINISHED'}

    @staticmethod
    def load_rom(context, filepath):
        scn = context.scene

        romdata = rom.Romdata(filepath)

        # save into the addon settings
        pda.pref_save(pda.PD_PREF_ROMPATH, filepath)

        # fill the scene's list of models
        scn.pd_modelfiles.clear()
        scn.pd_modelnames.clear()
        pdprops.rom_bgs.clear()
        pdprops.rom_pads.clear()
        pdprops.rom_setups.clear()
        pdprops.rom_tiles.clear()

        bg_idx = 0
        modelfiles = []
        for filename in romdata.fileoffsets.keys():
            if filename.startswith('bgdata') or filename.startswith('ob'):
                if filename.endswith('.seg'):
                    lvcode = pdu.get_lvcode(filename)
                    bgname = f'bg_{lvcode}'
                    lvname = pdu.get_lvname(lvcode, LEVELNAMES)
                    fullname = f'{lvname} ({bgname})' if lvname else bgname
                    idx = f'{bg_idx:02X}: '
                    pdprops.rom_bgs.append((bgname, idx+fullname, bgname))
                    bg_idx += 1
                elif 'pads' in filename:
                    filename = filename.replace('bgdata/', '')
                    lvcode = pdu.get_lvcode(filename)
                    lvname = pdu.get_lvname(lvcode, LEVELNAMES)
                    fullname = f'{lvname} ({filename})' if lvname else filename
                    pdprops.rom_pads.append((filename, fullname, filename))
                elif 'tiles' in filename:
                    filename = filename.replace('bgdata/', '')
                    lvcode = pdu.get_lvcode(filename)
                    lvname = pdu.get_lvname(lvcode, LEVELNAMES)
                    fullname = f'{lvname} ({filename})' if lvname else filename
                    pdprops.rom_tiles.append((filename, fullname, filename))
            elif filename[0] == 'U':
                lvcode = pdu.get_lvcode(filename)
                bgname = f'bg_{lvcode}'
                mp = ' MP ' if filename.startswith('Ump_') else ' '
                cs = ' CS' if bgname in LEVELNAMES and LEVELNAMES[bgname][2] else ''
                lvname = pdu.get_lvname(lvcode, LEVELNAMES, False)
                fullname = f'{lvname}{cs}{mp}({filename})' if lvname else filename
                pdprops.rom_setups.append((filename, fullname, bgname))
            elif filename[0] in ['P', 'C', 'G']:
                modelfiles.append(filename)
                # if item.alias: # TODO

        modelfiles.sort()
        for filename in modelfiles:
            item = scn.pd_modelfiles.add()
            item.name = filename

        for modelname in ModelNames:
            item = scn.pd_modelnames.add()
            item.name = modelname

        pdprops.rom_pads.sort(key=lambda e: e[1])
        pdprops.rom_setups.sort(key=lambda e: e[1])
        pdprops.rom_tiles.sort(key=lambda e: e[1])

        scn.pd_modelfilenames.clear()
        n = len(romdata.filenames)
        for modelstate in ModelStates:
            filenum = modelstate.filenum
            # JPN ROM (currently not supported) has more models than the others
            if filenum >= n: break

            item = scn.pd_modelfilenames.add()
            item.name = romdata.filenames[filenum]


class PDTOOLS_OT_ExportModel(Operator, ExportHelper):
    bl_idname = "pdtools.export_model"
    bl_label = "Export Model"
    bl_description = "Export the Model"

    filename_ext = ''

    def execute(self, context):
        print(f'Export model: {self.filepath}')
        model_obj = pdu.get_model_obj(context.object)
        try:
            mde.export_model(model_obj, self.filepath)
        except RuntimeError as ex:
            traceback.print_exc()
            pass

        self.report({'INFO'}, "Model Exported")
        return {'FINISHED'}

    def invoke(self, context, _event):
        obj = pdu.get_model_obj(context.object)
        props = obj.pd_model

        blend_filepath = context.blend_data.filepath
        self.filepath = os.path.join(blend_filepath, props.name)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PDTOOLS_OT_AssignMtxToVerts(Operator):
    bl_idname = "pdtools.assign_mtx_verts"
    bl_label = "Assign To Selected"
    bl_description = "Assign matrix to selected vertices"

    mtx: IntProperty()

    def execute(self, context):
        nverts = pdu.assign_mtx_to_selected_verts(self.mtx)
        s = 's' if nverts > 1 else ''
        self.report({"INFO"}, f'Matrix {self.mtx:02X} assigned to {nverts} vert{s}')
        return {'FINISHED'}


class PDTOOLS_OT_SelectVertsUnassignedMtxs(Operator):
    bl_idname = "pdtools.select_vtx_unassigned_mtxs"
    bl_label = "Select Unassigned"
    bl_description = "Select vertices with no assigned matrix"

    def execute(self, context):
        nverts = pdu.select_vtx_unassigned_mtxs()
        s = 's' if nverts > 1 else ''
        self.report({"INFO"}, f'{nverts} vert{s} selected')
        pdu.redraw_ui()
        return {'FINISHED'}


class PDTOOLS_OT_PortalFindRooms(Operator):
    bl_idname = "pdtools.portal_find_rooms"
    bl_label = "Auto Find"
    bl_description = "Find and assign 2 nearest rooms to the portal"

    def execute(self, context):
        bl_portal = context.active_object
        rooms = bgu.portal_find_rooms(bl_portal)
        print(rooms)
        # TODO check result

        props_portal = bl_portal.pd_portal
        props_portal.room1 = rooms[0]
        props_portal.room2 = rooms[1]

        return {'FINISHED'}

class PDTOOLS_OT_TileApplyProps(Operator):
    bl_idname = "pdtools.tile_apply_props"
    bl_label = "Apply Tile Props"
    bl_description = "Apply props to selected tiles"

    def execute(self, context):
        prop = context.pd_tile
        for bl_tile in context.selected_objects:
            bl_tile.pd_tile.flags = prop.flags
            bl_tile.pd_tile.floorcol = prop.floorcol
            bl_tile.pd_tile.floortype = prop.floortype
            # bl_tile.pd_tile.room = prop.room
        n = tlimp.bg_colortiles(context)
        return {'FINISHED'}


class PDTOOLS_OT_RoomCreatePortalBetween(Operator):
    bl_idname = "pdtools.room_create_portal_between"
    bl_label = "Create Portal"
    bl_description = "Create portal between rooms"

    @classmethod
    def poll(cls, context):
        sel = context.selected_objects
        n = len(sel)
        isroom = lambda o: (o.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_ROOMBLOCK
        # typeok = all([(o.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_ROOMBLOCK for o in sel])
        return n == 2 and isroom(sel[0]) and isroom(sel[1])

    def execute(self, context):
        sel = context.selected_objects
        room1 = sel[0]
        room2 = sel[1]
        return {'FINISHED'}


class PDTOOLS_OT_SelectDirectory(Operator):
    bl_idname = "pdtools.select_directory"
    bl_label = "Select Directory"
    bl_options = {'REGISTER'}

    # define this to tell 'fileselect_add' that we want a directory
    directory: StringProperty(name="Path", description="Select Directory")
    filter_folder: BoolProperty(default=True, options={"HIDDEN"})
    type: StringProperty(name='type', options={'LIBRARY_EDITABLE'})

    @classmethod
    def description(cls, context, properties):
        if properties.type == 'EXT_TEXTURES':
            return 'Directory With Replacement Textures'
        elif properties.type == 'EXT_MODELS':
            return 'Directory With Replacement Models'
        else:
            return 'Select Directory'

    def execute(self, context):
        scn = context.scene

        if self.type == 'EXT_TEXTURES':
           scn.external_tex_dir = self.directory
        elif self.type == 'EXT_MODELS':
            scn.external_models_dir = self.directory

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def load_model(_context, modelname=None, filename=None):
    rompath = pda.pref_get(pda.PD_PREF_ROMPATH)
    romdata = rom.Romdata(rompath)

    if modelname:
        model_obj, _ = mdi.import_model(romdata, modelname=modelname)
    elif filename:
        model_obj, _ = mdi.import_model(romdata, filename=filename)
    else:
        raise RuntimeError('load_model() called without modelname and filename params')

    coll = pdu.active_collection()
    pdu.add_to_collection(model_obj, coll=coll)
    stpi.blender_align(model_obj)
    pdu.select_obj(model_obj)


class PDTOOLS_OT_ImportModelFromFile(Operator, ImportHelper):
    bl_idname = "pdtools.import_model_file"
    bl_label = "Import From File"
    bl_description = "Import a model from a file"

    filter_glob: bpy.props.StringProperty(default="*.*",)

    def execute(self, context):
        scn = context.scene
        # when the addon is first installed, the icons need to be generated
        # because the load_post handler won't be called
        if len(scn.color_collection) == 0:
            gen_icons(context)

        # print('import model from file', self.filepath)
        load_model(context, filename=self.filepath)
        return {'FINISHED'}


class PDTOOLS_OT_ImportSelectFile(Operator, ImportHelper):
    bl_idname = "pdtools.import_select_file"
    bl_label = "File"
    bl_description = "Import from an external file"

    filter_glob: bpy.props.StringProperty(default="*", options={'HIDDEN'})
    type: StringProperty(name='type', options={'LIBRARY_EDITABLE', 'HIDDEN'})

    def execute(self, context):
        self.bl_label = "File"
        bl_description = "Import from an external file"
        scn = context.scene
        print('import from file', self.filepath)
        if self.type == 'BG':
            scn.file_bg = self.filepath
        elif self.type == 'pads':
            scn.file_pads = self.filepath
        elif self.type == 'setup':
            scn.file_setup = self.filepath
        elif self.type == 'tiles':
            scn.file_tiles = self.filepath
        return {'FINISHED'}


class PDTOOLS_OT_ImportModelFromROM(Operator):
    bl_idname = "pdtools.import_model_rom"
    bl_label = "Import Model From ROM"

    @classmethod
    def description(cls, context, properties):
        scn = context.scene
        if scn.rompath:
            return 'Import a model from the ROM'
        else:
            return 'ROM not loaded. Go to Preferences > Add-ons > pd_blendtools'

    def execute(self, context):
        scn = context.scene

        # when the addon is first installed, the icons need to be generated
        # because the load_post handler won't be called
        if len(scn.color_collection) == 0:
            gen_icons(context)

        item = scn.pd_modelfiles[scn.pd_modelfiles_idx]
        load_model(context, modelname=item.name)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        layout.template_list('pdtools.list_models', '', scn, 'pd_modelfiles', scn, 'pd_modelfiles_idx', rows=20)


class PDTOOLS_OT_SelectModel(Operator):
    bl_idname = "pdtools.select_model"
    bl_label = "Select Model"
    bl_description = "Select Model"

    type: StringProperty(name='type', options={'LIBRARY_EDITABLE', 'HIDDEN'})
    saved_idx: IntProperty(name='saved_idx', options={'LIBRARY_EDITABLE', 'HIDDEN'})

    def execute(self, context):
        scn = context.scene

        if len(scn.color_collection) == 0:
            gen_icons(context)

        if self.type == 'model':
            bl_obj = context.active_object
            pd_prop = bl_obj.pd_prop
            stu.change_model(bl_obj, scn.pd_modelnames_idx)
            scn.pd_modelnames_idx = self.saved_idx
        else:
            item = scn.pd_modelnames[scn.pd_modelnames_idx]
            scn.pd_model = item.name
        return {'FINISHED'}

    def invoke(self, context, event):
        scn = context.scene

        if self.type == 'model':
            pd_prop = context.active_object.pd_prop
            self.saved_idx = scn.pd_modelnames_idx
            scn.pd_modelnames_idx = pd_prop.modelnum
        else:
            scn.pd_modelnames_idx = ModelNames.index(scn.pd_model)

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        scn = context.scene
        self.layout.template_list('pdtools.list_models', '', scn, 'pd_modelnames',
            scn, 'pd_modelnames_idx', rows=20)

class PDTOOLS_OT_ImportLevel(Operator):
    bl_idname = "pdtools.import_level"
    bl_label = "Import Level"
    bl_description = 'Import levels from the ROM or external files'

    current_item = 0
    romdata = None
    steps = []
    all_props = []

    def next_step(self, context):
        self.steps.pop(0)
        self.current_item = 0
        context.window_manager.import_step += 1
        bpy.context.view_layer.objects.active = None

    def modal(self, context, event):
        scn = context.scene
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            scn.level_loading = False
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if not self.steps:
                scn.level_loading = False
                [a.tag_redraw() for a in context.screen.areas]
                return {'FINISHED'}

            current_step = self.steps[0]
            if current_step == STEP_BG:
                done, roomnum = bgi.bg_import(self.romdata, self.current_item, 0.1)
                self.current_item = roomnum
                if done:
                    # print(f'BGIMPORT done {time.time() - self.t_bgload:2.1f}')
                    self.t_tiles = time.time()
                    self.t_setup = time.time()
                    self.next_step(context)
            elif current_step == STEP_SETUP:
                # setup always needs the rom loaded, because of the models
                if self.romdata is None:
                    self.loadrom()

                romdata, all_props, cur_item = self.romdata, self.all_props, self.current_item
                done, objnum = stpi.setup_import(romdata, all_props, cur_item, 0.2)
                self.current_item = objnum

                if done:
                    dt = time.time() - self.t_setup
                    # print(f'LOAD_SETUP: {dt:2.1f}')
                    self.next_step(context)
            elif current_step == STEP_TILES:
                done = tlimp.tiles_import(self.romdata, self.current_item, TILE_BATCH_SIZE)
                self.current_item += TILE_BATCH_SIZE

                if done:
                    dt = time.time() - self.t_tiles
                    # print(f'LOAD_TILES: {dt:2.1f}')
                    self.next_step(context)

        return {'PASS_THROUGH'}

    def loadrom(self):
        rompath = pda.pref_get(pda.PD_PREF_ROMPATH)
        self.romdata = rom.load(rompath)

    def execute(self, context):
        scn = context.scene
        
        bpy.context.view_layer.objects.active = None

        self.current_item = 0
        scn.level_loading = True
        scn['rooms'] = {}
        self.t_bgload = time.time()
        self.t_setup = time.time()

        loadrom = 'ROM' in [scn.import_src_bg, scn.import_src_tiles]
        if loadrom:
            self.loadrom()

        add_step_if = lambda step, cond: self.steps.append(step) if cond else None

        self.steps.clear()
        self.all_props.clear()

        add_step_if(STEP_BG, scn.import_bg)
        add_step_if(STEP_SETUP, scn.import_pads and scn.import_setup)
        add_step_if(STEP_TILES, scn.import_tiles)

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        wm.import_step = 1
        wm.import_numsteps = len(self.steps)

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw_bg(self, context):
        scn = context.scene

        box = self.layout.box()
        row = box.row().split(factor=0.3)
        row.prop(scn, 'import_bg', text='BG File')
        row = row.row()
        row.label(text='Source:')
        row.prop(scn, 'import_src_bg', expand=True)
        row.enabled = scn.import_bg

        if scn.import_src_bg == 'ROM':
            row = box.row()
            row.prop(scn, 'rom_bgs', text='Level')
            row.enabled = scn.import_bg
        else:
            row = box.row().split(factor=0.9)
            row.prop(scn, 'file_bg', text='')
            op = row.operator('pdtools.import_select_file', text='...')
            op.type = 'BG'
            row.enabled = scn.import_bg

        box.separator(type='LINE')
        row = box.row()
        row.prop(scn, 'level_external_tex', text='Replace Textures')
        row.enabled = scn.import_bg
        row = box.row().split(factor=0.9)
        row.prop(scn, 'external_tex_dir', text='')
        op = row.operator('pdtools.select_directory', text='...')
        op.type = 'EXT_TEXTURES'
        row.enabled = scn.level_external_tex and scn.import_bg

    def draw_pads(self, context):
        scn = context.scene

        box = self.layout.box()
        row = box.row().split(factor=0.3)
        row.prop(scn, 'import_pads', text='Pads')
        row = row.row()
        row.label(text='Source:')
        row.prop(scn, 'import_src_pads', expand=True)
        row.enabled = scn.import_pads

        if scn.import_src_pads == 'ROM':
            row = box.row()
            row.prop(scn, 'rom_pads', text='Level')
            row.enabled = scn.import_pads
        else:
            row = box.row().split(factor=0.9)
            row.prop(scn, 'file_pads', text='')
            op = row.operator('pdtools.import_select_file', text='...')
            op.type = 'pads'
            row.enabled = scn.import_pads

    def draw_setup(self, context):
        scn = context.scene
        enabled = scn.import_setup and scn.import_pads

        box = self.layout.box()
        row = box.row().split(factor=0.3)
        row.prop(scn, 'import_setup', text='Setup')
        row = row.row()
        row.label(text='Source:')
        row.prop(scn, 'import_src_setup', expand=True)
        row.enabled = enabled
        box.enabled = scn.import_pads

        if scn.import_src_setup == 'ROM':
            row = box.row()
            row.prop(scn, "rom_setups", text='Level')
            row.enabled = enabled
        else:
            row = box.row().split(factor=0.9)
            row.prop(scn, 'file_setup', text='')
            op = row.operator('pdtools.import_select_file', text='...')
            op.type = 'setup'
            row.enabled = scn.import_setup

        box.separator(type='LINE')
        row = box.row()
        row.prop(scn, 'level_external_models', text='Replace Models')
        row.enabled = enabled
        row = box.row().split(factor=0.9)
        row.prop(scn, 'external_models_dir', text='')
        op = row.operator('pdtools.select_directory', text='...')
        op.type = 'EXT_MODELS'
        row.enabled = scn.level_external_tex and scn.import_bg

    def draw_tiles(self, context):
        scn = context.scene

        box = self.layout.box()
        row = box.row().split(factor=0.3)
        row.prop(scn, 'import_tiles', text='Tiles')
        row = row.row()
        row.label(text='Source:')
        row.prop(scn, 'import_src_tiles', expand=True)
        row.enabled = scn.import_tiles

        if scn.import_src_tiles == 'ROM':
            row = box.row()
            row.prop(scn, 'rom_tiles', text='Level')
            row.enabled = scn.import_tiles
        else:
            row = box.row().split(factor=0.9)
            row.prop(scn, 'file_tiles', text='')
            op = row.operator('pdtools.import_select_file', text='...')
            op.type = 'tiles'
            row.enabled = scn.import_tiles

    def draw(self, context):
        self.draw_bg(context)

        self.layout.separator(type='SPACE')
        self.draw_pads(context)

        self.layout.separator(type='SPACE')
        self.draw_setup(context)

        self.layout.separator(type='SPACE')
        self.draw_tiles(context)

class PDTOOLS_OT_ExportLevel(Operator):
    bl_idname = "pdtools.export_level"
    bl_label = "Export Level"
    bl_description = "Export Level To A File"

    def export(self, scene, module, filename):
        dir = scene.export_dir
        sep = os.sep if dir[-1] != os.sep else ''
        filepath = f'{dir}{sep}{filename}'
        module.export(filepath, scene.export_compress)

    def execute(self, context):
        scn = context.scene

        if not scn.export_name or not scn.export_dir:
            return {'CANCELLED'}

        if scn.export_bg:
            self.export(scn, bge, scn.export_file_bg)

        if scn.export_pads:
            self.export(scn, pde, scn.export_file_pads)

        if scn.export_setup:
            self.export(scn, stpe, scn.export_file_setup)

        if scn.export_tiles:
            self.export(scn, tle, scn.export_file_tiles)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw_options(self, context):
        scn = context.scene

        row = self.layout.row()
        icon = 'NONE' if scn.export_name else 'ERROR'
        row.prop(scn, 'export_name', text='Level Name', icon=icon)

        row = self.layout.row()
        icon = 'NONE' if scn.export_dir else 'ERROR'
        row.prop(scn, 'export_dir', text='Folder', icon=icon)

        row = self.layout.row()
        row.prop(scn, 'export_compress', text='Compress Files')

    def draw_file(self, context, prop_name, prop_text, enabled):
        scn = context.scene

        row = self.layout.row().split(factor=0.3)
        icon = 'NONE' if scn.export_name else 'ERROR'
        row.prop(scn, f'export_{prop_name}', text=prop_text)
        row = row.row()
        row.prop(scn, f'export_file_{prop_name}', text='', icon=icon)
        row.enabled = enabled

    def draw(self, context):
        scn = context.scene

        self.draw_options(context)
        self.layout.separator(type='LINE')
        self.draw_file(context, 'bg', 'BG', scn.export_bg)
        self.draw_file(context, 'pads', 'Pads', scn.export_pads)
        self.draw_file(context, 'setup', 'Setup', scn.export_setup)
        self.draw_file(context, 'tiles', 'Tiles', scn.export_tiles)


class PDTOOLS_OT_RoomSplitByPortal(Operator):
    bl_idname = "pdtools.room_split_by_portal"
    bl_label = "Split Room By Portal"
    # bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # self.report({'INFO'}, self.msg)
        scn = context.scene
        bl_roomblock = context.active_object
        bl_portal = scn.pd_portal
        bl_roomblock_new = bgu.room_split_by_portal(bl_roomblock, bl_portal, context)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = bl_roomblock_new
        bl_roomblock_new.select_set(True)
        scn.pd_portal = None
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class PDTOOLS_OT_RoomSelectAllBlocks(Operator):
    bl_idname = "pdtools.op_room_select_all_blocks"
    bl_label = "Select All Blocks In Room"
    # bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bl_room = context.active_object
        bl_room = bgu.parent_room(bl_room) if pdu.pdtype(bl_room) == pdprops.PD_OBJTYPE_ROOMBLOCK else bl_room

        bpy.ops.object.select_all(action="DESELECT")
        for child in bl_room.children:
            child.select_set(True)

        return {'FINISHED'}


class PDTOOLS_OT_RoomSelectRoom(Operator):
    bl_idname = "pdtools.op_room_select_room"
    bl_label = "Select Room"
    bl_description = "Select Room"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bl_roomblock = context.active_object
        bl_room = bgu.parent_room(bl_roomblock)
        pdu.select_obj(bl_room)
        return {'FINISHED'}


BLOCKTYPES = [
    (e, e, e) for e in [pdprops.BLOCKTYPE_DL, pdprops.BLOCKTYPE_BSP]
]

class PDTOOLS_OT_RoomCreateBlock(Operator):
    bl_idname = "pdtools.op_room_create_block"
    bl_label = "Create Block"
    bl_description = "Create a new block in this room"
    bl_options = {'REGISTER', 'INTERNAL'}

    layer: EnumProperty(name="layer", description="Room Layer", items=pdprops.BLOCK_LAYER)
    blocktype: EnumProperty(name='blocktype', default=BLOCKTYPES[0][0], items=BLOCKTYPES, options={'LIBRARY_EDITABLE'})

    def invoke(self, context, event):
        bl_room = context.active_object

        if pdu.pdtype(bl_room) == pdprops.PD_OBJTYPE_ROOM:
            wm = context.window_manager
            return wm.invoke_props_dialog(self, width=150)

        return self.execute(context)

    def draw(self, context):
        bl_room = context.active_object

        if pdu.pdtype(bl_room) != pdprops.PD_OBJTYPE_ROOM:
            return

        layout = self.layout
        col = layout.column()
        col.prop(self, 'layer', text='Layer')
        col.prop(self, 'blocktype', text='Type')

    def execute(self, context):
        bl_room = context.active_object

        blocks = [b for b in bl_room.children]
        for block in blocks: blocks += [b for b in block.children]
        blocknum = 1 + max([block.pd_room.blocknum for block in blocks])

        pd_room = bl_room.pd_room
        roomnum = pd_room.roomnum
        layer = self.layer
        name = bgu.blockname(roomnum, blocknum, self.blocktype, layer)

        bl_roomblock = bpy.data.objects.new(name, None)
        bl_roomblock.parent = bl_room
        bl_roomblock.pd_room.parent_enum = bl_room.name

        pdu.add_to_collection(bl_roomblock, 'Rooms')
        bgu.roomblock_set_props(bl_roomblock, roomnum, pd_room.room, blocknum, layer, self.blocktype)

        pdu.select_obj(bl_roomblock)
        return {'FINISHED'}


class PDTOOLS_OT_PortalFromEdge(Operator):
    bl_idname = "pdtools.op_portal_from_edge"
    bl_label = "Portal From Edge"
    # bl_options = {'REGISTER', 'INTERNAL'}

    def ws_update_geometry(_self, _ctx):
        PD_WSTOOL_PortalFromEdge.update_geometry()

    direction: bpy.props.EnumProperty(
        items=[
            ('vertical', 'Vertical', 'Vertical', 'Vertical', 1),
            ('horizontal', 'Horizontal', 'Horizontal', 'Horizontal', 2),
        ],
        name='Direction',
        description='Portal Direction (World)',
        default='vertical',
    )

    elevation: FloatProperty(name='Elevation', default=0, min=-180, max=180,
                             description='Rotation From The Edge Towards The Up Direction',
                             update=ws_update_geometry)

    pitch: FloatProperty(name='Pitch', default=0, min=-180, max=180,
                         # description='' ,
                         description='Rotation Around The Edge Axis',
                         update=ws_update_geometry)

    width: FloatProperty(name='width', default=10, min=1, max=10000,
                         update=ws_update_geometry)

    height: FloatProperty(name='height', default=10, min=1, max=10000,
                          update = ws_update_geometry)

    def execute(self, context):
        bl_obj = context.edit_object
        bm = bmesh.from_edit_mesh(bl_obj.data)

        edges_sel = [e for e in bm.edges if e.select]

        n = len(edges_sel)
        if n != 1:
            bm.free()
            msg = 'No Selection' if n < 1 else 'Select Only One Edge'
            pdu.msg_box('', msg, 'ERROR')
            return {'FINISHED'}

        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        props = tool.operator_properties(self.bl_idname)

        w, h = props.width, props.height
        elv, pitch = props.elevation, props.pitch
        direction = props.direction

        edge = edges_sel[0]
        M = bl_obj.matrix_world
        verts = bgu.portal_verts_from_edge(edge, M, w, h, elv, pitch, direction)
        print(w, h, edge)
        print(verts)
        print(M)
        bgu.new_portal_from_verts(bl_obj, verts)
        edge.select = False
        bm.free()
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class PD_WSTOOL_PortalFromEdge(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = "pdtools.ws_new_portal_from_edge"
    bl_label = "Portal From Edge"
    bl_description = "Creates a new portal from the selected edge"
    bl_icon = "ops.mesh.primitive_cube_add_gizmo"
    bl_widget = None
    # bl_keymap = (
    #     ("object.simple_operator", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
    # )

    _batch = None
    _draw_handle = None
    _shader = None

    @staticmethod
    def draw_prop(layout, props, name):
        layout.label(text=f'{name}:')
        layout.prop(props, name.lower(), text='')

    @staticmethod
    def draw_settings(context, layout, tool, extra=False):
        props = tool.operator_properties('pdtools.op_portal_from_edge')

        if extra:
            col = layout.column()
            row = col.row()
            PD_WSTOOL_PortalFromEdge.draw_prop(row, props, 'Direction')
            row = col.row()
            PD_WSTOOL_PortalFromEdge.draw_prop(row, props, 'Elevation')
            row = col.row()
            PD_WSTOOL_PortalFromEdge.draw_prop(row, props, 'Pitch')
            return

        PD_WSTOOL_PortalFromEdge.draw_prop(layout, props, 'width')
        PD_WSTOOL_PortalFromEdge.draw_prop(layout, props, 'height')

        # this will call this very function, with the parameter extra = True
        layout.popover("TOPBAR_PT_tool_settings_extra", text="...")
        layout.operator("pdtools.op_portal_from_edge", text='Create Portal')

    @classmethod
    def poll(self, context):
        if context.object and context.object.type == 'MESH':
            return context.object.mode == 'EDIT'

    @classmethod
    def update_geometry(cls):
        # Get current properties
        context = bpy.context
        tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        if tool and tool.idname == cls.bl_idname:
            bl_obj = context.edit_object
            bm = bmesh.from_edit_mesh(bl_obj.data)

            edges_sel = [e for e in bm.edges if e.select]

            if len(edges_sel) != 1:
                bm.free()
                context.area.tag_redraw()
                return 1

            props = tool.operator_properties(PDTOOLS_OT_PortalFromEdge.bl_idname)
            w, h = props.width, props.height

            elv, pitch = props.elevation, props.pitch
            direction = props.direction

            edge = edges_sel[0]
            M = bl_obj.matrix_world
            coords = bgu.portal_verts_from_edge(edge, M, w, h, elv, pitch, direction)
            indices = [(0, 1), (1, 2), (2, 3), (3, 0)]

            cls._batch = batch_for_shader(
                cls._shader, 'LINES',
                {'pos': coords}, indices= indices
            )

            # Force viewport update
            if context.area:
                context.area.tag_redraw()

            bm.free()
            return 0
    @classmethod
    def draw_callback_px(cls):
        if cls._shader:
            res = cls.update_geometry()
            if res: return

            gpu.state.line_width_set(2)
            cls._shader.bind()
            cls._shader.uniform_float("color", (1, 1, 0, 1))
            cls._batch.draw(cls._shader)

    @classmethod
    def setup_draw_handler(cls):
        if cls._draw_handle is None:
            if not cls._shader:
                cls._shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                # initial geometry creation
                cls.update_geometry()

            cls._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                cls.draw_callback_px, (), 'WINDOW', 'POST_VIEW')

    @classmethod
    def remove_draw_handler(cls):
        if cls._draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._draw_handle, 'WINDOW')
            cls._draw_handle = None


class PDTOOLS_OT_PortalFromFace(Operator):
    bl_idname = "pdtools.op_portal_from_face"
    bl_label = "PD: Portal From Face"
    bl_description = "Creates a portal from the selected face"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        err = bgu.new_portal_from_faces(context)
        if err:
            pdu.msg_box('', err, 'ERROR')
        return {'FINISHED'}

class PDTOOLS_OT_TilesFromFaces(Operator):
    bl_idname = "pdtools.op_tiles_from_faces"
    bl_label = "PD: Tiles From Faces"
    bl_description = "Creates tiles from the selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.edit_object
        bm = bmesh.from_edit_mesh(bl_obj.data)
        faces_sel = [f for f in bm.faces if f.select]

        if not faces_sel:
            pdu.msg_box('', 'No Selection', 'ERROR')
            bm.free()
            return {'FINISHED'}

        lib = bpy.data.collections
        num = len(lib['Tiles'].objects) if 'Tiles' in lib else 0
        tiles = []
        for face in faces_sel:
            bl_tile = bgu.tile_from_face(f'Tile_{num}', bl_obj, face)
            tiles.append(bl_tile)
            num += 1

        # switch to object mode and select all the newly created tiles
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action='DESELECT')
        for tile in tiles: tile.select_set(True)
        pdu.set_active_obj(tiles[0])
        bm.free()
        return {'FINISHED'}


class PDTOOLS_OT_TilesSelectSameRoom(Operator):
    bl_idname = "pdtools.op_tiles_select_room"
    bl_label = "PD: Select All From Room"
    bl_description = "Select all tiles from the same room"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_tile = bl_obj.pd_tile

        bpy.ops.object.select_all(action='DESELECT')
        tiles = bpy.data.collections['Tiles'].objects
        for bl_tile2 in tiles:
            pd_tile2 = bl_tile2.pd_tile
            if pd_tile2.roomnum == pd_tile.roomnum:
                bl_tile2.select_set(True)

        return {'FINISHED'}

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

        layout.separator(type='LINE')

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

class PDTOOLS_OT_MessageBox(Operator):
    bl_idname = "pdtools.messagebox"
    bl_label = "Message Box"

    msg: StringProperty(default='')

    def execute(self, _context):
        self.report({'INFO'}, self.msg)
        # print(f'OP: {self.msg}')
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


classes = [
    PDTOOLS_OT_LoadRom,
    PDTOOLS_OT_ImportModelFromROM,
    PDTOOLS_OT_ImportModelFromFile,
    PDTOOLS_OT_SelectModel,
    PDTOOLS_OT_ImportLevel,
    PDTOOLS_OT_ImportSelectFile,
    PDTOOLS_OT_AssignMtxToVerts,
    PDTOOLS_OT_ExportModel,
    PDTOOLS_OT_ExportLevel,
    PDTOOLS_OT_SelectVertsUnassignedMtxs,
    PDTOOLS_OT_SelectDirectory,
    PDTOOLS_OT_PortalFindRooms,
    PDTOOLS_OT_RoomCreatePortalBetween,
    PDTOOLS_OT_RoomSplitByPortal,
    PDTOOLS_OT_RoomSelectAllBlocks,
    PDTOOLS_OT_RoomSelectRoom,
    PDTOOLS_OT_RoomCreateBlock,
    PDTOOLS_OT_TileApplyProps,
    PDTOOLS_OT_PortalFromEdge,
    PDTOOLS_OT_PortalFromFace,
    PDTOOLS_OT_TilesFromFaces,
    PDTOOLS_OT_TilesSelectSameRoom,
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
    PDTOOLS_OT_MessageBox,
]

# this callback is to detect when the selected tool changed, and update the drawing
# state of the PortalFromEdge tool
def factory_callback(func):
    def callback(*args, **kwargs):
        idname = args[2]
        if idname == PD_WSTOOL_PortalFromEdge.bl_idname:
            PD_WSTOOL_PortalFromEdge.setup_draw_handler()
            PD_WSTOOL_PortalFromEdge.update_geometry()
        else:
            PD_WSTOOL_PortalFromEdge.remove_draw_handler()

        return func(*args, **kwargs)
    return callback

space_toolsystem_common.activate_by_id = factory_callback(
    space_toolsystem_common.activate_by_id
)

def pd_editmode_menu(self, context):
    self.layout.separator(factor=1.0)
    self.layout.operator(PDTOOLS_OT_PortalFromFace.bl_idname)
    self.layout.operator(PDTOOLS_OT_TilesFromFaces.bl_idname)

def pd_editmode_ctxmenu(self, context):
    if bpy.context.tool_settings.mesh_select_mode[2]:
        self.layout.separator(factor=1.0)
        self.layout.operator(PDTOOLS_OT_PortalFromFace.bl_idname)
        self.layout.operator(PDTOOLS_OT_TilesFromFaces.bl_idname)

def remove_menu():
    bpy.types.VIEW3D_MT_edit_mesh_faces.remove(pd_editmode_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(pd_editmode_ctxmenu)

def register():
    for cl in classes:
        bpy.utils.register_class(cl)


    # TMP
    pdu.unregister_tool('pdtools.ws_new_portal_from_edge', 'VIEW_3D', 'EDIT_MESH')
    pdu.unregister_tool('pdtools.ws_new_portal_from_face', 'VIEW_3D', 'EDIT_MESH')

    bpy.utils.register_tool(PD_WSTOOL_PortalFromEdge,
                            after={"builtin.scale_cage"}, separator=True, group=True)

    bpy.types.VIEW3D_MT_edit_mesh_faces.append(pd_editmode_menu)  # for top menu
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(pd_editmode_ctxmenu)  # for context menu


def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)

    bpy.utils.unregister_tool(PD_WSTOOL_PortalFromEdge)
    PD_WSTOOL_PortalFromEdge.remove_draw_handler()


if __name__ == '__main__':
    register()
