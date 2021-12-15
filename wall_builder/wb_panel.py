import bpy
from bpy.props import RemoveProperty
import data_types
import wb_operators

class WBPanel(bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_MainMenu'
    bl_label = 'wall builder configurator'
    bl_category = 'C7 WALL BUILDER'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    # @classmethod
    # def poll(cls, context):
    #     pass

    def get_object_buttons(self, layout):
        row = layout.row()
        props = row.operator(wb_operators.WallBuilder.bl_idname)

    # def draw_header(self, context):
    #         layout = self.layout
    #         layout.label(text="MY TEST HEADER")
    #         layout.prop(context.object.wall_builder_props, 'height')



    def draw(self, context):
        layout = self.layout
        if context.object:

            col = layout.column()
            tex = bpy.data.textures['jopa']
            col.template_preview(tex, show_buttons=False)

            row = col.row()
            row.label(text='OBJECT: {} ({})'.format(context.object.name, context.object.type))

            col = layout.column()
            row = col.row()
            row.label(text='OBJECT PROPERTIES:')

            row = col.row()
            row.prop(context.object.wall_builder_props, 'customer')

            row = col.row()
            row.prop(context.object.wall_builder_props, 'object_type')

            #IF WALL
            if context.object.wall_builder_props.object_type == 'WALL':

                row = col.row()
                row.prop(context.object.wall_builder_props, 'is_inner_wall')

                row = col.row()
                row.prop(context.object.wall_builder_props, 'level')

                #geom nodes props
                row = col.row()
                modif_geom_nodes = context.object.modifiers.get('wb_geom_nodes')
                
                row = col.row()
                row.prop(context.object.wall_builder_props, 'height')
                
                row = col.row()
                row.prop(context.object.wall_builder_props, 'thickness')

                row = col.row()
                row.prop(context.object.wall_builder_props, 'position', text='wall position (ex. photoshop stroke')

                #CONVERT OR RESET THE OBJECT -------------------------------------------------------
                if context.object.wall_builder_props.is_converted:
                    row = col.row()
                    row.operator(wb_operators.WallBuilder.bl_idname, text='RESET OBJECT', icon='CANCEL')
                else:
                    row = col.row()
                    props = row.operator(wb_operators.WallBuilder.bl_idname, text='CONVERT OBJECT', icon='SHADERFX')

                #IF OBJECT HAS OPENINGS ------------------------------------------------------------
                if context.object.wall_builder_props.is_converted:
                    scn = bpy.context.scene

                    row = col.row()
                    row.template_list('OpeningsItem2', '', bpy.context.object, 'openings', bpy.context.object, 'opening_index', rows=1)

                    row = col.row(align=True)
                    row.operator('object.opnenings_adder', text='ADD OPENINGS').action = 'ADD'
                    row.operator('object.opnenings_adder', text='REMOVE OPENING').action = 'REMOVE'
                    # row.operator('custom.add_openings', icon='ZOOM_IN', text='ADD').action = 'ADD'
                    # row.operator('custom.add_openings', icon='ZOOM_OUT', text='REMOVE').action = 'REMOVE'
                    row.operator('custom.add_openings', icon='TRIA_UP', text='').action = 'UP'
                    row.operator('custom.add_openings', icon='TRIA_DOWN', text='').action = 'DOWN'

                    row = col.row()
                    bo = row.prop(context.object.wall_builder_props, 'align_marker')


                    


            #IF OPENING
            elif context.object.wall_builder_props.object_type == 'OPENING':
                row = col.row()
                row.prop(context.object.wall_builder_props, 'opening_type')

            #IF FLOOR
            elif context.object.wall_builder_props.object_type == 'FLOOR':
                row = col.row()
                row.prop(context.object.wall_builder_props, 'level')
                row = col.row()
                row.prop(context.object.wall_builder_props, 'height')
                row = col.row()
                props = row.operator(wb_operators.WallBuilder.bl_idname, text='CONVERT OBJECT', icon='SHADERFX')

            row=col.row()
            row.label(text='GLOBAL PROPERTIES:')

            row=col.row()
            plans_collection = row.prop(data=context.scene.wall_builder_scene_props,property='plans_collection', slider=True)     

            row = col.row()
            row.operator(wb_operators.BuildingAssembler.bl_idname, text='ASSEMBLE THE BUILDING') 
                

# openings item
class OpeningsItem(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split()
        split.label(text=f'opening idx: {index}')
        # split.prop(item, 'name', text='', emboss='false', translate='false', icon='EXPERIMENTAL')
        split.label(text=item.name, icon='EXPERIMENTAL')

    def invoke(self, context, ivent):
        pass

# openings item
class OpeningsItem2(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split()
        split.label(text=f'opening idx: {index}')
        # split.prop(item, 'name', text='', emboss='false', translate='false', icon='EXPERIMENTAL')
        split.label(text=item.obj.name, icon='EXPERIMENTAL')

    def invoke(self, context, ivent):
        pass


# REGISTRATION

classes = (WBPanel,
            OpeningsItem,
            OpeningsItem2)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)

if __name__ == "__main__":
    register()