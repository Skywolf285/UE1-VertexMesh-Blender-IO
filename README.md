# UE1-VertexMesh-Blender-IO
Exporter and importer for the Unreal Engine 1 _a.3d and _d.3d vertex mesh format for Blender. Also has support for ION Storm's variant of the format (Which has a higher vertex precision but cuts the max vertices in half).

## Installation
On Github, Under **releases** (on the right) click on the latest one. Then click on **io_u_vertex_m.zip** under assets and save this file somewhere.

Then open Blender and go to the **Edit** drop down menu on the top left, select **Preferences...**. Click the **Add-ons** tab on the left and click **install...**. Select the .zip file you just downloaded. Enter *Unreal* in the search field in the top right and make sure **Unreal Engine 1 Vertex Mesh Format** is enabled.

## Usage
When exporting you have two options to pick whether it should use Actions or just the scene timeline for animation data. Using Actions is easier to work with while using the Timeline allows for things like Keyframes and the NLA editor (Non Linear Action editor) to be used.

Down side is that when using the timeline method you won't be getting a .uc file with all the animation data filled in for you. Just an ALL and Still sequence. The others will have to be entered by hand.

For the best results set the fps under render settings to something lower than the default 24fps and base your animations on that. Around 10-15 should be fine. Setting it higher will just give you larger file sizes while making the animations look worse as well. Keep in mind that this doesn't affect the rate at which the animations are played back in Unreal.

### Polytypes Polyflags and Texnum
**Polytypes**, **Polyflags** and **texnum** are handled by material name The material should start with a three digits containing a number between 0 and 255 (if not it will use Blender's material index instead) which is the **texnum**. After this you can add one of the following **Polytypes** (case sensitive):

- `_NOMRAL/_NM` = The default. Used if none of these are given.
- `_2SIDED/_DD` = **2-sided**
- `_TRANSLUCENT/_LU` = **translucent** and **2-sided**
- `_MASKED/_CL` = **masked* and **2-sided**
- `_MODULATED/_MD` = **modulated** and **2-sided**
- `_ALPHABLEND/_AB` = **alphablend* and **2-sided** (Supported by OldUnreal's Unreal 227 patch only).
- `_WEAPONTRI/_PH` = makes this polygon a **weapon triangle** (used to place the weapon in 3rd person view).

You can also add these **Polyflags** to the name. Unlike **Polytypes** can you have more than one of these at the same time (also case sensitive):

- `_UNLIT/_UL` = **Unlit**.
- `_FLAT/_FL` = Not really sure to be honest. Probably related to the mesh curvy thingy.
- `_ENVIRONMENT/_RF` = Render this poly to make it look **shiny/reflective**.
- `_NOSMOOTH/_NS` = **No texture smoothing** (see: Minecraft)

Example: The following name would make the polygons assigned to this material **translucent**, **unlit** and **shiny/reflective** while using texture slot 0:

    000_UL_TRANSLUCENT_ENVIRONMENT_

Note how the order of the flags don't matter. The only thing that has a specific spot in the name is the texture number.

You can have different flags for different polygons while still make them use the same texture slot. So lets say I make another one and name it like this:

    000_MD_2SIDED_

Would it use the same texture slot while making these polygons **modulated** and **2-Sided**.

The texture name (used for the .uc file) is read from the currently active (selected) **Image Texture** node in the material.

## Limitations
Unreal Engine 1's vertex model format has a few inherit limiation and oddities when interacting with Blender's way of doing things.

- There is a vertex (note vertex. not polygons) limit of 16383 dictated by the animation file (8191 for ION Storm's format).
- Always keep your vertices within 255x255x255 units. -128 to 127 Blender units on each axis. Any vertices that are/move outside this will be clamped.
- Cooridinates have a limited resolution of 2048x2048x1024 within this (65535x65535x65535 for ION Storm's format).
- You **can't** have the vertex count of your mesh change during an animation. Doing so will break the animation. The exporter throws and exception in the event it detects this to avoid unexpected results.
- UVs snap to a 256 to 256 grid. Anything outside the 0-1 UV grid in Blender gets clamped.
- Unreal snaps to the center of the 256x256 UV coordinates while Blender snaps inbetween pixels. This means that, when snapping to the pixels on a 256x256 resolution texture, you technically have 258x258 possible coordinates. This difference results on a slight offset in the UVs and the outer edge of the UV range getting clamped by a small amount.
