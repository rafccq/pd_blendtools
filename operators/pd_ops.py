import os
import time

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty

from pd_data.model_info import ModelNames, ModelStates
from pd_blendprops import LEVELNAMES
from pd_data.pd_padsfile import *
from pd_data import romdata as rom
from pd_import import (
    bg_import as bgi,
    tiles_import as tlimp,
    setup_import as stpi,
)
from pd_export import (
    pads_export as pde,
    tiles_export as tle,
    setup_export as stpe,
    bg_export as bge,
)
from pd_blendtools import pd_addonprefs as pda
import pd_blendprops as pdprops
from materials import pd_materials as pdm

from fast64.f3d import f3d_material as f3dm


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
        pda.set_rompath(filepath)

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

    def finished(self, context):
        scn = context.scene
        scn.level_loading = False
        [a.tag_redraw() for a in context.screen.areas]

        n = len(bpy.data.materials)
        for i, mat in enumerate(bpy.data.materials):
            if not mat.is_f3d: continue

            t0 = time.time()
            f3dm.update_node_values_of_material(mat, bpy.context)
            # print(f'Mat {i}/{n} {time.time() - t0:2.3f}')

    def modal(self, context, event):
        scn = context.scene
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            scn.level_loading = False
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if not self.steps:
                self.finished(context)
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
        rompath = pda.rompath()
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

        pdu.ui_separator(box, type='LINE')
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

        pdu.ui_separator(box, type='LINE')
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

        pdu.ui_separator(self.layout, type='SPACE')
        self.draw_pads(context)

        pdu.ui_separator(self.layout, type='SPACE')
        self.draw_setup(context)

        pdu.ui_separator(self.layout, type='SPACE')
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
        pdu.ui_separator(self.layout, type='LINE')
        self.draw_file(context, 'bg', 'BG', scn.export_bg)
        self.draw_file(context, 'pads', 'Pads', scn.export_pads)
        self.draw_file(context, 'setup', 'Setup', scn.export_setup)
        self.draw_file(context, 'tiles', 'Tiles', scn.export_tiles)


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

class PDTOOLS_OT_UnlinkPDMaterialImage0(Operator):
    bl_idname = "pdtools.tex0_unlink"
    bl_label = "Unlink PD Material Image"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    def execute(self, context):
        context.material.pd_mat.texload.tex0 = None
        return {"FINISHED"}

class PDTOOLS_OT_UnlinkPDMaterialImage1(Operator):
    bl_idname = "pdtools.tex1_unlink"
    bl_label = "Unlink PD Material Image"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    def execute(self, context):
        context.material.pd_mat.texload.tex1 = None
        return {"FINISHED"}

class PDTOOLS_OT_CreatePDMaterial(Operator):
    bl_idname = "pdtools.create_pd_mat"
    bl_label = "Create PD Material (Simple)"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        bl_obj = context.active_object
        replacements = {'(opa)': '', '(xlu)': '', ' ': '_', '__': '_'}
        name = pdu.str_replace(bl_obj.name, replacements)
        name = f'{name[0].upper()}{name[1:]}' #capitalize the name
        n = len(bl_obj.data.materials)
        mat = pdm.material_from_template(f'{name}_Mat{n}', 'DIFFUSE')
        mat.is_pd = True
        bl_obj.data.materials.append(mat)
        return {"FINISHED"}

classes = [
    PDTOOLS_OT_LoadRom,
    PDTOOLS_OT_ImportLevel,
    PDTOOLS_OT_ImportSelectFile,
    PDTOOLS_OT_ExportLevel,
    PDTOOLS_OT_SelectDirectory,
    PDTOOLS_OT_MessageBox,
    PDTOOLS_OT_UnlinkPDMaterialImage0,
    PDTOOLS_OT_UnlinkPDMaterialImage1,
    PDTOOLS_OT_CreatePDMaterial,
]

register, unregister = bpy.utils.register_classes_factory(classes)
