import bpy
from bpy.types import Material
from bpy.utils import register_classes_factory

from materials.pd_materials import PDMaterialProperty, PDMaterialPanel
from materials.mat_setcombine import MatSetCombine
from materials.mat_geomode import MatGeoMode
from materials.mat_othermode_h import MatOtherModeH
from materials.mat_othermode_l import MatOtherModeL
from materials.mat_tex import MatTexLoad, MatTexConfig

from fast64 import f3d

from reload_util import import_modules
_modules_loaded = import_modules(__file__, globals())

classes = [
    MatSetCombine,
    MatGeoMode,
    MatOtherModeH,
    MatOtherModeL,
    MatTexConfig,
    MatTexLoad,
    PDMaterialProperty,
    PDMaterialPanel,
]

register_cls, unregister_cls = register_classes_factory(classes)

def register():
    register_cls()

    Material.pd_mat = bpy.props.PointerProperty(type=PDMaterialProperty)
    Material.is_pd = bpy.props.BoolProperty(name='is_pd', default=False)

def unregister():
    unregister_cls()
