import math

import bpy
from . import data_types
import urllib.request, urllib.error, json
from json.decoder import JSONDecodeError

import mathutils
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
import blf
import bgl
import gpu
from gpu_extras.batch import batch_for_shader


#---------------------------------------------------------------------------------------------------
# BASIC OPERATIONS
#---------------------------------------------------------------------------------------------------


def set_active(object: bpy.types.Object):
    bpy.context.view_layer.objects.active = object
    
def set_mode(mode: str):
    bpy.ops.object.mode_set(mode=mode)

def select_none():
    bpy.ops.object.select_all(action='DESELECT')

def set_parent(children: list, parent: bpy.types.Object, keep_transform: bool, context: bpy.types.Context) -> None:
    ctx = context.copy()
    ctx['active_object'] = parent
    ctx['selected_objects'] = children
    ctx['selected_editable_objects'] = children
    bpy.ops.object.parent_set(ctx, keep_transform=keep_transform)

#additional operations
def get_selected_points(obj: bpy.types.Object) -> list:
    data = obj.data
    set_mode('OBJECT')
    points = []
    for idx, point in enumerate(data.splines[0].points):
        if point.select:
            points.append([point, idx])
    return points
    
def get_points_pairs(selected: list, max_curve_points_idx: int) -> list:
    selected_length = len(selected)
    pairs = []
    if selected_length == 1:
        print('You\'ve selected only one point')
        return None
    elif selected_length == 2:
        #------------------------------------------------
        # returns refs to points
        # pairs.append([selected[0][0], selected[1][0]])
        #------------------------------------------------
        
        #------------------------------------------------
        # returns points indices
        pairs.append([selected[0][1], selected[1][1]])
        #------------------------------------------------
        return pairs
    elif selected_length > 2:
        for idx, point in enumerate(selected):
            try:
                if point[1]+1 == selected[idx+1][1]:
                    #------------------------------------------------
                    # returns refs to points
                    # pairs.append([point[0], selected[idx+1][0]])
                    #------------------------------------------------
                    #------------------------------------------------
                    # returns points indices
                    pairs.append([point[1], selected[idx+1][1]])
                    #------------------------------------------------
                    
            except IndexError:
                if point[1] == max_curve_points_idx and selected[0][1] == 0:
                    #------------------------------------------------
                    # returns refs to points
                    # pairs.append([point[0], selected[0][0]])
                    #------------------------------------------------
                    #------------------------------------------------
                    # returns points indices
                    pairs.append([point[1], selected[0][1]])
                    #------------------------------------------------
        return pairs
                
def get_vector_from_coordinates(point1: Vector, point2: Vector):
    point1_3d = point1.copy()
    point1_3d.resize(3)
    point2_3d = point2.copy()
    point2_3d.resize(3)
    return point2_3d - point1_3d
    
def get_vector_center(vector: Vector):
    return vector / 2
    
def get_edges_of_selected_verts_2(obj: bpy.types.Object, vertices: list):
    data = obj.data
    groups = {None: []}
    groups.pop(None)
    for v in vertices:
        edges = []
        for edge in data.edges:
            if v.index in set(edge.vertices):
                edges.append(edge)
        groups[v] = edges
    return groups
        
def get_edges_of_selected_verts(obj: bpy.types.Object, vertices: list) -> list:
    data = obj.data
    groups: dict
    edges = []
    for edge in data.edges:
        for v in vertices:
            if v.index in set(edge.vertices):
                edges.append(edge)
    if len(edges) > 0:
        return edges
    else:
        return None
    
def get_common_edges_for_verts(edges: list) -> list:
    common = []
    for elem in edges:
        n = edges.count(elem)
        if n > 1:
            common.append(elem)
            return common
    return None
    

#---------------------------------------------------------------------------------------------------
# CUSTOM OPERATIONS
#---------------------------------------------------------------------------------------------------


#objects generation --------------------------------------------------------------------------------

#set boundings for object
def set_boundings_for_object(opening_mdl: bpy.types.Object, context: bpy.types.Context, extrude: bool):
    opening_mdl = context.object
    #get object's bounds
    obj_bounds_cords = get_object_bounds_coords(opening_mdl, 'WORLD')
    #create bounds object
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    bounds_obj: bpy.types.Object = context.object
    bounds_obj.props.type = 'BOUNDING'
    bounds_obj.display_type = 'WIRE'
    bounds_obj.hide_render = True
    bnds_obj_sides = get_bounder_vertices(bounds_obj)
    for idx, v_grp in enumerate(bnds_obj_sides):
        for v_ind in v_grp:
            if idx < 3:
                bounds_obj.data.vertices[v_ind].co[idx] = obj_bounds_cords[idx]
            else:
                bounds_obj.data.vertices[v_ind].co[idx-3] = obj_bounds_cords[idx]
    
    #setting origin to the center of bounding
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')

    #setting wb_props for both window model and bounding
    opening_mdl.wb_props.bounding_object = bounds_obj
    if opening_mdl.wb_props.object_type != 'OPENING':
        opening_mdl.wb_props.object_type = 'OPENING'
    bounds_obj.wb_props.object_type = 'HELPER'
    bounds_obj.wb_props.helper_type = opening_mdl.wb_props.opening_type[0: len(opening_mdl.wb_props.opening_type) - 1]
    
    
    #make opening mesh unselectable
    # opening_mdl.hide_select = True    
    
    #change bounder name according to the window model
    bounds_obj.name = opening_mdl.name + '_BND'
    
    #extrude alongside/opposite face axis
    if extrude:
        face_data = get_bounder_face(bounds_obj)
        face_inds = [p.index for p in face_data[0]]
        print(f'FACE IDXS: {face_inds}')
        #deselect all polys
        set_mode(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        set_mode(mode='OBJECT')
        if face_data[1] < 0.5:
            extr_value = (0.5 - face_data[1]) / 2
            for idx in face_inds:
                set_mode(mode='OBJECT')
                bounds_obj.data.polygons[idx].select = True
                set_mode(mode='EDIT')
                #invert extrude_value if normal is negative
                if bounds_obj.data.polygons[idx].normal[1] < 0:
                    extr_value = -extr_value
                bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False,
                                                                        "use_dissolve_ortho_edges":False,
                                                                        "mirror":False},
                                                TRANSFORM_OT_translate={"value":(0, 0, extr_value),
                                                                        "orient_axis_ortho":'X',
                                                                        "orient_type":'NORMAL',
                                                                        "orient_matrix":((-1, 0, 0), (0, -0, 1), (0, 1, 0)),
                                                                        "orient_matrix_type":'NORMAL',
                                                                        "constraint_axis":(False, False, True),
                                                                        "mirror":False,
                                                                        "use_proportional_edit":False})
                    
                bpy.ops.mesh.select_all(action='DESELECT')

    set_mode(mode='OBJECT')
    
    #setting bounder origin to window origin
    bpy.ops.object.select_all(action='DESELECT')
    bounds_obj.select_set(True)
    set_active(opening_mdl)
    bpy.context.scene.tool_settings.use_transform_data_origin = True
    bpy.ops.view3d.snap_selected_to_active()
    
    #setting bounding object as parent for opening
    bpy.ops.object.select_all(action='DESELECT')
    opening_mdl.select_set(True)
    set_active(bounds_obj)
    bounds_obj.select_set(True)
    bpy.ops.object.parent_set(keep_transform=True)
    
    #select and activate bounder object
    bpy.context.scene.tool_settings.use_transform_data_origin = False
    bpy.ops.object.select_all(action='DESELECT')
    set_active(bounds_obj)
    bounds_obj.select_set(True)
    
    return 'EEE BOI'


def get_object_bounds_coords(object: bpy.types.Object, space: str = 'WORLD') -> tuple:
    """calculates an object's maximum and minimum world positions
    on axes. Returns a tuple of type: (x_max, y_max, z_max, x_min, y_min, z_min).
    Space should be 'WORLD' for global coords system, and 'OBJECT' for local coords system"""

    obj_verts = object.data.vertices
    v_cords_x = []
    v_cords_y = []
    v_cords_z = []
    for v in obj_verts:
        if space == 'WORLD':
            v_cords_x.append((object.matrix_world @ v.co)[0])
            v_cords_y.append((object.matrix_world @ v.co)[1])
            v_cords_z.append((object.matrix_world @ v.co)[2])
        elif space == 'OBJECT':
            v_cords_x.append(v.co[0])
            v_cords_y.append(v.co[1])
            v_cords_z.append(v.co[2])
    x_min = min(v_cords_x)
    x_max = max(v_cords_x)
    y_min = min(v_cords_y)
    y_max = max(v_cords_y)
    z_min = min(v_cords_z)
    z_max = max(v_cords_z)
    # print(z_min)
    
    return (x_max, y_max, z_max, x_min, y_min, z_min)

#get object's bounds vertices indices
def get_bounder_vertices(object: bpy.types.Object) -> list:
    """gets parallelepiped object that will be used as bounding box,
    and returns groups of vertices of faces, depending on the position
    of the polygons normals in relation to the coordinate axes. Returns
    list of lists vertices in the order: [[x+][y+][z+],[x-],[y-],[z-]]"""

    obj_data = object.data
    v_idxs = [[], [], [], [], [], []]
    for p in obj_data.polygons:
        for idx, v in enumerate(list(p.normal)):
            if v > 0:
                v_idxs[idx] = list(p.vertices)
            elif v < 0:
                v_idxs[idx + 3] = list(p.vertices)

    return v_idxs

def get_bounder_face(bounds_obj: bpy.types.Object) -> list:
    '''-> [[polygon face axis +, polygon face axis -], face side dimension, face axis]'''
    obj_data: bpy.types.Mesh = bounds_obj.data
    
    polygons = [None, None]
    axis = 1
    bounds_dims = bounds_obj.dimensions
    face_size = bounds_dims.y
    if bounds_dims.x < bounds_dims.y:
        axis = 0
        face_size = bounds_dims.x
    for p in obj_data.polygons:
        if p.normal[axis] > 0:
            polygons[0] = p
        elif p.normal[axis] < 0:
            polygons[1] = p
    
    return [polygons, face_size]

def get_objects_distance(object1: bpy.types.Object, object2: bpy.types.Object, axis: str = 'x'):
    """method returns distance between two objects"""
    bounds = []
    #specific operations for certain types of objects
    for obj in (object1, object2):
        if obj.type == 'MESH':
            bounds.append(get_object_bounds_coords(obj))
        elif obj.type == 'EMPTY':
            pass
    
    axis_ind = data_types.axes[axis]
        
    if bounds[0][axis_ind + 3] > bounds[1][axis_ind]:
        print('======DOROU=====')
    elif bounds[1][axis_ind + 3] > bounds[0][axis_ind]:
        print('====DOTVIDANINYA=======')
    else:
        print('=====OBJECTS OVERLAPING======')
    
        
    print(bounds)
    print(axis_ind)
    
    return 'jopa'

def get_average_relative_location(object1: bpy.types.Object, object2: bpy.types.Object, axis='x') -> Vector:
    axis_idx = data_types.axes[axis]
    return (0, 0, 0)


def get_objects_distance_axis(axis: str = '') -> str:
    """returns calculated or received axis to use between objects"""
    if axis:
        return axis
    else:
        return 'x'
    

#curves generators
def curve_create_line(self, context, start: tuple, end: tuple) -> bpy.types.Object:
    bpy.ops.curve.simple(
        align='WORLD', 
        location=(0, 0, 0), 
        rotation=(0, 0, 0), 
        Simple_Type='Line', 
        shape='2D', 
        outputType='POLY', 
        use_cyclic_u=False,
        edit_mode=False)
    obj = context.object
    mat_world = obj.matrix_world
    obj.data.splines[0].points[0].co = mat_world.inverted() @ Vector(start)

    point0_pos = obj.data.splines[0].points[0].co
    obj.data.splines[0].points[1].co = (point0_pos[0] + context.scene.tools_props.new_length, point0_pos[1], point0_pos[2], point0_pos[3])
    


    # bpy.ops.transform.resize(value=(1, 1, 0))
    # mat_world = obj.matrix_world
    # obj.data.splines[0].points[0].co = mat_world.inverted() @ Vector(start)
    # end_vec = Vector((start[0] + context.scene.tools_props.new_length, end[1], end[2], end[3]))
    # print(end_vec)
    # obj.data.splines[0].points[1].co = mat_world.inverted() @ end_vec
    
    context.object.data.fill_mode = 'NONE'
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')

    return context.object

def curve_create_rectangle(self, context) -> bpy.types.Object:
    length = context.scene.tools_props.new_length
    width = context.scene.tools_props.new_width
    #create shape
    bpy.ops.curve.simple(
        align='WORLD', 
        location=(0, 0, 0), 
        rotation=(0, 0, 0), 
        Simple_Type='Rectangle', 
        Simple_width=width, 
        Simple_length=length, 
        shape='2D', 
        outputType='POLY', 
        use_cyclic_u=True, 
        edit_mode = False)
    #remove filling
    context.object.data.fill_mode = 'NONE'
    

    return context.object

#geometry nodes ------------------------------------------------------------------------------------

#geom nodes connector method
def node_group_link(node_group, node1_output, node2_input):
    node_group.links.new(node1_output, node2_input)


#web operations ------------------------------------------------------------------------------------

#generate customers list from API
def get_customers_info():
    interface_list_generated = []
    url = 'https://www.bauvorschau.com/api/clients_measures'
    errmessage = 'BBP->Utils->get_customers_info(): '
    try:
        responce = urllib.request.urlopen(url)
    except urllib.error.URLError as err:
        print(errmessage, err)
        return [('URL_ERR', 'CUSTOMERS DATA NOT LOADED', 'error in the utils->get_customers_info()->urlopen()')]
    else:
        try:
            customers = json.loads(responce.read())
        except JSONDecodeError as err:
            print(errmessage, err)
            return [('JSON_ERR', 'CUSTOMERS DATA NOT LOADED', 'error in the Butils->get_customers_info()->json.loads()')]
        else:
            data_types.customers_json = customers
            for customer in customers:
                interface_list_generated.append((customer['ucm_id'], customer['mc_name'], ''))

            return interface_list_generated
        

# bgl/gpu/blf operations ---------------------------------------------------------------------------
def draw_callback_line_3D(self, context: bpy.types.Context, points: tuple, color: tuple, linewidth: int):
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_LINE_SMOOTH)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    
    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": points})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    
    bgl.glLineWidth(linewidth)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glDisable(bgl.GL_LINE_SMOOTH)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    
def draw_size_ruler_3D(self, context: bpy.types.Context):
    obj = context.object
    omw = obj.matrix_world
    
    point0 = get_vertex_global_co(obj, 0)
    inverted_normal = obj.data.vertices[0].normal * 2
    
    eul = mathutils.Euler((1, 2, 1), 'XYZ')
    eul.rotate_axis('Z', math.radians(2))
    
    inverted_normal_2D = Vector((inverted_normal[0], inverted_normal[1], obj.data.vertices[0].co[2]))
    inverted_normal_2D.rotate(eul)
    inverted_normal_2D_global = omw @ inverted_normal_2D
    
    point1 = get_vertex_global_co(obj, 1)
    the_vector = Vector((point1 - point0))
    ortho = Vector.orthogonal(the_vector)
    print(ortho)
    
    draw_callback_line_3D(self, context, (point0, inverted_normal_2D_global), (0.0, 1.0, 0.0, 1.0), 1)
    
def get_vertex_global_co(obj: bpy.types.Object, v_index: int):
    matrix_world = obj.matrix_world
    v_coords = matrix_world @ obj.data.vertices[v_index].co
    return v_coords

def draw_text_callback_2D(self, context: bpy.types.Context, color=(0.0, 1.0, 0.0, 1.0), size=16, dpi=72, \
                            position=(100, 100, 0), text='Lorem Ipsum', loc3d_to_2d=False, position3D=(1, 1, 1)):
    v3d = context.space_data
    rv3d = v3d.region_3d
    
    font_id = 0
    
    blf.color(font_id, color[0], color[1], color[2], color[3])
    blf.size(font_id, context.scene.props.opengl_font_size, dpi)
    if loc3d_to_2d:
        pos_2d = location_3d_to_region_2d(context.region, rv3d, position3D)
        blf.position(font_id, pos_2d[0], pos_2d[1], 0)
    else:
        blf.position(font_id, position[0], position[1], 0)
    blf.draw(font_id, text)
    

def draw_text_callback_2D_exp(self, context: bpy.types.Context, pairs: list, obj: bpy.types.Object):
    
    v3d = context.space_data
    rv3d = v3d.region_3d
    
    font_id = 0
    
    for pair in pairs:        
        length = (obj.data.splines[0].points[pair[1]].co - obj.data.splines[0].points[pair[0]].co).length
        center_4d = (obj.data.splines[0].points[pair[1]].co + obj.data.splines[0].points[pair[0]].co) / 2
        center_3d = center_4d.copy()
        center_3d.resize(3)
        center = bpy.context.object.matrix_world @ center_3d
        text_pos = location_3d_to_region_2d(context.region, rv3d, center)
        blf.color(font_id, 0.0, 1.0, 0.0, 1.0)
        blf.size(font_id, 20, 72)
        blf.position(font_id, 100, 100, 0)
        print(pair)
        blf.position(font_id, text_pos[0], text_pos[1], 0)
        system_units = bpy.data.scenes['Scene'].unit_settings.length_unit
        if system_units == 'MILLIMETERS':
            blf.draw(font_id, '%.0f mm' % (length * 1000))
        elif system_units == 'METERS':
            blf.draw(font_id, '%.2f m' % (length))
        elif system_units == 'CENTIMETERS':
            blf.draw(font_id, '%.2f cm' % (length * 100))
        else:
            blf.draw(font_id, 'unsupported length units')
            
            

    # blf.draw(font_id, '%.2f m | %.2f m | %.2f m' % (dims[0], dims[1], dims[2]))