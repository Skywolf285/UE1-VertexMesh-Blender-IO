#   V1.3.5

import bpy
import bmesh
import os
import ntpath


#=======================================================================
# Polygon flags tuples.
#=======================================================================
polytype =   (("_NORMAL", "_NM", 0),
             ("_2SIDED", "_DD", 1),
             ("_TRANSLUCENT", "_LU", 2),
             ("_MASKED", "_CL", 3),
             ("_MODULATED", "_MD", 4),
             ("_ALPHABLEND", "_AB", 5),
             ("_WEAPONTRI", "_PH", 8))
             
polyflags =  (("_UNLIT", "_UL", 16),
             ("_FLAT", "_FL", 32),
             ("_ENVIRONMENT", "_RF", 64),
             ("_NOSMOOTH", "_NS", 128))
             



#print (baseob.data.vertices[0].co)

def corcoords (val, mult, SCALE):
    if val * SCALE < -128: 
        return -128 * mult
    if val * SCALE > 127: 
        return 127 * mult
    
    return int(round(val * mult * SCALE, 0))


def range2anim (range_min, range, FORMAT, SCALE):
    Fmax = 0
    r2a_out = []
    vertcount = len(baseob.evaluated_get(dgraph).to_mesh().vertices)
    for frame in range:
        bpy.context.scene.frame_set (range_min+Fmax)
        Fmax += 1
        
        animmesh = baseob.evaluated_get(dgraph).to_mesh()
        
        if len(animmesh.vertices) != vertcount:
            raise Exception ("Error: Number of vertices changed between frames. This is not supported in Unreal Engine's animation format and break animations. Aborting...")
        
        if FORMAT == "UNREAL":
            for verts in animmesh.vertices:
                co = ((corcoords(verts.co[0], 8, SCALE) & 0x7ff))
                
                co += (((corcoords((verts.co[1]*-1), 8, SCALE) & 0x7ff) << 11)) # Unreal's y axis is inverted from Blender's.
                
                co += ((corcoords(verts.co[2], 4, SCALE) & 0x3ff) << 22)
                
                r2a_out.append ((co).to_bytes(4, 'little'))

        elif FORMAT == "ION":
            for verts in animmesh.vertices:
                
                co = ((corcoords(verts.co[0], 256, SCALE) & 0xffff))
                r2a_out.append ((co).to_bytes(2, 'little'))
                co = ((corcoords((verts.co[1]*-1), 256, SCALE) & 0xffff)) # Unreal's y axis is inverted from Blender's.
                r2a_out.append ((co).to_bytes(2, 'little'))
                co = ((corcoords(verts.co[2], 256, SCALE) & 0xffff))
                r2a_out.append ((co).to_bytes(2, 'little'))
                r2a_out.append ((0).to_bytes(2, 'little'))

                #co = ((corcoords(verts.co[0], 256) & 0xffff))
                
                #co += (((corcoords((verts.co[1]*-1), 256) & 0xffff) << 16)) # Unreal's y axis is inverted from Blender's.
                
                #co += ((corcoords(verts.co[2], 256) & 0xffff) << 32)
                
                #r2a_out.append ((co).to_bytes(6, 'little'))               
                #r2a_out.append ((0).to_bytes(2, 'little'))
         
 
    else:
        bpy.context.scene.frame_set(range_min)
        return r2a_out

def prep_data ():
    data = []
    meshcolor = (0).to_bytes(1, 'little') #unused
    texnum = 0
    unusedflags = (0).to_bytes(1, 'little') #unused
    mnlist = []
    mattdata = []
    texdata = []
    notex = ""
    
    tnums = []
    for id, matt in enumerate(me.materials): #Getting material data and setting texnum..
        meshtype = 0
        
        if matt.name[0:3].isdigit(): #Reading texnum from materials.
            if int(matt.name[0:3]) <= 255: #Max of 256 (0-255 supported).
                texnum = int(matt.name[0:3])
            else:
                texnum = 0
        elif id <= 255:
            texnum = id
        else:
            texnum = 0
            
        for i in polytype: #Compares strings from polytype with material name.
            if i[0] in matt.name or i[1] in matt.name:
                meshtype = i[2]
                break #Can only have one polytype at the same time.
        for i in polyflags: #Compares strings from polyflags with material name.
            if i[0] in matt.name or i[1] in matt.name:
                meshtype += i[2]
        
        mattdata.append ([texnum, meshtype])
        if texnum not in tnums: #To prevent dulpicates when writing .uc file.
            if matt.node_tree != None and matt.node_tree.nodes.active.type == 'TEX_IMAGE' and matt.node_tree.nodes.active.image != None:
                texdata.append ([texnum, matt.node_tree.nodes.active.image.name])
            else:
                texdata.append ([texnum, "Texture"])
            tnums.append (texnum)
        
    if mattdata == []:
        mattdata = [[0, 0]] #For when no materials are assigned.
        
    for polys in me.polygons:
        
        v = []
        uv = []
        meshtype = 0
        
        mi = polys.material_index
        
        texnum = (mattdata[mi][0]).to_bytes(1, 'little')
                
        meshtype = (mattdata[mi][1]).to_bytes(1, 'little')
        
        
        for i in polys.loop_indices: #reading uvs.
            if me.uv_layers.active != None:
                uvl = me.uv_layers.active
                #for n, uvl in enumerate(me.uv_layers):
                tempuv = [int((uvl.data[me.loops[i].index].uv[0]+(1/255))*255), #add offset of 1 pixel 
                abs(int(uvl.data[me.loops[i].index].uv[1]*255)-255)] #Unreal V coords are the inverse of Blender's
                #tempuv = [int(round((uvl.data[me.loops[i].index].uv[0]*256))), 
                #          int(round((uvl.data[me.loops[i].index].uv[1]*-256)))] #Unreal V coords are the inverse of Blender's
                for i, i2 in enumerate (tempuv):
                    if i2 < 0:
                        tempuv[i] = 0
                    if i2 > 255:
                        tempuv[i] = 255
                                
            else: 
                tempuv = [0,0]                    
            uv.append ([(tempuv[0]).to_bytes(1, 'little'), (tempuv[1]).to_bytes(1, 'little')])
            
            
        for verts in polys.vertices:
            v.append((verts).to_bytes(2, 'little'))
            #print (me.vertices[verts].co)

            #uv.append(int(me.uv_layers.active.data[verts].uv[0]*255).to_bytes(1, 'little'))
            #uv.append(int(me.uv_layers.active.data[verts].uv[1]*255).to_bytes(1, 'little'))

            
        else:

            data.append(v[0])
            data.append(v[2])
            data.append(v[1])
            data.append(meshtype)
            data.append(meshcolor)
            if uv != []:
                data.extend(uv[0])
                data.extend(uv[2])
                data.extend(uv[1])
            else:
                #print ("Model has no UV data: Adding Padding data and setting LODNOTEX=True for .uc file.")
                data.extend([(0).to_bytes(3, 'little')])
                notex = "LODNOTEX=True"
                
            data.append(texnum)
            data.append(unusedflags)
            
            
    else:
        return data, texdata, notex
    
    
def prep_anim (ANIMSOURCE, FORMAT, SCALE):
    ucdata = []
    ucframe = 0
    anim = []
    
    print (me.vertices)
    
    if ANIMSOURCE == "ACTIONS":
        for action in bpy.data.actions:
            if not len(action.fcurves): #check if action has keyframes. If not then it will be skipped.
                print ("No keyframes in",action.name,", skipping.")
                continue
            
            single_key_check = 1
            for fcu in action.fcurves:
                single_key_check *= len(fcu.keyframe_points) #Equals 1 if action has only 1 set of keyframes.
                
            
            for ob in bpy.context.selected_objects:
                if ob.animation_data == None:
                    raise Exception("Error: One of the selected objects doesn't have animation data. Aborting...")
                ob.animation_data.action = action

            framemin, framemax = action.frame_range
            range_min = int(framemin)
            range_max = int(framemax+1)
             
            if single_key_check == 1:
                range_max = 1 # To allow a sequence with one keyframe to have only 1 frame.
                
            tot_frames = (range_max - range_min)            
            action_range = range(range_min, range_max)

            ucst = ucframe

            r2a_out = range2anim(range_min, action_range, FORMAT, SCALE)
            anim.extend (r2a_out)     
                 
            ucdata.append ([action.name, ucst, tot_frames])
            ucframe += tot_frames
            #print (ucdata)
        else:
            return anim, ucdata, ucframe
    elif ANIMSOURCE == "SCENE": #Use scene frames
    
        
        range_min = bpy.context.scene.frame_start
        range_max = bpy.context.scene.frame_end + 1
        scene_range = range(range_min, range_max)
        tot_frames = (range_max - range_min)
        

        anim = range2anim(range_min, scene_range, FORMAT, SCALE)
        ucdata = None
        
        return anim, ucdata, tot_frames
            
  
           


def write_files (context, filepath, EXPORT_DATA, EXPORT_ANIM, FORMAT, ANIMSOURCE, SCALE, EXPORT_UC, USE_FOLDERS, MODELDIR, ANIMDIR, UCDIR, TEXDIR, LOD, LODSTYLE, LODFRAME):
    ucframe = 0
    ucdata = None
    texdata = None
    notex = ""
    
    global baseob 
    baseob = bpy.context.active_object
    
    global dgraph
    dgraph = bpy.context.evaluated_depsgraph_get()

    if baseob.type != 'MESH':
        raise Exception("Error: Selected object is not a mesh. Aborting...")

    global me
    me = baseob.evaluated_get(dgraph).to_mesh()

    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    
    
    
    datapath = os.path.splitext(filepath)[0] + "_d" + os.path.splitext(filepath)[1] #Data file path.
    if USE_FOLDERS:
        newdir = os.path.join(os.path.split(datapath)[0], MODELDIR)
        
        if not os.path.exists (newdir):
            os.makedirs(newdir)
            
        datapath = os.path.join(newdir, os.path.split(datapath)[1])
            
            
    animpath = os.path.splitext(filepath)[0] + "_a" + os.path.splitext(filepath)[1] #Animation file path.
        
    if USE_FOLDERS:
        newdir = os.path.join(os.path.split(animpath)[0], ANIMDIR)
        
        if not os.path.exists (newdir):
            os.makedirs(newdir)
            
        animpath = os.path.join(newdir, os.path.split(animpath)[1])
            
    
    if EXPORT_DATA:
        data, texdata, notex = prep_data()

        with open (datapath, 'w+b') as d:
            print ("Writing {n}...".format(n=datapath))
            numpolys = (len(me.polygons)).to_bytes(2, 'little')
            numverts = (len(me.vertices)).to_bytes(2, 'little')
            unusedrot = (0).to_bytes(2, 'little')
            unusedframe = (0).to_bytes(2, 'little')
            unusednormx = (0).to_bytes(4, 'little')
            unusednormy = (0).to_bytes(4, 'little')
            unusednormz = (0).to_bytes(4, 'little')
            unusedscale = (0).to_bytes(4, 'little')
            genunused = (0).to_bytes(12, 'little')
            moreunused = (0).to_bytes(12, 'little')
            
            header = [numpolys, 
                      numverts, 
                      unusedrot, 
                      unusedframe, 
                      unusednormx, 
                      unusednormy, 
                      unusednormz, 
                      unusedscale, 
                      genunused,
                      moreunused]
            for i in header: #Write header
                d.write (i)
            
            for i in data: #Write data
                d.write (i)
            print ("{n} created successfully.".format(n=datapath))
                
                
    if EXPORT_ANIM:
        anim, ucdata, ucframe = prep_anim(ANIMSOURCE, FORMAT, SCALE)
        me = baseob.to_mesh() #fixes "structRNA of type Mesh has been removed" error
        
        if FORMAT == "UNREAL":
            fsize = 4
        elif FORMAT == "ION":
            fsize = 8
        
        with open (animpath, 'w+b') as a:
            print ("Writing {n}...".format(n=animpath))
            header = [(ucframe).to_bytes(2, 'little'),
                      (len(me.vertices) * fsize).to_bytes(2, 'little')]
            for i in header: #Write header
                a.write (i)
                
            for i in anim: #Write animations
                a.write (i)
                
            print ("{n} created successfully.".format(n=animpath))
                
                
    if EXPORT_UC:
        ucpath = os.path.splitext(filepath)[0] + ".uc"
        
        if USE_FOLDERS:
            newdir = os.path.join(os.path.split(ucpath)[0], UCDIR)
            
            if not os.path.exists (newdir):
                os.makedirs(newdir)
                
            ucpath = os.path.join(newdir, os.path.split(ucpath)[1])
            
            
        with open (ucpath, 'w', encoding = 'utf-8') as uc:
            print ("Writing {n}...".format(n=ucpath))
            uc.write ("//=============================================================================\n")
            uc.write ("// {on}.\n".format(on=os.path.splitext(os.path.basename(filepath))[0]))
            uc.write ("//=============================================================================\n")
            uc.write ("class {on} expands actor;\n".format(on=os.path.splitext(os.path.basename(filepath))[0]))
            uc.write ("\n")
            if LOD:
                ld = ("LODSTYLE={LS} LODFRAME={LF}".format(LS=str(LODSTYLE), LF=str(LODFRAME)))
            else:
                ld = ("MLOD={L}".format(L=str(LOD)))
            uc.write ("#exec MESH IMPORT MESH={on} ANIVFILE={ad}\{af} DATAFILE={md}\{df} X=0 Y=0 Z=0 {ld} {noT}\n".format(on=baseob.name,af=ntpath.basename(animpath), df=ntpath.basename(datapath), ad=ANIMDIR, md= MODELDIR, noT=notex, ld=ld))
            uc.write ("#exec MESH ORIGIN MESH={on} X=0 Y=0 Z=0 YAW=-64 PITCH=0 ROLL=0\n".format(on=baseob.name)) #Adjust rotation.
            uc.write ("\n")
            uc.write ("#exec MESH SEQUENCE MESH={on} SEQ=ALL    STARTFRAME=0 NUMFRAMES={f} RATE={r}\n" .format(on=baseob.name, f=ucframe, r=bpy.context.scene.render.fps))
            uc.write ("#exec MESH SEQUENCE MESH={on} SEQ=Still    STARTFRAME=0 NUMFRAMES=1 RATE={r}\n" .format(on=baseob.name, r=bpy.context.scene.render.fps))
            
            if ucdata != None: #Can only do this if anim file is based on actions.
                for allanim in ucdata:
                    uc.write ("#exec MESH SEQUENCE MESH={on} SEQ={a[0]}    STARTFRAME={a[1]} NUMFRAMES={a[2]} RATE={r}\n" .format(on=baseob.name, a=allanim, r=bpy.context.scene.render.fps))
                
            uc.write ("\n")
            uc.write ("#exec MESHMAP NEW MESHMAP={on} MESH={on}\n".format(on=baseob.name))
            if FORMAT == 'UNREAL':
                uc.write ("#exec MESHMAP SCALE MESHMAP={on} X=0.1 Y=0.1 Z=0.2\n".format(on=baseob.name))
            elif FORMAT == 'ION':
                uc.write ("#exec MESHMAP SCALE MESHMAP={on} X=0.003125 Y=0.003125 Z=0.003125\n".format(on=baseob.name)) #Ion Storm format requires different scaling.
                
            if texdata != None:
                for tn in texdata:
                    if os.path.splitext(tn[1])[1].lower() != "bmp":
                        tfn = os.path.splitext(tn[1])[0] + ".PCX" #support both PCX and BMP.
                    uc.write ("\n")
                    uc.write ("#exec TEXTURE IMPORT NAME={t[1]} FILE={td}\{tf} GROUP=Skins FLAGS=2\n".format(t=tn, tf=tfn, td=TEXDIR))
                    uc.write ("#exec MESHMAP SETTEXTURE MESHMAP={on} NUM={t[0]} TEXTURE={t[1]}\n".format(on=baseob.name, t=tn))
                
            uc.write ("\n")
            uc.write ("defaultproperties\n")
            uc.write ("{\n")
            uc.write ("    DrawType=DT_Mesh\n")
            uc.write ("    Mesh={on}\n".format(on=baseob.name))
            uc.write ("}")
            print ("{n} created successfully.".format(n=ucpath))
    baseob.to_mesh_clear()


def save (operator, context, filepath="", e_anim=False, a_format="UNREAL", a_source="ACTIONS", e_scale=1, e_data=False, e_uc=False, e_to_folders = False, modeldir = "Models", animdir = "Models", classdir = "Classes", texdir = "Textures", lod = True, lod_style = 10, lod_frame = 0):

    write_files(context, filepath, e_data, e_anim, a_format, a_source, e_scale, e_uc, e_to_folders, modeldir, animdir, classdir, texdir, lod, lod_style, lod_frame)
                
    return {'FINISHED'}
