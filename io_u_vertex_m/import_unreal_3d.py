#   V1.3.5
import bpy, bmesh, sys, os

bDebug = False #print more information (much slower)

#Unreal fsize = 4
#DX dsize = 8

#Constants:
polysize = 16
dheadersize = 48

aheadersize = 4
def ofprint (var, sep, var2):
    if bDebug:
        out = "%d %s %d" % (var, sep, var2)
        sys.stdout.write('\r' + ' '*len(out))
        sys.stdout.write('\r')
        sys.stdout.flush()
        sys.stdout.write(out)
        sys.stdout.flush() 
            
def unsign (i):
    if i >= 128:
        return i - 256      
    else:
        return i
    
#Data file:            
def get_data_header (DATAFILE):
    #Header
    polycount = int.from_bytes(DATAFILE[0:2], 'little')
    vertcount = int.from_bytes(DATAFILE[2:4], 'little')
    unusedrot = int.from_bytes(DATAFILE[4:6], 'little')
    unusedframe = int.from_bytes(DATAFILE[6:8], 'little')
    unusednormx = int.from_bytes(DATAFILE[8:12], 'little')
    unusednormy = int.from_bytes(DATAFILE[12:16], 'little')
    unusednormz = int.from_bytes(DATAFILE[16:20], 'little')
    unusedscale = int.from_bytes(DATAFILE[20:24], 'little')
    genunused = int.from_bytes(DATAFILE[24:36], 'little')
    moreunused = int.from_bytes(DATAFILE[36:48], 'little')
    
    return polycount, vertcount

    
def get_data_polys (DATAFILE, pi):
    vertindex = []
    for i in range(3):
        vertindex.append(int.from_bytes(DATAFILE[dheadersize+(polysize*pi)+(i*2):dheadersize+(polysize*pi)+(i*2)+2], 'little'))
    
    polyflags = DATAFILE[dheadersize+(polysize*pi+6)]
    meshcolor = DATAFILE[dheadersize+(polysize*pi+7)] #unused
    
    uvs = []
    for v in range(3): #Vertices
        tempuvs = []
        for uv in range(2): #uvs
            tempuvs.append(DATAFILE[dheadersize+(polysize*pi)+8+(v*2)+uv])
        uvs.append(tempuvs)
        
    texnum = DATAFILE[dheadersize+(polysize*pi+14):dheadersize+(polysize*pi+15)]
    unusedflags = DATAFILE[dheadersize+(polysize*pi+15):dheadersize+(polysize*pi+16)]
    
    return vertindex, polyflags, uvs, texnum
    

def assign_materials (texnum, polyflags, ob, name):
    mtname = str(int.from_bytes(texnum, 'little'))
    mtname = ("0"*(3-len(mtname)))+mtname
    
    if (polyflags & 0xF) == 1: mtname+="_2SIDED"
    elif (polyflags & 0xF) == 2: mtname+="_TRANSLUCENT"
    elif (polyflags & 0xF) == 3: mtname+="_MASKED"
    elif (polyflags & 0xF) == 4: mtname+="_MODULATED"
    elif (polyflags & 0xF) == 5: mtname+="_ALPHABLEND"
    elif (polyflags & 0xF) == 8: mtname+="_WEAPONTRI"
    else: mtname+="_NORMAL"
    
    if ((polyflags >> 4) & 0x1) == 1: mtname+="_UNLIT"
    if ((polyflags >> 5) & 0x1) == 1: mtname+="_FLAT"
    if ((polyflags >> 6) & 0x1) == 1: mtname+="_ENVIRONMENT"
    if ((polyflags >> 7) & 0x1) == 1: mtname+="_NOSMOOTH"
    
    mtname+="_"
    mtname+=name
    
    
    if mtname in ob.data.materials:
        i = 0
        for m in ob.data.materials:
            if m.name == mtname:
                break
            i+=1
        return i
    else:
        if mtname in bpy.data.materials:
            for m in bpy.data.materials:
                if m.name == mtname:
                    ob.data.materials.append(m)
                    break
        else:
            mt = bpy.data.materials.new(mtname)
            ob.data.materials.append(mt)
            
        return len(ob.data.materials)-1
    
    
#Animation File:    
def get_anim_header (ANIMFILE):
    numframes = int.from_bytes(ANIMFILE[0:2], 'little')
    framesize = int.from_bytes(ANIMFILE[2:4], 'little')
    
    return numframes, framesize
    
    
def get_anim_coords(ANIMFILE, frame, vertex_index, framesize, FORMAT):
            
    coords = []
    if FORMAT == "UNREAL":
        bytes = int.from_bytes(ANIMFILE[aheadersize+(frame*framesize)+(vertex_index*4):aheadersize+(frame*framesize)+(vertex_index*4+4)], 'little')
        coords.append(unsign((bytes & 0x7ff)/8))
        coords.append(unsign(((bytes >> 11) & 0x7ff)/8)*-1) #Unreal's Y axis is inverted from Blender's
        coords.append(unsign(((bytes >> 22) & 0x3ff)/4))
            
    elif FORMAT == "ION":
        address = aheadersize+(frame*framesize)+(vertex_index*8)
        
        coords.append(unsign((int.from_bytes(ANIMFILE[address:address+2], 'little'))/256))
        coords.append(unsign((int.from_bytes(ANIMFILE[address+2:address+4], 'little'))/256)*-1) #Unreal's Y axis is inverted from Blender's
        coords.append(unsign((int.from_bytes(ANIMFILE[address+4:address+6], 'little'))/256))
        
    return coords
    


def make_mesh(PATH, IM_ANIM, FORMAT, IM_MATT, SCALE, A_START, A_END, FRAME):
    #Creating proper paths for both files
    if PATH[-5:] == "_d.3d" or PATH[-5:] == "_a.3d":
        datapath = PATH[:-5] + "_d.3d"
        animpath = PATH[:-5] + "_a.3d"
        modelname = os.path.split(PATH[:-5])[1]
    else:
        datapath = os.path.splitext(PATH)[0] + "_d.3d"
        animpath = os.path.splitext(PATH)[0] + "_a.3d"
        modelname = os.path.splitext(os.path.split(PATH)[1])[0]
    
    print ("Opening data file:", datapath)
    dfile = open(datapath, "r+b")    
    DATAFILE = dfile.read()

    print ("Opening animation file:", animpath)
    afile = open(animpath, "r+b")
    ANIMFILE = afile.read()
    
    scene = bpy.context.scene
    col = bpy.data.collections.new(modelname)
    
    me = bpy.data.meshes.new(modelname)
    ob = bpy.data.objects.new(modelname, me)
    
    bm = bmesh.new()
    bm.from_mesh(me)
    
    scene.collection.children.link(col)
    
    bpy.data.collections[modelname].objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)
    
    #Data
    polycount, vertcount = get_data_header(DATAFILE)
    
    print ("\nCreating vertices...")
    for v in range(vertcount): #create vertices
        bm.verts.new ()
        ofprint(v+1, "of", vertcount)

    bm.verts.ensure_lookup_table()
    
    uv_layer = bm.loops.layers.uv.verify()
    #bm.faces.layers.tex.verify()
    
    print ("\n\nCreating polygons...")
    for p in range(polycount): #create polygons
        vertindex, polyflags, uvs, texnum = get_data_polys(DATAFILE,p)
        try: 
            polygon = bm.faces.new((bm.verts[vertindex[0]], bm.verts[vertindex[1]], bm.verts[vertindex[2]]))
        except ValueError as e: 
            #Some meshes have multiple polygons that share the same vertices which causes a ValueError. Blender has no support having three vertices contain two polygons. So we skip creating these.
            print('\nError on polygon',str(p+1)+':', e, ', Skipping.')
            continue
            
        polygon.smooth = True
        if IM_MATT:
            polygon.material_index = assign_materials(texnum, polyflags, ob, modelname)
        
        for i, loop in enumerate(polygon.loops):
            uv = loop[uv_layer].uv
            uv[0] = uvs[i][0]/256
            uv[1] = ((uvs[i][1]/256)*-1)+1
       
        ofprint(p+1, "of", polycount)
    
    
    #Animation
    numframes, framesize = get_anim_header(ANIMFILE)
    if IM_ANIM:
        if A_START-1 <= numframes:
            frame = A_START-1
        else:
            frame = numframes
    elif FRAME-1 <= numframes:
        frame = FRAME-1
    else:
        frame = numframes
    
    if FORMAT == "AUTO":
        fsize = framesize/vertcount
        if fsize == 4:
            FORMAT = "UNREAL"
            print ("Animation format auto detected as UNREAL.")
        elif fsize == 8:
            FORMAT = "ION"
            print ("Animation format auto detected as ION STORM.")
        else:
            raise Exception("Error: Unable to detect animation format. Aborting...")
            
    print ("\n\nMoving vertices to frame", str(frame)+"...")
    for v in range(len(bm.verts)):
        coords = get_anim_coords(ANIMFILE, frame, v, framesize, FORMAT)
        #print ("coords=", coords)
        coords = [c*SCALE for c in coords]
        bm.verts[v].co = (coords)
        ofprint (v+1, "of", len(bm.verts))
    
    bm.normal_update()
    bpy.ops.object.mode_set(mode='OBJECT', toggle = False)
    bm.to_mesh(me)
    
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)
    bpy.ops.mesh.select_all(action='SELECT')
    #bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode='OBJECT', toggle = False)
    bm.free()
    

    if IM_ANIM == True and numframes > 1: #Importing Animation
        print ("\n\nImporting Animation...")
        if A_END == 0 or A_END > numframes:
            A_END = numframes
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = A_END-A_START
        for frame in range(A_START-1, A_END):
            keyname = 'Frame'+str(frame-A_START+1)
            ob.shape_key_add(name=keyname, from_mix=False)
            
            me = ob.data
            bm = bmesh.new()
            bm.from_mesh(me)
            shape = bm.verts.layers.shape.get(keyname)
            bm.verts.ensure_lookup_table()
            
            for v in range(len(bm.verts)):
                coords = get_anim_coords(ANIMFILE, frame, v, framesize, FORMAT)
                coords = [c*SCALE for c in coords]
                bm.verts[v][shape]= (coords)
                if bDebug:
                    out = "Adding Frame %d of %d. Vertice %d of %d." % (frame+1, A_END-A_START+1, v+1, len(bm.verts))
                    sys.stdout.write('\r' + ' '*len(out))
                    sys.stdout.write('\r')
                    sys.stdout.flush()
                    sys.stdout.write(out)
                    sys.stdout.flush() 
                
            bm.to_mesh(me)
            bm.free()
            ob.data.shape_keys.key_blocks[keyname].interpolation = 'KEY_LINEAR'
            # ob.data.shape_keys.key_blocks[keyname].keyframe_insert("value",frame=frame-A_START+2) #old code using Relative Shape keys.
            # ob.data.shape_keys.key_blocks[keyname].keyframe_insert("value",frame=frame-A_START)
            # ob.data.shape_keys.key_blocks[keyname].value = 1
            # ob.data.shape_keys.key_blocks[keyname].keyframe_insert("value",frame=frame-A_START+1)
        ob.data.shape_keys.use_relative = False
        ob.data.shape_keys.eval_time = 0
        ob.data.shape_keys.keyframe_insert("eval_time", frame=0)
        ob.data.shape_keys.eval_time = bpy.context.scene.frame_end*10 #Eval_time of 10 = 1 frame
        ob.data.shape_keys.keyframe_insert("eval_time", frame=bpy.context.scene.frame_end)
        ob.data.shape_keys.animation_data.action.fcurves[0].keyframe_points[0].interpolation = 'LINEAR'
        ob.data.shape_keys.animation_data.action.fcurves[0].keyframe_points[1].interpolation = 'LINEAR'
        bpy.context.scene.frame_set(0)

def load (operator, context, filepath, i_anim, a_format, i_matt, i_scale, frame_start, frame_end, frame_single):
    
    make_mesh(filepath, i_anim, a_format, i_matt, i_scale, frame_start, frame_end, frame_single)
    
    return {'FINISHED'}
