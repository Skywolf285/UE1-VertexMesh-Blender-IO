#======================================================================

#   Unreal Vertex format exporter for Blender 2.80
#   Created by: Skywolf
#
#   History:
#
#   1.3.8 - 14/12/2024
#       -Fixed issue with wrong material index being assigned to polygons. It now correctly searches in the object's assigned materials rather than the entire open .blend file's materials array.
#
#   1.3.7 - 29/03/2021
#       -Made folder filepaths OS agnostic. Exporting with folder structure on Linux should work correctly now.
#
#   1.3.6 - 26/11/2020
#       -Fixed polyflags getting combined inbetween materials. This made so that, for example, two _UNLIT materials created one _UNLIT (16) and one _FLAT (32) material.
#       
#
#   1.3.5 - 28/7/2019
#       -Fixed the _TRANSLUCENT_ flag when importing and exporting materials to _TRANSLUCENT.
#       -Added automatic detection of the model format.
#       -Made importer not create any keyframes nor set any animation data if the mesh only has 1 frame of animation.
#       -Exporter now checks for changes in vertex count to avoid unexpected breaking of animations due to procedural modifiers and the like.
#       -Exporter now returns to the starting frame of the last exported animation to make re-exporting easier.
#       -Importer now adds the name of the file to the material name. This is to ensure the material for the model is unique.
#       -Fixed Importer only looking for materials in the created objects rather than all materials. This caused a new material to be made for each polygon using a material that already existed but wasn't used on the created object.
#       -Fixed Exporter writing multiple #exec texture import lines for materials that share the same texnum.
#       -Exporter now accepts both .BMP and .PCX extensions for textures when writing the .uc file. Any texture that isn't either of the two gets changed to .PCX. Also fixes issue where files got double file extensions.
#
#   1.3.4 - 27/7/2019
#       -Made exporter and importer compatible with Blender 2.8. It now looks for the active material node for texture file name.
#
#   1.3.3 - 19-1-2019
#       -Fixed vertex order for polygons to fix weapon triangle.
#       -Made animation import use sequence for keyframe playback (instead of relative). Functionally the same but much cleaner as it is the intended way to do vertex based animation.
#       -Removed some console output when importing. This slowed down the process quite a lot so it now requires setting the bDebug flag to True in import_unreal_3d.py
#
#   1.3.2 - 30-9-2018
#       -Added a catch for polygons that share the same vertices. Blender has no support for this. So we skip creating these (atleast for now).
#
#   1.3.1 - 21/9/2018
#       -Fixed importer breaking ION Storm format on any animations frame other than the first imported one.
#
#   1.3.0 - 25/9/2017
#       -Added an importer.
#       -Fixed crashing when mesh has no UV layer when exporting.
#
#   1.2.6 - 
#       -Fix the script comparing a str with an int when reading the Texture Slot from the Material name.
#       -Made the class name now the same as the file name gives during export. To avoid "Script vs. class name mismatch" errors.
#       -Added a scale option to make optimizing the model easier.
#       -Removed .pcx extension in the SETTEXTURE lines in the uc file. It should assign textures properly now.
#       -Fixed the script using all UV Layers. Causing the UVs to be incorrect when exporting a model with more than one UV Layer. It now only uses the active one.
#
#   1.2.5 - 04/06/17
#       -Fixed the mesh scaling for ION Storm (Deus Ex) format in the .uc file to adjust for the larger scale due to the larger file format.
#
#   1.2.4 - 04/02/17
#       -Fixed the mesh scaling for ION Storm (Deus Ex) format in the .uc file.
#       -Fixed a crash when exporting the .uc file if the user unchenked exporting the animation and/or data file.
#
#   1.2.3 - 04/01/17
#       -Changed the way the ION Storm (Deus Ex) is written at the suggestion of Han. Should yield the same result but doesn't have the unnecessary bit shifting.
#
#   1.2.2 - 03/31/17
#       -Fixed padding in ION Storm (Deus Ex) format.
#
#
#   1.2.1 - 03/30/17
#       -Fixed crashing when a mesh is exported with no UV data. A model with no UV data will have LODNOTEX=True set in the .uc file.
#       -Added MLOD, LODSTYLE and LODFRAME settings for the .uc file.
#       -Updated the version number in the bl_info section this time....
#
#   1.1.2 - 03/24/17
#       -Added support for ION Storm format.
#       -Added support for ION Polytype and Polyflag matertial naming scheme.
#       -Modified reading of the texture slots space in the material names to allow up to 256 (0-255) texture slots.
#       -Added RATE= for sequences in .uc file based on scene fps setting.
#       -Set an initial rotation in the .uc file to rotate the mesh 90 degrees to make Blender's front also the front in Unreal.
#       -Added folder settings for use with ucc -make.
#       -Made the selection for Actions or Scene Timeline a list instead of a bool.
#       -Vertex coordinates are now rounded instead of truncated.
#       -Vertex coordinates are now clamped to move any vertices outside the 255*255*255 range to the borders instead of a random location.
#       -Fixed crashing when exporting meshes with no materials or empty first texture slot.
#
#   0.9.0 - 03/21/17 
#       -Initial release.

#======================================================================

bl_info = {
    "name": "Unreal Engine 1 Vertex Mesh Format",
    "author": "Skywolf",
    "version": (1, 3, 7),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "description": "Export and import _a.3d and _d.3d files",
    "warning": "",
    "wiki_url": "http://www.oldunreal.com/wiki/index.php?title=Main_Page",
    "support": 'COMMUNITY',
    "category": "Import-Export"}
    
import bpy
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        CollectionProperty,
        IntProperty
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        )

class ImportUnrealVertexMesh(bpy.types.Operator, ImportHelper):
    """Import from .3d file format (.3d)"""
    bl_idname = "import_unreal_vertex_mesh.3d"
    bl_label = 'Import Unreal vertex mesh'
    
    filename_ext = ".3d"
    filter_glob: StringProperty(
            default="*.3d",
            options={'HIDDEN'},
            )

    i_anim: BoolProperty(
        name="Import Animation",
        description="Import Animation. If unchecked it will only import the given frame",
        default=True,
        )

    a_format: EnumProperty(
        name = "Format",
        items=(("AUTO", "Automatic", "Automatically detects the format"),
               ("UNREAL", "Standard", "Standard format used by most Unreal Engine 1 games"),
               ("ION", "ION Storm", "Modified format used by ION Storm games (Deus Ex)"),
               ))        
               
    i_matt: BoolProperty(        
        name="Create Materials",
        description="Wether to create materials with correct naming for exporting",
        default=True,
        )
        
    i_scale: FloatProperty(
        name = "Scale",
        description="Scaling of the imported model. It's not uncommon for Unreal meshes to be rather large. This allows the model to be scaled down",
        default = 1,
        )
        
    frame_start: IntProperty(
        name="From frame",
        default=1,
        min=1,
        )

    frame_end: IntProperty(
        name="To frame",
        description="Set to 0 for all frames. If this value is higher than the number of animation frames in the _a.3d file the end frame will be that last frame instead",
        default=0,
        min=0,
        )

    frame_single: IntProperty(
        name="Frame",
        description="If this value is higher than the number of animation frames in the _a.3d file the last frame will be imported instead",
        default=1,
        min=1,
        )

        
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "i_scale")
        layout.prop(self, "i_anim")
        if self.i_anim:
            layout.prop(self, "frame_start")
            layout.prop(self, "frame_end")
        else:
            layout.prop(self, "frame_single")
        layout.separator()
        layout.prop(self, "a_format")
        layout.prop(self, "i_matt")

    def execute(self, context):
        from . import import_unreal_3d
        
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "check_existing",
                                            ))
                                    
        return import_unreal_3d.load(self, context, **keywords)
        
        
class ExportUnrealVertexMesh(bpy.types.Operator, ExportHelper):
    """Export to .3d file format (.3d)"""
    bl_idname = "export_unreal_vertex_mesh.3d"
    bl_label = 'Export Unreal vertex mesh'
    
    filename_ext = ".3d"
    filter_glob: StringProperty(
            default="*.3d",
            options={'HIDDEN'},
            )

    e_anim: BoolProperty(
        name="Animation file (_a.3d)",
        description="Export vertex animation file",
        default=True,
        )
        
    a_format: EnumProperty(
        name = "Format",
        items=(("UNREAL", "Standard", "Standard format used by most Unreal Engine 1 games"),
               ("ION", "ION Storm", "Modified format used by ION Storm games (Deus Ex)"),
               ))
                   
    a_source: EnumProperty(
        name = "Source",
        items=(("ACTIONS", "Actions", "Get animations from Actions. Be sure to have all Objects affecting the Mesh selected with the Mesh as the Active Object (selected last)"),
               ("SCENE", "Scene Timeline", "Get animation from the current scene timeline. Be sure to only select the Mesh"),
               ))
               
    e_scale: FloatProperty(
        name = "Scale",
        description="Scale of the exported model. Increasing this will allow for higher detail but setting this too high will cause the model to get squished when it goes too far outside the boundries. \n The model should still fit within 256 x 256 Blender units after this scale is applied",
        default = 1,
        )
    
    e_data: BoolProperty(
        name="Data file (_d.3d)",
        description="Export vertex data file containing polygon flags .etc",
        default=True,
        )
    
    e_uc: BoolProperty(
        name="Unreal script (.uc)",
        description="Makes an Unreal script file with #exec commands to import the mesh using ucc -make",
        default=True,
        )
        

    lod: BoolProperty(
        name="Make mesh a LODMesh.",
        description="Wether the mesh will be a LODMesh (geometry collapses if the player is far enough from the mesh)",
        default=True,
        )

    lod_style: IntProperty(
        name="LODSTYLE",
        description="1: Value curvature over length.\n2: Protect the edges of doublesided polygons - like the CTF flags.\n4: Try to respect texture seams more. Use this if there is too much 'stretching' going on.\n8: Value length over curvature. Needed for unwelded, multi-element, or otherwise 'open' meshes.\n16: Translucent polygons will be collapsed less early in the LOD sequence.\n\nOptions can be combined by adding together the desired values",
        default=10,
        min=0, max=31,
        )
        
    lod_frame: IntProperty(
        name="LODFRAME",
        description="Animation frame used for generating the LOD collapse sequence",
        default=0,
        min=0,
        )      
        
    e_to_folders: BoolProperty(
        name="Export to ucc folder structure",
        description="Export to folders in the currently selected directory for ucc -make. Also affects the class (.uc) file. If a folder doesn't exist it will be created",
        default=False,
        )
        
    modeldir: StringProperty(
        name="Data File Folder",
        description="Folder to write the data (_d.3d) file to",
        default="Models",
        )
        
    animdir: StringProperty(
        name="Animation File Folder",
        description="Folder to write the animation (_a.3d) file to",
        default="Models",
        )
        
    classdir: StringProperty(
        name="Classes Folder",
        description="Folder to write the class (.uc) file to",
        default="Classes",
        )
        
    texdir: StringProperty(
        name="Textures Folder",
        description="Folder to where the Textures are stored. Used for the .uc file",
        default="Textures",
        )   

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "e_anim")
        layout.prop(self, "a_format")
        layout.prop(self, "a_source")
        layout.prop(self, "e_scale")
        layout.prop(self, "e_data")
        layout.prop(self, "e_uc")
        if self.e_uc:
            layout.prop(self, "lod")
            if self.lod:
                layout.prop(self, "lod_style")
                layout.prop(self, "lod_frame")              
        layout.separator()
        layout.prop(self, "e_to_folders")
        
        if self.e_to_folders:
            layout.prop(self, "modeldir")
            layout.prop(self, "animdir")
            layout.prop(self, "classdir")
            layout.prop(self, "texdir")

        
    def execute(self, context):
        from . import export_unreal_3d
        
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "check_existing",
                                            ))
                                    
        return export_unreal_3d.save(self, context, **keywords)

# Add to a menu
def menu_func_export(self, context):
    self.layout.operator(ExportUnrealVertexMesh.bl_idname, text="Unreal Engine Vertex Mesh (_a.3d, _d.3d)")

def menu_func_import(self, context):
    self.layout.operator(ImportUnrealVertexMesh.bl_idname, text="Unreal Engine Vertex Mesh (_a.3d, _d.3d)")

def register():
    bpy.utils.register_class(ExportUnrealVertexMesh)
    bpy.utils.register_class(ImportUnrealVertexMesh)
    
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ExportUnrealVertexMesh)
    bpy.utils.unregister_class(ImportUnrealVertexMesh)

    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
