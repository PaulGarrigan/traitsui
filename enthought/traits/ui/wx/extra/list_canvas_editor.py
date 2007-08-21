#-------------------------------------------------------------------------------
#
#  An editor for displaying list items as themed Traits UI Views on a themed
#  free-form canvas.
#
#  Written by: David C. Morrill
#
#  Date: 08/10/2007
#
#  (c) Copyright 2007 by Enthought, Inc.
#
#-------------------------------------------------------------------------------

""" An editor for displaying list items as themed Traits UI Views on a themed
    free-form canvas.
"""

#-------------------------------------------------------------------------------
#  Imports:
#-------------------------------------------------------------------------------

import wx

from enthought.traits.api \
    import HasTraits, HasPrivateTraits, HasStrictTraits, Interface, Instance, \
           List, Enum, Color, Bool, Range, Str, Float, Event, Tuple, Property, \
           Any, implements, on_trait_change
    
from enthought.traits.trait_base \
    import user_name_for
           
from enthought.traits.ui.api \
    import UI, View, Item, Theme
    
from enthought.traits.ui.ui_traits \
    import ATheme
    
from enthought.traits.ui.ui_traits \
    import AView
    
from enthought.traits.ui.wx.editor \
    import Editor
    
from enthought.traits.ui.wx.basic_editor_factory \
    import BasicEditorFactory
    
from enthought.traits.ui.wx.image_panel \
    import ImagePanel
    
from enthought.traits.ui.wx.themed_checkbox_editor \
    import ThemedCheckboxEditor
    
from enthought.traits.ui.wx.themed_slider_editor \
    import ThemedSliderEditor
    
from enthought.pyface.dock.api \
    import add_feature
    
from enthought.pyface.timer.api \
    import do_later

from enthought.pyface.image_resource \
    import ImageResource
    
from enthought.traits.ui.wx.helper \
    import init_wx_handlers
    
#-------------------------------------------------------------------------------
#  Constants:
#-------------------------------------------------------------------------------
        
# Have the contents of an item been modified:
Modified = None

# wx pen styles:
pen_styles = {
    'solid': wx.SOLID,
    'dash':  wx.SHORT_DASH,
    'dot':   wx.DOT
}

# Dictionay of standard images used:
images = {
    'feature':  ImageResource( 'feature' ),
    'clone':    ImageResource( 'drag' ),
    'drag':     ImageResource( 'drag' ),
    'close':    ImageResource( 'close' ),
    'minimize': ImageResource( 'minimize' ),
    'restore':  ImageResource( 'restore' ),
    'selected': ImageResource( 'selected' )
}

#-------------------------------------------------------------------------------
#  Trait definitions:
#-------------------------------------------------------------------------------

# Operations allowed on a list canvas:
CanvasOperations = List( Enum( 'move', 'size', 'add', 'clone', 'drag', 'drop', 
                               'load', 'save', 'close', 'clear', 'minimize', 
                               'status', 'tooltip' ) )

#-------------------------------------------------------------------------------
#  Helper functions:
#-------------------------------------------------------------------------------

# wx stock cursor cache:
stock_cursors = {}

def get_cursor ( cursor_id ):
    """ Returns the wx stock cursor corresponding to a specified cursor id.
    """
    global stock_cursors
    
    cursor = stock_cursors.get( cursor_id )
    if cursor is None:
        stock_cursors[ cursor_id ] = cursor = wx.StockCursor( cursor_id )
        
    return cursor
    
#-------------------------------------------------------------------------------
#  'IListCanvasAdapter' interface:
#-------------------------------------------------------------------------------

class IListCanvasAdapter ( Interface ):
    """ The interface that any sub-adapter of a ListCanvasAdapter must
        implement.
    """

    # The current list canvas item:
    item = Instance( HasTraits )

    # The current item being dropped (if any):
    drop = Instance( HasTraits )    
    
    # Does the adapter know how to handle the current *item* or not:
    accepts = Bool
    
    # Does the value of *accepts* depend only upon the type of *item*?
    is_cacheable = Bool

#-------------------------------------------------------------------------------
#  'AnIListCanvasAdapter' interface:
#-------------------------------------------------------------------------------

class AnIListCanvasAdapter ( Interface ):
    """ A concrete implementation of the IListCanvasAdapter interface.
    """
    
    implements( IListCanvasAdapter )

    # The current list canvas item:
    item = Instance( HasTraits )

    # The current item being dropped (if any):
    drop = Instance( HasTraits )    
    
    # Does the adapter know how to handle the current *item* or not:
    accepts = Bool( True )
    
    # Does the value of *accepts* depend only upon the type of *item*?
    is_cacheable = Bool( True )
    
#-------------------------------------------------------------------------------
#  'IListCanvasItem' interface:
#-------------------------------------------------------------------------------

class IListCanvasItem ( Interface ):
    """ An interface that items on a list canvas can implement to supply
        information that would normally be supplied by a ListCanvasAdapter.
        
        Note that it is not necessary for a class to implement the entire
        interface. If a list canvas adapter sees that an item implements the
        IListCanvasItem interface, it will check to see if the class implements
        the particular aspect of the interface it needs. If it does not, then
        the adapter will satisfy the request itself.
    """
    
    # The theme to use for the list canvas item when it is active:
    list_canvas_item_theme_active = ATheme
    
    # The theme to use for the list canvas item when it is inactive:
    list_canvas_item_theme_inactive = ATheme
    
    # The theme to use while the pointer hovers over the list canvas item:
    list_canvas_item_theme_hover = ATheme
    
    # The title to use for the list canvas item:
    list_canvas_item_title = Str
    
    # The unique id of the list canvas item:
    list_canvas_item_unique_id = Str
    
    # Can the list canvas item be moved?
    list_canvas_item_can_move = Bool
    
    # Can the list canvas item be resized?
    list_canvas_item_can_resize = Bool
    
    # Can the current drag object be dropped on the list canvas item?
    list_canvas_item_can_drop = Bool
    
    # If the preceding trait is implemented, then this trait should be 
    # implemented as well if you need to know what object is being dropped:
    list_canvas_item_drop = Instance( HasTraits )
    
    # Can the list canvas item be closed?
    list_canvas_item_can_close = Enum( True, False, Modified )
    
    # Returns the draggable form of the list canvas item:
    list_canvas_item_drag = Instance( HasTraits )
    
    # Specifies the clone of the list canvas item:
    list_canvas_item_clone = Instance( HasTraits )
    
    # Specifies the Traits UI View to use for the canvas list item when it is
    # added to the canvas:
    list_canvas_item_view = AView
    
    # Specifies the view model used to represent the canvas list item when it 
    # is added to the canvas:
    list_canvas_item_view_model = Instance( HasTraits )
    
    # Specifies the initial size to make the canvas list item when it is added
    # to the canvas. The value is a tuple of the form: (width,height), where 
    # the width and height values have the following meaning:
    # - <= 0: Use the default size.
    # - 0 < value <= 1: Use the specified fraction of the corresponding width
    #     or height dimension.
    # > 1: Use int(value) as the actual width or height specified in pixels.
    list_canvas_item_size = Tuple( Float, Float )
    
    # Specifies the initial position of the canvas list item when it is added 
    # to the canvas. The value is a tuple of the form: (x,y), where x and y 
    # values have the following meaning:
    # - <= 0: Use the default coordinate.
    # - 0 < value <= 1: Use the specified fraction of the corresponding width
    #     or height dimension as the coordinate value.
    # > 1: Use int(value) as the actual x or y coordinate specified in pixels.
    list_canvas_item_position = Tuple( Float, Float )
    
    # Specifies the tooltip to display for the list canvas item:
    list_canvas_item_tooltip = Str
    
    # Event fired when the list canvas item is closed:
    list_canvas_item_closed = Event
    
    # The event fired when the list canvas item is activated:
    list_canvas_item_activated = Event
    
    # The event fired when the list canvas item is de-activated:
    list_canvas_item_deactivated = Event
    
#-------------------------------------------------------------------------------
#  'ListCanvasAdapter' class:
#-------------------------------------------------------------------------------

class ListCanvasAdapter ( HasPrivateTraits ):
    """ The base class for all list canvas editor adapter classes.
    """
    
    #-- Traits that are item specific ------------------------------------------
    
    # The default theme to use for the current active list canvas item:
    ###theme_active = ATheme( Theme( '@BL5', margins = ( -6, -2 ) ) )
    theme_active = ATheme( Theme( 'default_active', 
                                  offset = ( 0, 2 ), margins = ( -15, 2 ) ) )
    
    # The default theme to use for the current inactive list canvas item (if 
    # None is returned, the value of *theme_active* is used):
    ###theme_inactive = ATheme( Theme( '@BLB', margins = ( -6, -2 ) ) )
    theme_inactive = ATheme( Theme( 'default_inactive', 
                                    offset = ( 0, 2 ), margins = ( -15, 2 ) ) )
    
    # The default theme to use while the pointer hovers over the current
    # inactive list canvas item (if None is returned, the value of 
    # *theme_inactive* is used):
    ###theme_hover = ATheme( Theme( '@BLC', margins = ( -6, -2 ) ) )
    theme_hover = ATheme( Theme( 'default_hover', 
                                 offset = ( 0, 2 ), margins = ( -15, 2 ) ) )
    
    # The title to use for the current list canvas item:
    title = Str
    
    # The unique id of the current list canvas item:
    unique_id = Str
    
    # Can the current list canvas item be moved?
    can_move = Bool( True )
    
    # Can the current list canvas item be resized?
    can_resize = Bool( True )
    
    # Can the current drag object be dropped on the current list canvas item
    # (or on the canvas itself if the current list canvas item is None)? 
    can_drop = Bool( False )
    
    # Can the current list canvas item be deleted (i.e. is close allowed)?
    can_delete = Bool( False )
    
    # Can the current list canvas item be closed? The possible values are:
    # - True: Yes.
    # - False: No.
    # - Modified: The item has been modified. Prompt the user whether the item
    #     should be closed before closing it.
    can_close = Enum( True, False, Modified )
    
    # Can the current list canvas item be dragged?
    can_drag = Bool( False )
    
    # Returns the draggable form of the current list canvas item (or None if
    # the current item can not be dragged):
    drag = Instance( HasTraits )
    
    # Can the current list canvas item be cloned?
    can_clone = Bool( True )
    
    # Specifies the clone of the current list canvas item:
    clone = Instance( HasTraits )
    
    # Specifies the Traits UI View to use for the current canvas list item when
    # it is added to the canvas:
    view = AView
    
    # Specifies the view model used to represent the current canvas list item
    # when it is added to the canvas:
    view_model = Instance( HasTraits )
    
    # Specifies the initial size to make the current canvas list item when it
    # is added to the canvas. The value is a tuple of the form: (width,height),
    # where the width and height values have the following meaning:
    # - <= 0: Use the default size.
    # - 0 < value <= 1: Use the specified fraction of the corresponding width
    #     or height dimension.
    # > 1: Use int(value) as the actual width or height specified in pixels.
    size = Tuple( Float, Float )
    
    # Specifies the initial position of the current canvas list item when it
    # is added to the canvas. The value is a tuple of the form: (x,y), where
    # x and y values have the following meaning:
    # - <= 0: Use the default coordinate.
    # - 0 < value <= 1: Use the specified fraction of the corresponding width
    #     or height dimension as the coordinate value.
    # > 1: Use int(value) as the actual x or y coordinate specified in pixels.
    position = Tuple( Float, Float )
    
    # Specified the tooltip to display for the current list canvas item:
    tooltip = Str
    
    #-- Events fired by the editor ---------------------------------------------
    
    # Event fired when the current list canvas item is closed:
    closed = Event
    
    # Event fired when the current list canvas item is activated:
    activated = Event
    
    # Event fired when the current list canvas item is de-activated:
    deactivated = Event

    #-- Traits that the editor listens for changes on --------------------------
    
    # Specifies the current message to display on the list canvas status line:
    status = Str
    
    #-- Traits set by the editor -----------------------------------------------
    
    # The current list canvas item (a value of **None** means the entire 
    # canvas):
    item = Instance( HasTraits )

    # The current item being dropped (if any):
    drop = Instance( HasTraits )    
    
    #-- Traits not used by the editor ------------------------------------------
    
    # The list of optional delegated adapters:
    adapters = List( IListCanvasAdapter, update = True )

    #-- Private Traits ---------------------------------------------------------
    
    # Cache of attribute handlers:
    cache = Any( {} )
    
    #-- Adapter methods called by the editor -----------------------------------

    def get_theme_active ( self, item ):
        """ Returns the theme to use for the specified item when it is active.
        """
        return self._result_for( 'get_theme_active', item )
        
    def get_theme_inactive ( self, item ):
        """ Returns the theme to use for the specified item when it is inactive.
        """
        return (self._result_for( 'get_theme_inactive', item ) or
                self._result_for( 'get_theme_active',   item ))
        
    def get_theme_hover ( self, item ):
        """ Returns the theme to use for the specified item when it is inactive
            and the mouse pointer is hovering over it.
        """
        return (self._result_for( 'get_theme_hover',    item ) or
                self._result_for( 'get_theme_inactive', item ) or
                self._result_for( 'get_theme_active',   item ))
                
    def get_title ( self, item ):     
        """ Returns the title to use for the specified item.
        """
        return self._result_for( 'get_title', item )
                
    def get_unique_id ( self, item ):     
        """ Returns the unique id for the specified item.
        """
        return self._result_for( 'get_unique_id', item )
                
    def get_can_move ( self, item ):     
        """ Returns whether or not the specified item can be moved on the
            canvas.
        """
        return self._result_for( 'get_can_move', item )
                
    def get_can_resize ( self, item ):     
        """ Returns whether or not the specified item can be resized on the
            canvas.
        """
        return self._result_for( 'get_can_resize', item )
                
    def get_can_drop ( self, item, drop ):     
        """ Returns whether or not the specified droppable object can be
            dropped on the specified item.
        """
        return self._result_for( 'get_can_drop', item, drop )
                
    def get_can_delete ( self, item ):     
        """ Returns whether or not the specified item can be deleted from the
            canvas.
        """
        return self._result_for( 'get_can_delete', item )
                
    def get_can_close ( self, item ):     
        """ Returns whether or not the specified item can be closed on the 
            canvas.
        """
        return self._result_for( 'get_can_close', item )
                
    def get_can_drag ( self, item ):     
        """ Returns whether or not the specified item can be dragged.
        """
        return self._result_for( 'get_can_drag', item )
                
    def get_drag ( self, item ):     
        """ Returns the draggable form of the specified item.
        """
        return self._result_for( 'get_drag', item )
                
    def get_can_clone ( self, item ):     
        """ Returns whether or not the specified item can be cloned on the 
            canvas.
        """
        return self._result_for( 'get_can_clone', item )
                
    def get_clone ( self, item ):     
        """ Returns the clone of the specified item.
        """
        return self._result_for( 'get_clone', item )
                
    def get_view ( self, item ):     
        """ Returns the view to use for the specified item when it is added to
            the canvas.
        """
        return self._result_for( 'get_view', item )
                
    def get_view_model ( self, item ):     
        """ Returns the view model to use for the specified item when it is 
            added to the canvas.
        """
        return self._result_for( 'get_view_model', item )
                
    def get_size ( self, item ):     
        """ Returns the size to use for the view of the specified item when it
            is added to the canvas.
        """
        return self._result_for( 'get_size', item )
                
    def get_position ( self, item ):     
        """ Returns the position to use for the view of the specified item when 
            it is added to the canvas.
        """
        return self._result_for( 'get_position', item )
                
    def get_tooltip ( self, item ):     
        """ Returns the tooltip to display for the specified item when the 
            mouse pointer is over its view on the canvas.
        """
        return self._result_for( 'get_tooltip', item )
                
    def set_closed ( self, item ):     
        """ Notifies that the specified item has been closed on the canvas.
        """
        self._result_for( 'set_closed', item )
                
    def set_activated ( self, item ):     
        """ Notifies that the specified item has been activated on the canvas.
        """
        self._result_for( 'set_activated', item )
                
    def set_deactivated ( self, item ):     
        """ Notifies that the specified item has been deactivated on the canvas.
        """
        self._result_for( 'set_deactivated', item )
    
    #-- Trait Event Handlers ---------------------------------------------------
    
    @on_trait_change( ' adapters' )
    def _on_adapters_changed ( self ):
        """ Handles any change to the list of sub-adapters by flushing the 
            handler cache.
        """
        self.cache = {}
        
    #-- Private Methods --------------------------------------------------------
    
    def _result_for ( self, name, item, drop = None ):
        """ Returns/Sets the value of the specified *name* attribute for the
            specified list canvas item.
        """
        # Split the name into a prefix (get_/set_) and a trait name: 
        prefix     = name[:4]
        trait_name = name[4:]   
        
        # Check to see if the item itself implements the required trait:
        if item.has_traits_interface( IListCanvasItem ):
            lci_name = 'list_canvas_item_' + trait_name
            if item.trait( lci_name ) is not None:
                if prefix == 'get_':
                    if ((trait_name == 'can_drop') and
                        (item.trait( 'list_canvas_item_drop' ) is not None)):
                        item.list_canvas_item_drop = drop
                        
                    return getattr( item, lci_name )
                
                setattr( item, lci_name, True )
                
                return
                
        # Otherwise, we'll handle the request:
        self.item = item
        self.drop = drop
        
        # Check to see if we have already cached a handler for the trait:
        item_class = item.__class__
        key        = '%s:%s' % ( item_class.__name__, name )
        handler    = self.cache.get( key )
        if handler is not None:
            return handler()
            
        # If not, check to see if any sub-adapter can handle the request:
        for i, adapter in enumerate( self.adapters ):
            adapter.item = item
            adapter.drop = drop
            if adapter.accepts and adapter.trait( trait_name ) is not None:
                if prefix == 'get_':
                    handler = lambda: getattr( adapter.set(
                                          item = self.item, drop = self.drop ),
                                          trait_name ) 
                else:
                    handler = lambda: setattr( adapter.set(
                                          item = self.item, drop = self.drop ),
                                          trait_name, True )
                 
                # If the handler is cacheable, then proceed normally:
                if adapter.is_cacheable:
                    break
                    
                # Otherwise, invoke it and we'll do same thing the next time:
                return handler()
        else:
            # Look for a specialized handler based on a class in the item's mro:
            for klass in item_class.__mro__:
                handler = self._get_handler_for(
                              '%s_%s' % ( klass.__name__, trait_name ), prefix ) 
                if handler is not None:
                    break
                    
            else:  
                # If none found, just use the generic trait for the handler:
                handler = self._get_handler_for( trait_name, prefix )
            
        # Cache the resulting handler, so we don't have to look it up again:
        self.cache[ key ] = handler
        
        # Invoke the handler and return the result:
        return handler()

    def _get_handler_for ( self, name, prefix ):
        """ Returns the handler for a specified trait name (or None if not
            found).
        """
        if self.trait( name ) is not None:
            if prefix == 'get_':
                return lambda: getattr( self, name )
                
            return lambda: setattr( self, name, True )
            
        return None

#-------------------------------------------------------------------------------
#  'SnapInfo' class:  
#-------------------------------------------------------------------------------
                
class SnapInfo ( HasStrictTraits ):
    """ Defines item 'snapping' information for a canvas.
    """
    
    #-- Public Traits ----------------------------------------------------------
    
    # The magnetic 'snap' distance for edge snapping while dragging (a distance
    # of 0 means no snapping):
    distance = Range( 0, 10, 0 )
    
    #-- Trait View Definitions -------------------------------------------------
    
    view = View(
        Item( 'distance',
              editor  = ThemedSliderEditor(),
              tooltip = 'The magnetic snap distance for edge snapping while '
                        'dragging (a distance of 0 means no snapping)'
        )
    )
    
#-------------------------------------------------------------------------------
#  'GuideInfo' class:
#-------------------------------------------------------------------------------

class GuideInfo ( HasStrictTraits ):
    """ Defines 'guideline' information for a canvas.
    """
    
    #-- Public Traits ----------------------------------------------------------
    
    # When should guide lines be visible. The possible values are:
    # - always: Always display guide lines.
    # - never: Never display guide lines.
    # - drag: Display guide lines only during drag operations (move/resize).
    visible = Enum( 'never', 'always', 'drag' )
    
    # Is snapping allowed?
    snapping = Bool( True )
    
    # The color used for drawing guide lines:
    color = Color( 0xC8C8C8 )
    
    # The style used to draw guide lines:
    style = Enum( 'solid', 'dash', 'dot' )
    
    #-- Trait View Definitions -------------------------------------------------
    
    view = View(
        Item( 'visible',
              tooltip = 'Specifies when guide lines are visible'
        ),
        Item( 'snapping',
              editor  = ThemedCheckboxEditor(),
              tooltip = 'Specifies whether or not snapping is allowed?'
        ),
        Item( 'color',
              tooltip = 'Specifies the color used for drawing guide lines'
        ),
        Item( 'style',
              tooltip = 'Specifies the style used to draw guide lines'
        )
    )
    
#-------------------------------------------------------------------------------
#  'GridInfo' class:
#-------------------------------------------------------------------------------

class GridInfo ( HasStrictTraits ):
    """ Defines grid information for a coanvas.
    """
    
    #-- Public Traits ----------------------------------------------------------
    
    # When should the grid visible. The possible values are:
    # - always: Always display the grid.
    # - never: Never display the grid.
    # - drag: Display the grid only during drag operations (move/resize).
    visible = Enum( 'never', 'always', 'drag' )
    
    # Is snapping allowed?
    snapping = Bool( True )
    
    # The color used for drawing grid lines:
    color = Color( 0xC8C8C8 ) 
    
    # The style used for drawing grid lines:
    style = Enum( 'solid', 'dash', 'dot' )
    
    # The size of each grid cell (in pixels):
    size = Range( 5, 200, 50 )
    
    # The offset from the top-left corner of the canvas to the first grid cell
    # corner:
    offset = Range( 0, 200, 0 )
    
    #-- Trait View Definitions -------------------------------------------------
    
    view = View(
        Item( 'visible',
              tooltip = 'Specifies when grid lines are visible'
        ),
        Item( 'snapping',
              editor  = ThemedCheckboxEditor(),
              tooltip = 'Specifies whether or not snapping is allowed?'
        ),
        Item( 'color',
              tooltip = 'Specifies the color used for drawing grid lines'
        ),
        Item( 'style',
              tooltip = 'Specifies the style used to draw grid lines'
        ),
        Item( 'size',
              editor  = ThemedSliderEditor(),
              tooltip = 'Specifies the size of each grid cell in pixels'
        ),
        Item( 'offset',
              editor  = ThemedSliderEditor(),
              tooltip = 'Specifies the offset from the top-left corner of the '
                        'canvas to the first grid cell'
        )
    )
        
#-------------------------------------------------------------------------------
#  'ListCanvasItem' class:
#-------------------------------------------------------------------------------

class ListCanvasItem ( ImagePanel ):
    """ Defines a list canvas item, one or more of which can be added to a list 
        canvas.
    """
    
    #-- Public Traits ----------------------------------------------------------
    
    # The HasTraits object this is a list canvas item for:
    object = Instance( HasTraits )
    
    # The list canvas this item is displayed on:
    canvas = Instance( 'ListCanvas' )
    
    # The current mouse event state (override):
    state = 'inactive'
    
    # The position of the item on the list canvas:
    position = Property
    
    # The size of the item on the list canvas:
    size = Property
    
    #-- Private Traits ---------------------------------------------------------
    
    # The title of this item:
    title = Str
    
    # The Traits UI for the associated object:
    ui = Instance( UI )
    
    # The layout bounds dictionary:
    layout = Any( {} )
    
    #-- Public Methods ---------------------------------------------------------
    
    def dispose ( self ):
        """ Removes the item from the canvas it is contained in.
        """
        # Close the Traits UI contained in the item:
        if self.ui is not None:
            self.ui.dispose()
            
        # Now destroy the list canvas item control:
        if self.control is not None:
            self.control.Destroy()
            self.control = None

    def initialize_position ( self ):
        """ Initializes the position and size of the item.
        """
        # Get the values needed to compute the initial postion and size of the
        # item:
        canvas   = self.canvas
        adapter  = canvas.adapter
        bdx, bdy = self.best_size
        cdx, cdy = canvas.size
        x, y     = adapter.get_position( self.object )
        dx, dy   = adapter.get_size( self.object )
            
        # Calculate the initial size of the item:
        if dx <= 0.0:
            dx = bdx
        elif dx <= 1.0:
            dx = int( dx * cdx )
        else:
            dx = int( dx )
            
        if dy <= 0.0:
            dy = bdy
        elif dy <= 1.0:
            dy = int( dy * cdy )
        else:
            dy = int( dy )
        
        # Calculate the initial position of the item:
        if x <= 0.0:
            if y > 0.0:
                x = 0
        elif x <= 1.0:
            x = int( x * cdx )
        else:
            x = int( x )
        
        if y <= 0.0:
            if x <= 0.0:
                x, y = canvas.initial_position_for( dx, dy )
            else:
                y = 0
        elif y <= 1.0:
            y = int( y * cdy )
        else:
            y = int( y )
            
        # Set the item's position and size:
        self.control.SetDimensions( x, y, dx, dy )
        
    def resize ( self, mode, xo, yo, dxo, dyo, dx, dy ):
        """ Resize the control while in drag mode.
        """
        # Adjust axes that are not being dragged:
        if (mode & 0x05) == 0:
            dx = 0
            
        if (mode & 0x0A) == 0:
            dy = 0
        
        # Adjust the x-axis size and position:
        canvas = self.canvas
        if (mode & 0x04) != 0:
            dxs = canvas.snap_x( xo, dx )
            if (mode & 0x01) != 0:
                xo  += dxs
                dxo -= dxs
            elif dxs == dx:
                xo += canvas.snap_x( xo + dxo, dx )
            else:
                xo += dxs
        elif (mode & 0x01) != 0:
            dxo += canvas.snap_x( xo + dxo, dx )
            
        # Adjust the y-axis size and position:
        if (mode & 0x08) != 0:
            dys = canvas.snap_y( yo, dy )
            if (mode & 0x02) != 0:
                yo  += dys
                dyo -= dys
            elif dys == dy:
                yo += canvas.snap_y( yo + dyo, dy )
            else:
                yo += dys
        elif (mode & 0x02) != 0:
            dyo += canvas.snap_y( yo + dyo, dy )
            
        # Get the current control position and size:
        cx,  cy  = self.position
        cdx, cdy = self.size
        
        # Update the position and size of the control:
        if (xo != cx) or (yo != cy) or (dxo != cdx) or (dyo != cdy):
            self.control.SetDimensions( xo, yo, dxo, dyo )
        
    #-- Property Implementations -----------------------------------------------
    
    def _get_position ( self ):
        return self.control.GetPositionTuple()
        
    def _get_size ( self ):
        return self.control.GetSizeTuple()
            
    #-- Trait Event Handlers ---------------------------------------------------
    
    def _object_changed ( self, object ):
        """ Handles the 'object' trait being changed.
        """
        canvas     = self.canvas
        adapter    = canvas.adapter
        self.theme = adapter.get_theme_inactive( object )
        control    = self.create_control( canvas.canvas )
        self.title = (adapter.get_title( object ) or 
                      user_name_for( object.__class__.__name__ ))
        view_model = adapter.get_view_model( object ) or object
        self.ui    = ui = view_model.edit_traits(
                              parent = control, 
                              view   = adapter.get_view( object ), 
                              kind   = 'subpanel' )
            
        control.GetSizer().Add( ui.control, 1, wx.EXPAND )
        
    def _state_changed ( self, state ):
        """ Handles the control 'state' being changed.
        """
        self.theme = getattr( self.canvas.adapter, 'get_theme_' + state )(
                              self.object )
                              
        # If we have been activate, make sure we are on top of every other item:                              
        if state == 'active':
            self.control.Raise()
                              
    def _theme_changed ( self, theme ):
        """ Handles the 'theme' trait being changed.
        """
        super( ListCanvasItem, self )._theme_changed( theme )
        
        control = self.control
        if control is not None:
            self.ui.control.SetBackgroundColour( control.GetBackgroundColour() )
            
    @on_trait_change( 'title' )
    def _on_update ( self ):
        """ Handles a trait changing that requires the item to be refreshed on
            the display.
        """
        self.refresh()
        
    #-- Mouse Event Handlers ---------------------------------------------------
        
    def active_motion ( self, x, y, event ):
        """ Handles a mouse motion event while in the active state.
        """
        self._set_cursor( x, y )
        
    def active_left_down ( self, x, y, event ):
        """ Handles the user pressing the left mouse button while in the active
            state.
        """
        mode = self._set_cursor( x, y )
        if mode > 0:
            self.control.ReleaseMouse()
            self.canvas.begin_drag( self, mode, x, y )
        
    def active_left_up ( self, x, y, event ):
        """ Handles the user releasing the left mouse button while in the active
            state.
        """
        self._drag_mode = None
        self._set_cursor( x, y )
    
    def inactive_motion ( self, x, y, event ):
        """ Handles a mouse motion event while in the inactive state.
        """
        self.state = 'hover'
        self.control.CaptureMouse()
        self._set_cursor( x, y )
        
    def hover_motion ( self, x, y, event ):
        """ Handles a mouse motion event while in the hover state.
        """
        if not self.in_control( x, y ):
            self.state = 'inactive'
            self.control.ReleaseMouse()
            return
            
        self._set_cursor( x, y )
        
    def hover_left_down ( self, x, y, event ):
        """ Handles the user pressing the left mouse button while in the 
            inactive state.
        """
        self.canvas.activate( self )
        self.control.ReleaseMouse()
        self.active_left_down( x, y, event )
 
    #-- wx.Python Event Handlers -----------------------------------------------
           
    def _paint ( self, event ):
        """ Paint the background using the associated ImageSlice object.
        """
        global images
        
        # Note that we specifically skip our parent class's method 
        # implementation since it doesn't quite do what we want. So we just use
        # it's parent class's implementation:
        dc, slice = super( ImagePanel, self )._paint( event )
        
        # Draw each item in the layout dictionary:
        for name, bounds in self.layout.items():
            x, y, dx, dy = bounds
            
            # If the item is for item's title:
            if name == 'title':
                # Display it as text:
                title = self.title.strip()
                if self.title != '':
                    dc.SetBackgroundMode( wx.TRANSPARENT )
                    dc.SetTextForeground( slice.text_color )
                    dc.SetFont( self.control.GetFont() )
                    # fixme: Might need to set clipping region here...
                    dc.DrawText( title, x, y )
            else:
                # Otherwise, display the item's bitmap:
                dc.DrawBitmap( images[ name ], x, y, True )
        
    def _size ( self, event ):
        """ Handles the control being resized.
        """
        self._layout()
        
        super( ListCanvasItem, self )._size( event )

    #-- Private Methods --------------------------------------------------------
   
    def _set_cursor ( self, x, y ):
        """ Sets the correct mouse cursor for a specified mouse position.
        """
        n      = 4
        cursor = wx.CURSOR_ARROW
        dx, dy = self.size
        mode   = 0
        if (x >= 0) and (x < dx) and (y >= 0) and (y < dy):
            adapter = self.canvas.adapter
            
            # Check if the pointer is in a valid 'resize' position:
            if adapter.get_can_resize( self.object ):
                if x < n:
                    cursor = wx.CURSOR_SIZEWE
                    mode   = 5
                    if y < n:
                        cursor = wx.CURSOR_SIZENWSE
                        mode   = 15
                    elif y >= (dy - n):
                        cursor = wx.CURSOR_SIZENESW
                        mode   = 7
                elif x >= (dx - n):
                    cursor = wx.CURSOR_SIZEWE
                    mode   = 1
                    if y < n:
                        cursor = wx.CURSOR_SIZENESW
                        mode   = 11
                    elif y >= (dy - n):
                        cursor = wx.CURSOR_SIZENWSE
                        mode   = 3
                elif (y < n) or (y >= (dy - n)):
                    cursor = wx.CURSOR_SIZENS
                    mode   = 2
                    if y < n:
                        mode = 10
                 
            # If not, check if the pointer is in a valid 'move' position:
            if (mode == 0) and adapter.get_can_move( self.object ):
                slice = self.theme.image_slice
                if (y < slice.xtop) or (y >= (dy - slice.xbottom)):
                    mode = 12
                
        self.control.SetCursor( get_cursor( cursor ) )
        
        return mode
        
    def _layout ( self ):
        """ Lays out the contents of the item's title bar.
        """
        self.layout = {}
        tdx, tdy, descent, leading = self.control.GetFullTextExtent( 'Myj' )
        theme = self.theme
        slice = theme.image_slice
        tdy  += 4
        if (tdy <= slice.xtop) or (tdy <= slice.xbottom):
            wdx, wdy = self.control.GetClientSizeTuple()
            ox, oy   = theme.offset
            if tdy <= slice.xtop:
                ty = oy + ((slice.xtop - tdy + 4) / 2)
                ay = (2 * oy) + slice.xtop
            else:
                ty = oy + wdy - ((slice.xbottom + tdy + 4) / 2)
                ay = (2 * (oy + wdy)) - slice.xbottom
            
            xl = ox + slice.xleft
            xr = ox + wdx - slice.xright
                
            adapter = self.canvas.adapter
            object  = self.object

            # fixme: Add support for the 'feature' button...
            if adapter.get_can_delete( object ):
                xr = self._layout_button( 'close', xr, ay )
                
            xr = self._layout_button( 'minimize', xr, ay )
            
            if adapter.get_can_drag( object ):
                xr = self._layout_button( 'drag', xr, ay )
                
            if adapter.get_can_clone( object ):
                xr = self._layout_button( 'clone', xr, ay )
            # fixme: Add support for the 'select' button...
            
            # Add the layout information for the title:
            self.layout[ 'title' ] = ( xl, ty, xr - xl, tdy - 4 )
            
    def _layout_button ( self, name, x, y, direction = -1 ):
        """ Lays out the position of an image button.
        """
        global images
        
        bm = images[ name ]
        if isinstance( bm, ImageResource ):
            images[ name ] = bm = bm.create_image().ConvertToBitmap()
            
        dx = bm.GetWidth()
        dy = bm.GetHeight()
        
        if direction < 0:
            x -= dx
            rx = x - 2
        else:
            rx = x + dx + 2
            
        self.layout[ name ] = ( x, (y - dy) / 2, dx, dy )
        
        return rx
    
#-------------------------------------------------------------------------------
#  'ListCanvas' class:
#-------------------------------------------------------------------------------

class ListCanvas ( ImagePanel ):
    """ Defines the main list canvas editor widget, which contains and manages
        all of the list canvas items.
    """

    #-- Private Traits ---------------------------------------------------------
    
    # Is the canvas scrollable?
    scrollable = Bool( False )
    
    # The current set of items on the canvas:
    items = List( ListCanvasItem )
    
    # The current active item (if any):
    active_item = Instance( ListCanvasItem )
    
    # The adapter used to control canvas operations:
    adapter = Instance( ListCanvasAdapter )
   
    # The snapping information to use:
    snap_info = Instance( SnapInfo, () )
    
    # The guide line information to use:
    guide_info = Instance( GuideInfo, () )
    
    # The grid information to use:
    grid_info = Instance( GridInfo, () )

    # What operations are allowed on the list canvas:
    operations = CanvasOperations
    
    # The list of classes that can be added to the canvas using the canvas
    # toolbar and/or context menu:
    add = List
    
    # The current position of the canvas:
    position = Property
    
    # The current size of the canvas:
    size = Property
    
    # The wx Control acting as the list canvas:
    canvas = Instance( wx.Window )
    
    #-- Public Methods ---------------------------------------------------------
    
    def create_control ( self, parent, scrollable = False ):
        """ Creates the underlying wx.Panel control.
        """
        control = super( ListCanvas, self ).create_control( parent )
        
        self.scrollable = scrollable
        if scrollable:
            self.canvas = canvas = wx.ScrolledWindow( control )
            canvas.SetScrollRate( 1, 1 )
            canvas.SetMinSize( wx.Size( 0, 0 ) )
        else:
            self.canvas = canvas = wx.Panel( control, -1, 
                                           style = wx.TAB_TRAVERSAL          |
                                                   wx.FULL_REPAINT_ON_RESIZE | 
                                                   wx.CLIP_CHILDREN )
                                                   
        canvas.SetBackgroundColour( control.GetBackgroundColour() )
                                                   
        # Initialize the wx event handlers for the canvas control:                                                   
        init_wx_handlers( self.canvas, self, 'canvas' )                                                   
            
        control.GetSizer().Add( self.canvas, 1, wx.EXPAND )
        
        return control
        
    def create_object ( self, object ):
        """ Creates a specified HasTraits object as a new list canvas item.
        """ 
        return ListCanvasItem( canvas = self ).set( object = object )
        
    def replace_items ( self, items = [], i = 0, j = -1 ):
        """ Replaces the [i:j] items in the current items list with the 
            specified set of replacement items.
        """
        self_items = self.items
        
        # If 'j' was not specified, replace all items until the end of the list:
        if j < 0:
            j = len( self_items )
        
        # If the currently active item is in the group being deleted, then
        # indicate that there is no active item currently:
        if self.active_item in self_items[i:j]:
            self.active_item = None
            
        # Destroy all items being removed from the list:
        for item in self_items[i:j]:
            item.dispose()
            
        # Delete the removed items from the list:
        del self_items[i:j]
        
        # Initialize each item's position, then add it to the list:
        for item in items:
            item.initialize_position()
            self_items.insert( i, item )
            i += 1
            
        # Update the canvas bounds (if necessary):
        self._adjust_size()
        
    def initial_position_for ( self, dx, dy ):
        """ Returns the initial position for an item of the specified width and
            height.
        """
        xmax = ymax = ynext = 0
        cdx, cdy = self.size
        
        for item in self.items:
            x, y     = item.position
            idx, idy = item.size
            if y > ymax:
                xmax, ymax, ynext = x + idx, y, y + idy
            elif y == ymax:
                xmax  = max( xmax, x + idx )
                ynext = max( ynext, y + idy )
        
        if (xmax + dx) > cdx:
            ymax = ynext
            xmax = 0
            
        return ( xmax, ymax )
        
    def activate ( self, item ):
        """ Activates a specified list canvas item.
        """
        # If there is actually a change in the current active item:
        active_item = self.active_item
        if item is not active_item:
            
            # Deactivate the previous active item (if any):
            if active_item is not None:
                active_item.state = 'inactive'
                self.adapter.set_deactivated( active_item.object ) 
                
            # Active the new item (if any):
            self.active_item = item
            if item is not None:
                item.state = 'active'
                self.adapter.set_activated( item.object )
                
    def begin_drag ( self, item, mode, x, y ):
        """ Handles a drag operation for a specified list item.
        """
        x, y            = self._event_xy( x, y )
        x0, y0          = item.position
        dx, dy          = item.size
        x1, y1          = self.position
        self._drag_item = item
        self._drag_info = ( mode, x0, y0, dx, dy, x0 + x1 + x, y0 + y1 + y )
        self.state      = 'dragging'
        if (self.snap_info.distance > 0) and self.guide_info.snapping:
            self._drag_guides = self._guide_lines()
        self.control.CaptureMouse()
        self._refresh_canvas_drag( True )
        
    def snap_x ( self, x, dx ):
        """ Adjust an x-coordinate to take into account any grid or guide line
            snapping in effect.
        """
        # If snapping distance is 0, then it is effectively turned off, so just
        # return the original delta:
        snap = self.snap_info.distance
        if snap == 0:
            return dx
            
        # Compute the adjusted x-coordinate:
        xt = x + dx
        
        # Check to see if grid snapping is allowed:
        gi = self.grid_info
        if gi.snapping:
            
            # Compute the nearest grid point to the left of the point:
            n  = (xt - gi.offset) / gi.size
            x0 = (n * gi.size) + gi.offset
            
            # If it is within snapping distance, return the snapped delta:
            if abs( xt - x0 ) <= snap:
                return (x0 - x)
                
            # Compute the nearest grid point to the right of the point:
            x0 += gi.size
            
            # If it is within snapping distance, return the snapped delta:
            if abs( xt - x0 ) <= snap:
                return (x0 - x)
                
        # Check to see if guide line snapping is allowed:
        if self.guide_info.snapping:
            xs, ys = self._drag_guides
            
            # Check to see if the point is within snapping distance of any of
            # the guide lines:
            for x0 in xs.keys():
                delta = abs( xt - x0 )
                if delta <= snap:
                    snap = delta
                    dx   = x0 - x
                
        # Return the delta:
        return dx
        
    def snap_y ( self, y, dy ):
        """ Adjust an y-coordinate to take into account any grid or guide line
            snapping in effect.
        """
        # If snapping distance is 0, then it is effectively turned off, so just
        # return the original delta:
        snap = self.snap_info.distance
        if snap == 0:
            return dy
            
        # Compute the adjusted x-coordinate:
        yt = y + dy
        
        # Check to see if grid snapping is allowed:
        gi = self.grid_info
        if gi.snapping:
            
            # Compute the nearest grid point above the point:
            n  = (yt - gi.offset) / gi.size
            y0 = (n * gi.size) + gi.offset
            
            # If it is within snapping distance, return the snapped delta:
            if abs( yt - y0 ) <= snap:
                return (y0 - y)
                
            # Compute the nearest grid point below the point:
            y0 += gi.size
            
            # If it is within snapping distance, return the snapped delta:
            if abs( yt - y0 ) <= snap:
                return (y0 - y)
                
        # Check to see if guide line snapping is allowed:
        if self.guide_info.snapping:
            xs, ys = self._drag_guides
            
            # Check to see if the point is within snapping distance of any of
            # the guide lines:
            for y0 in ys.keys():
                delta = abs( yt - y0 )
                if delta <= snap:
                    snap = delta
                    dy   = y0 - y
                
        # Return the delta:
        return dy        
        
    #-- Property Implementations -----------------------------------------------
    
    def _get_position ( self ):
        return self.canvas.GetPositionTuple()
        
    def _get_size ( self ):
        return self.canvas.GetSizeTuple()
        
    #-- Trait Event Handlers ---------------------------------------------------
    
    @on_trait_change( 'snap_info.+, grid_info.+, guide_info.+' )
    def _on_canvas_changed ( self ):
        """ Handles any trait change that affects the appearance of the
            canvas.
        """
        self._refresh_canvas()
        
    #-- Mouse Event Handlers ---------------------------------------------------
    
    def dragging_motion ( self, x, y, event ):
        """ Handles one of the list items being moved or resized.
        """
        x, y = self._event_xy( x, y )
        mode, x0, y0, dx, dy, xo, yo = self._drag_info
        self._drag_item.resize( mode, x0, y0, dx, dy, x - xo, y - yo )
        
    def dragging_left_up ( self, x, y, event ):
        """ Handles the left mouse button being released while moving or
            resizing a list item.
        """
        self._drag_item = self._drag_guides = None 
        self.state      = 'normal'
        self._refresh_canvas_drag( False )
        
        # Refresh all canvas items:
        self._refresh_items()
        
        # Update the canvas size:
        self._adjust_size()
        
    #-- Other wx Event Handlers ------------------------------------------------
    
    def canvas_erase_background ( self, event ):
        """ Do not erase the background here (do it in the 'on_paint' handler).
        """
        pass
   
    def canvas_paint ( self, event ):
        """ Handles repainting the canvas.
        """
        # Set up to do the drawing:
        canvas   = self.canvas
        dc       = wx.PaintDC( canvas )
        wdx, wdy = canvas.GetClientSizeTuple()
        if self.scrollable:
            canvas.DoPrepareDC( dc )
            vdx, vdy = canvas.GetVirtualSize()
            wdx, wdy = max( wdx, vdx ), max( wdy, vdy )
        
        # Draw the canvas background:
        dc.SetBrush( wx.Brush( canvas.GetBackgroundColour() ) )
        dc.SetPen( wx.TRANSPARENT_PEN )
        dc.DrawRectangle( 0, 0, wdx, wdy )
        
        # Draw the grid (if necessary):
        gi = self.grid_info
        if ((gi.visible == 'always') or
            ((gi.visible == 'drag') and (self.state == 'dragging'))):
            dc.SetPen( wx.Pen( gi.color_, 1, pen_styles[ gi.style ] ) )
            
            size   = gi.size
            offset = gi.offset % size
            for x in range( offset, wdx, size ):
                dc.DrawLine( x, 0, x, wdy )
                
            for y in range( offset, wdy, size ):
                dc.DrawLine( 0, y, wdx, y )
        
        # Draw the guide lines (if necessary):
        gi = self.guide_info
        if ((gi.visible == 'always') or
            ((gi.visible == 'drag') and (self.state == 'dragging')) and
            (len( self.items ) > 0)):
                
            # Determine the set of guide lines to draw:
            xs, ys = self._guide_lines()
            
            # Set up the pen for drawing guide lines:
            dc.SetPen( wx.Pen( gi.color_, 1, pen_styles[ gi.style ] ) )
            
            # Draw the x guide lines:
            for x in xs.keys():
                dc.DrawLine( x, 0, x, wdy )
                
            # Draw the y guide lines:
            for y in ys.keys():
                dc.DrawLine( 0, y, wdx, y )
                
    #-- Private Methods --------------------------------------------------------
    
    def _refresh_canvas ( self ):
        """ Refresh the contents of the canvas.
        """
        if self.canvas is not None:
            self.canvas.Refresh()
            
    def _refresh_canvas_drag ( self, start = True ):
        """ Refreshes the canvas at the beginning or end of a drag operation if
            necessary.
        """
        visible = self.guide_info.visible
        if ((self.grid_info.visible == 'drag') or
            (visible == 'drag') or ((not start) and (visible == 'always'))):
            self._refresh_canvas()
            
    def _refresh_items ( self ):
        """ Refresh all list items on the canvas.
        """
        for item in self.items:
            item.refresh()
        
    def _guide_lines ( self ):
        """ Returns the x and y coordinates for all guide lines.
        """
        dx, dy    = self.size
        xs        = { 0: None, dx - 1: None }
        ys        = { 0: None, dy - 1: None }
        skip_item = self._drag_item
        for item in self.items:
            if item is not skip_item:
                x,  y  = item.position
                dx, dy = item.size
                xs[ x ]      = None
                ys[ y ]      = None
                xs[ x + dx ] = None
                ys[ y + dy ] = None
                    
        # Return the x and y coordinate dictionaries:
        return ( xs, ys )

    def _adjust_size ( self ):
        """ Adjusts the size of the canvas (if necessary).
        """
        if self.scrollable:
            xvs, yvs   = self.canvas.GetViewStart()
            xppu, yppu = self.canvas.GetScrollPixelsPerUnit()
            xvs       *= xppu
            yvs       *= yppu
            cdx = cdy  = 0
            for item in self.items:
                x,  y  = item.position
                dx, dy = item.size
                cdx    = max( cdx, x + dx + xvs )
                cdy    = max( cdy, y + dy + yvs )
                
            self.canvas.SetVirtualSize( ( cdx, cdy ) )

    def _event_xy ( self, x, y ):
        """ Returns the translated (x,y) coordinates for an event.
        """
        if not self.scrollable:
            return ( x, y )
            
        xvs, yvs = self.canvas.GetViewStart()
        dx, dy   = self.canvas.GetScrollPixelsPerUnit()
        return ( x + (xvs * dx), y + (yvs * dy) )
            
#-------------------------------------------------------------------------------
#  '_ListCanvasEditor' class:
#-------------------------------------------------------------------------------
                               
class _ListCanvasEditor ( Editor ):
    """ An editor for displaying list items as themed Traits UI Views on a 
        themed free-form canvas.
    """
    
    #-- Private Traits ---------------------------------------------------------
    
    # The list canvas used by the editor:
    list_canvas = Instance( ListCanvas, () )
    
    #---------------------------------------------------------------------------
    #  Trait definitions:  
    #---------------------------------------------------------------------------
        
    # Is the shell editor is scrollable? This value overrides the default.
    scrollable = True
    
    #-- Editor Method Overrides ------------------------------------------------
        
    def init ( self, parent ):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        factory = self.factory
        
        # Add all specified features to DockWindows:
        for feature in factory.features:
            add_feature( feature )
        
        # Create the underlying wx control:
        lc = self.list_canvas
        lc.set( **factory.get( 'theme', 'adapter', 'snap_info', 'guide_info',
                               'grid_info', 'operations', 'add' ) )
        self.control = lc.create_control( parent, factory.scrollable )
                     
        # Set up the additional 'list items changed' event handler needed for
        # a list based trait:
        self.context_object.on_trait_change( self.update_editor_item, 
                               self.extended_name + '_items?', dispatch = 'ui' )
                                                        
        # Add the developer specified tooltip information:
        self.set_tooltip()

    def update_editor ( self ):
        """ Updates the editor when the object trait changes externally to the
            editor.
        """
        if self._inited is None:
            self._inited = True
            do_later( self.update_editor )
            return
            
        lc = self.list_canvas
        lc.replace_items( [ lc.create_object( object ) 
                            for object in self.value ] ) 
                
    def dispose ( self ):
        """ Disposes of the contents of an editor.
        """
        self.list_canvas.replace_items()
        
        super( _ListCanvasEditor, self ).dispose()
     
    #-- Private Methods --------------------------------------------------------
    
    def update_editor_item ( self, event ):
        """ Updates the editor when an item in the object trait changes 
            externally to the editor.
        """
        lc = self.list_canvas
        lc.replace_items( [ lc.create_object( object )
                            for object in event.added ],
                          event.index, event.index + len( event.removed ) )

#-------------------------------------------------------------------------------
#  Create the editor factory object:
#-------------------------------------------------------------------------------

# wxPython editor factory for list canvas editors.
class ListCanvasEditor ( BasicEditorFactory ):
    
    # The class used to construct editor objects:
    klass = _ListCanvasEditor
    
    # The adapter used to control operations on the list canvas:
    adapter = Instance( ListCanvasAdapter, () )
    
    # The list of feature classes that items on the list canvas can support:
    features = List
    
    # The theme to use for the list canvas:
    theme = ATheme( '@G45' )
    
    # The snapping information to use for the list canvas:
    snap_info = Instance( SnapInfo, () )
    
    # The guide line information to use for the list canvas:
    guide_info = Instance( GuideInfo, () )
    
    # The grid information to use for the list canvas:
    grid_info = Instance( GridInfo, () )

    # What operations are allowed on the list canvas:
    operations = CanvasOperations
    
    # The list of classes that can be added to the canvas using the canvas
    # toolbar and/or context menu:
    add = List
    
    # Is the list canvas scrollable?
    scrollable = Bool( False )
    
#-- Test Case ------------------------------------------------------------------

if __name__ == '__main__':
    snap_info  = SnapInfo( distance = 8 )
    grid_info  = GridInfo( visible = 'always', snapping = False )
    guide_info = GuideInfo()
    
    class Person ( HasTraits ):
        name   = Str
        age    = Range( 0, 100 )
        gender = Enum( 'Male', 'Female' )
        
        view = View( 'name', 'age', 'gender' )
        
    class People ( HasTraits ):
        people = List
        
        view = View( 
            Item( 'people',
                  show_label = False,
                  editor = ListCanvasEditor( scrollable = True,
                                             snap_info  = snap_info,
                                             grid_info  = grid_info,
                                             guide_info = guide_info )
            ),
            title     = 'List Canvas Test',
            id        = 'enthought.traits.ui.wx.extra.list_canvas_editor',
            width     = 0.75,
            height    = 0.75,
            resizable = True 
        )
        
    people = [ 
        Person( name   = 'Nick Adams', 
                age    = 37,
                gender = 'Male' ),
        Person( name   = 'Joan Thomas',
                age    = 42,
                gender = 'Female' ),
        Person( name   = 'John Jones',
                age    = 27,
                gender = 'Male' ),
        Person( name   = 'Tina Gerlitz',
                age    = 51,
                gender = 'Female' ),
        snap_info, grid_info, guide_info
    ]
        
    People( people = people ).configure_traits()
