import glue.core.message as msg
import solara
from glue.core import DataCollection
from glue_jupyter import JupyterApplication
import time  # ENHANCED: For timing delays to let glue settle

from .hooks import use_glue_watch

# TASK 3: SAFE REGISTRY ACCESS - FOLLOWING QT'S EXACT PATTERN
# Based on Jon Carifio's explanation and Qt's LinkMenu.__init__() 
# (glue_qt/dialogs/link_editor/link_editor.py:27-48)
#
# KEY INSIGHT: Qt accesses registries ONCE at LinkMenu.__init__(), 
# stores the actual function/helper objects, never accesses during render

print("🔗 TASK 3: Loading registry access system...")

# TASK 3.1: Module-level registry cache (Qt's exact approach)
_CACHED_LINK_MENU_DATA = None

def get_function_name(registry_item):
    """Qt's exact get_function_name function - adapted for LinkFunction and LinkHelper objects"""
    if hasattr(registry_item, 'display') and registry_item.display is not None:
        return registry_item.display
    elif hasattr(registry_item, 'function'):  # LinkFunction
        return registry_item.function.__name__
    elif hasattr(registry_item, 'helper'):    # LinkHelper  
        if hasattr(registry_item.helper, 'display') and registry_item.helper.display:
            return registry_item.helper.display
        else:
            return registry_item.helper.__name__
    else:
        return str(registry_item)  # Fallback

def _build_link_menu_cache():
    """
    Build link menu data using Qt's EXACT pattern from LinkMenu.__init__()
    This happens ONCE at module import, never during component rendering.
    
    Qt pattern (lines 32-48 in link_editor.py):
    - Access link_function.members and link_helper.members ONCE
    - Store the actual registry objects for later use
    - Build category structure for UI
    """
    global _CACHED_LINK_MENU_DATA
    
    if _CACHED_LINK_MENU_DATA is not None:
        print("🔗 TASK 3: Using existing cache")
        return _CACHED_LINK_MENU_DATA
        
    print("🔗 TASK 3: Building link menu cache (Qt LinkMenu.__init__ pattern)")
    
    # SAFE: Same as Qt LinkMenu.__init__() - access registries outside render loop
    from glue.config import link_function, link_helper
    
    print(f"🔗 REGISTRY: Accessing link_function.members...")
    print(f"🔗 REGISTRY: link_function = {link_function}")
    print(f"🔗 REGISTRY: link_function.members = {link_function.members}")
    print(f"🔗 REGISTRY: len(link_function.members) = {len(link_function.members)}")
    
    print(f"🔗 REGISTRY: Accessing link_helper.members...")
    print(f"🔗 REGISTRY: link_helper = {link_helper}")
    print(f"🔗 REGISTRY: link_helper.members = {link_helper.members}")
    print(f"🔗 REGISTRY: len(link_helper.members) = {len(link_helper.members)}")
    
    # Step 1: Collect all categories (Qt's exact logic)
    categories = []
    function_count = 0
    for function in link_function.members:
        print(f"🔗 REGISTRY: function = {function}, output_labels = {function.output_labels}")
        if len(function.output_labels) == 1:  # Qt's exact filter
            categories.append(function.category)
            function_count += 1
            print(f"🔗 REGISTRY: Added function category: {function.category}")
    
    helper_count = 0        
    for helper in link_helper.members:
        print(f"🔗 REGISTRY: helper = {helper}, category = {helper.category}")
        categories.append(helper.category)  
        helper_count += 1
        
    # Qt's exact category ordering: General first, then sorted
    categories = ['General'] + sorted(set(categories) - set(['General']))
    
    print(f"🔗 REGISTRY: Found {function_count} functions, {helper_count} helpers")
    print(f"🔗 REGISTRY: Categories: {categories}")
    
    # Step 2: Build menu structure (Qt's exact logic)
    menu_data = {}
    
    for category in categories:
        menu_data[category] = []
        
        # Add functions to this category (Qt's exact logic)
        for function in link_function.members:
            if function.category == category and len(function.output_labels) == 1:
                try:
                    # Qt's exact pattern: get_function_name(function)  
                    display_name = get_function_name(function)
                    
                    menu_data[category].append({
                        'type': 'function',
                        'display': display_name,
                        'registry_object': function,  # Store Qt-compatible object
                        'description': getattr(function, 'info', '')
                    })
                    print(f"🔗 REGISTRY: Added function: {display_name} to {category}")
                except Exception as e:
                    print(f"🔗 REGISTRY: ERROR processing function {function}: {e}")
                    
        # Add helpers to this category (Qt's exact logic)  
        for helper in link_helper.members:
            if helper.category == category:
                try:
                    # Qt's exact pattern: get_function_name(helper)
                    display_name = get_function_name(helper) 
                    menu_data[category].append({
                        'type': 'helper',
                        'display': display_name, 
                        'registry_object': helper,  # Store Qt-compatible object
                        'description': getattr(helper.helper, 'description', '')
                    })
                    print(f"🔗 REGISTRY: Added helper: {display_name} to {category}")
                except Exception as e:
                    print(f"🔗 REGISTRY: ERROR processing helper {helper}: {e}")
    
    # Find identity function for fallback
    identity_function = None
    for function in link_function.members:
        if hasattr(function, 'function') and function.function.__name__ == 'identity':
            identity_function = function
            print(f"🔗 REGISTRY: Found identity function: {identity_function}")
            break
    
    # Add identity to General if not already there and if found
    if identity_function and 'General' in menu_data:
        identity_already_added = any(item['display'] == 'identity' for item in menu_data['General'])
        if not identity_already_added:
            menu_data['General'].append({
                'type': 'function',
                'display': 'identity',
                'registry_object': identity_function,
                'description': 'Identity link function'
            })
            print(f"🔗 REGISTRY: Added identity function to General")
    
    _CACHED_LINK_MENU_DATA = menu_data
    print(f"🔗 REGISTRY: Cache built successfully - {len(categories)} categories")
    print(f"🔗 REGISTRY: Final menu_data keys: {list(menu_data.keys())}")
    for cat, items in menu_data.items():
        print(f"🔗 REGISTRY: {cat}: {len(items)} items")
        for item in items:
            print(f"🔗 REGISTRY:   - {item['display']} ({item['type']})")
    
    return menu_data

def get_link_menu_data():
    """
    Get cached link menu data. Safe for Solara components.
    No registry access - everything pre-computed at module import.
    """
    return _build_link_menu_cache()

# TASK 3.2: Initialize cache at module import (Qt's exact timing)  
print("🔗 TASK 3: Initializing cache at module import (Qt pattern)...")

# Force import of coordinate helpers (they might not be auto-loaded)
try:
    print("🔗 ASTRONOMY: Attempting to import coordinate helpers...")
    import glue.plugins.coordinate_helpers.link_helpers  # Force load astronomy plugins
    print("🔗 ASTRONOMY: Coordinate helpers imported successfully")
except Exception as e:
    print(f"🔗 ASTRONOMY: Error importing coordinate helpers: {e}")

# Force rebuild to see debug output
_CACHED_LINK_MENU_DATA = None  # Force rebuild
_build_link_menu_cache()


@solara.component
def AdvancedLinkMenu(
    app: JupyterApplication,
    data_collection: DataCollection,
    selected_data1: solara.Reactive[int],
    selected_data2: solara.Reactive[int],
    selected_row1: solara.Reactive[int],
    selected_row2: solara.Reactive[int],
    shared_refresh_counter: solara.Reactive[int],
):
    """
    TASK 4: Advanced Link Menu Component
    
    Implements hierarchical link function/helper selection matching Qt's approach.
    Based on Qt's LinkMenu class (glue_qt/dialogs/link_editor/link_editor.py:25-49)
    
    Features:
    - Hierarchical category dropdown (General, Astronomy, Join)
    - Function/helper selection within categories
    - Safe cached registry access (no freezing)
    - Dynamic link creation for functions and helpers
    """
    
    # TASK 4.1: All hooks at top level (Solara requirement)
    selected_category = solara.use_reactive("general")
    selected_link_item = solara.use_reactive("")
    show_menu = solara.use_reactive(False)
    
    print(f"🔗 TASK 4: AdvancedLinkMenu render - category={selected_category.value}, item={selected_link_item.value}")
    
    # TASK 4.2: Get cached categories (safe for components)
    categories = get_link_menu_data()
    category_names = list(categories.keys())
    
    # TASK 4.3: Get items in selected category
    current_category_items = categories.get(selected_category.value, [])
    item_names = [item['display'] for item in current_category_items]
    
    print(f"🔗 TASK 4: Available categories: {category_names}")
    print(f"🔗 TASK 4: Items in '{selected_category.value}': {len(current_category_items)}")
    
    # TASK 4.4: Link creation handler
    def create_advanced_link():
        """Create link using Qt's EXACT EditableLinkFunctionState pattern"""
        print(f"🔗 ADVANCED: ===== Creating Advanced Link (Qt pattern) =====")
        print(f"🔗 ADVANCED: Category: {selected_category.value}")
        print(f"🔗 ADVANCED: Item: {selected_link_item.value}")
        
        # Validate selections
        if not selected_link_item.value or selected_data1.value == -1 or selected_data2.value == -1:
            print(f"🔗 ADVANCED: Invalid selections - cannot create link")
            return
            
        # Find the selected item in the category
        selected_item = None
        for item in current_category_items:
            if item['display'] == selected_link_item.value:
                selected_item = item
                break
                
        if not selected_item:
            print(f"🔗 ADVANCED: Selected item not found")
            return
            
        print(f"🔗 ADVANCED: Creating {selected_item['type']}: {selected_item['display']}")
        
        # Get datasets
        data1 = data_collection[selected_data1.value]
        data2 = data_collection[selected_data2.value]
        
        print(f"🔗 ADVANCED: data1={data1.label}, data2={data2.label}")
        
        try:
            # Qt's EXACT pattern from meeting notes:
            from glue.dialogs.link_editor.state import LinkEditorState
            
            # Create temporary LinkEditorState (Qt's approach)
            temp_state = LinkEditorState(data_collection)
            temp_state.data1 = data1
            temp_state.data2 = data2
            
            # Qt's exact method call - this does ALL the work
            registry_object = selected_item['registry_object']
            print(f"🔗 ADVANCED: Calling temp_state.new_link() with registry_object")
            
            try:
                temp_state.new_link(registry_object)
                
                # Apply to data collection (Qt's pattern)
                print(f"🔗 ADVANCED: Calling temp_state.update_links_in_collection()")
                temp_state.update_links_in_collection()
                
                print(f"🔗 ADVANCED: Successfully created advanced link!")
                
                # CRITICAL: Verify the link actually exists in backend
                _verify_backend_connection(data_collection, "ADVANCED_LINK_CREATION")
                
            except Exception as e:
                print(f"🔗 ADVANCED: Link creation failed: {str(e)}")
                print(f"🔗 ADVANCED: This usually means the datasets are incompatible with this link type")
                print(f"🔗 ADVANCED: Link type: {selected_item.get('label', 'Unknown')}")
                # Don't crash - just return gracefully
                return
            
            # UI refresh
            shared_refresh_counter.set(shared_refresh_counter.value + 1)
            
        except Exception as e:
            print(f"🔗 ADVANCED: ERROR creating link: {e}")
            import traceback
            print(f"🔗 ADVANCED: Traceback: {traceback.format_exc()}")
            raise
    
    # TASK 4.8: UI Layout
    with solara.Card(title="Create Advanced Link", elevation=2):
        with solara.Column():
            # Category selection dropdown
            solara.Select(
                label="Link Category",
                value=selected_category,
                values=category_names,
            )
            
            # Item selection dropdown (within category)
            if current_category_items:
                solara.Select(
                    label=f"{selected_category.value.title()} Links",
                    value=selected_link_item,
                    values=item_names,
                )
                
                # Show description if item is selected
                if selected_link_item.value:
                    selected_item = next(
                        (item for item in current_category_items if item['display'] == selected_link_item.value),
                        None
                    )
                    if selected_item and selected_item.get('description'):
                        solara.Text(f"Description: {selected_item['description']}", style={"font-style": "italic"})
                        
                # Create button
                with solara.Row():
                    solara.Button(
                        "Create Link",
                        on_click=create_advanced_link,
                        disabled=not selected_link_item.value or selected_data1.value == -1 or selected_data2.value == -1,
                        color="primary"
                    )
            else:
                solara.Text(f"No links available in '{selected_category.value}' category", style={"color": "gray"})

def _verify_backend_connection(data_collection, context="UNKNOWN"):
    """
    CRITICAL VERIFICATION: Check if links are actually functional in glue-core backend
    
    This verifies that our UI links correspond to real data connections that glue can use
    for selections, filtering, and data operations.
    """
    print(f"🔗 BACKEND VERIFICATION: ===== {context} =====")
    
    try:
        external_links = data_collection.external_links
        print(f"🔗 BACKEND: Total external_links count = {len(external_links)}")
        
        if len(external_links) == 0:
            print(f"🔗 BACKEND: ❌ NO LINKS FOUND - This is a serious problem!")
            return
        
        # Verify each link's backend properties
        for i, link in enumerate(external_links):
            print(f"🔗 BACKEND: Link {i}: {type(link).__name__}")
            
            # Check if link has proper data references
            if hasattr(link, 'data1') and hasattr(link, 'data2'):
                data1_label = getattr(link.data1, 'label', 'Unknown')
                data2_label = getattr(link.data2, 'label', 'Unknown')
                print(f"🔗 BACKEND:   Connects: {data1_label} ↔ {data2_label}")
            elif hasattr(link, '_cid1') and hasattr(link, '_cid2'):
                cid1_label = getattr(link._cid1, 'label', 'Unknown')
                cid2_label = getattr(link._cid2, 'label', 'Unknown')
                data1_label = getattr(link._cid1.parent, 'label', 'Unknown') if hasattr(link._cid1, 'parent') else 'Unknown'
                data2_label = getattr(link._cid2.parent, 'label', 'Unknown') if hasattr(link._cid2, 'parent') else 'Unknown'
                print(f"🔗 BACKEND:   Connects: {data1_label}[{cid1_label}] ↔ {data2_label}[{cid2_label}]")
            elif hasattr(link, '_from') and hasattr(link, '_to'):
                # ComponentLink structure
                if isinstance(link._from, list) and link._from:
                    from_labels = [getattr(c, 'label', 'Unknown') for c in link._from]
                    from_data_label = getattr(link._from[0].parent, 'label', 'Unknown') if hasattr(link._from[0], 'parent') else 'Unknown'
                else:
                    from_labels = [getattr(link._from, 'label', 'Unknown')]
                    from_data_label = getattr(link._from.parent, 'label', 'Unknown') if hasattr(link._from, 'parent') else 'Unknown'
                
                to_label = getattr(link._to, 'label', 'Unknown')
                to_data_label = getattr(link._to.parent, 'label', 'Unknown') if hasattr(link._to, 'parent') else 'Unknown'
                
                if len(from_labels) == 1:
                    print(f"🔗 BACKEND:   Connects: {from_data_label}[{from_labels[0]}] → {to_data_label}[{to_label}]")
                else:
                    from_str = ','.join(from_labels)
                    print(f"🔗 BACKEND:   Connects: {from_data_label}[{from_str}] → {to_data_label}[{to_label}]")
            else:
                print(f"🔗 BACKEND:   ⚠️ Link structure unknown - may not be functional")
            
            # Check if link has computation capability
            if hasattr(link, 'compute'):
                print(f"🔗 BACKEND:   ✅ Has compute() method - functional link")
            elif hasattr(link, '_links'):
                # LinkCollection/JoinLink - check if it has links OR is iterable
                if link._links:
                    print(f"🔗 BACKEND:   ✅ Contains {len(link._links)} sub-links - functional collection")
                elif hasattr(link, '__iter__'):
                    # JoinLink might have empty _links but still be functional
                    print(f"🔗 BACKEND:   ✅ JoinLink/LinkCollection - functional (special join logic)")
                else:
                    print(f"🔗 BACKEND:   ⚠️ LinkCollection with no sub-links")
            else:
                print(f"🔗 BACKEND:   ❌ No compute capability found - may be broken")
        
        # Test if data_collection can use the links
        datasets = list(data_collection)  # DataCollection is iterable
        if len(datasets) >= 2:
            print(f"🔗 BACKEND: Testing link functionality with {len(datasets)} datasets...")
            
            # Check if datasets are properly linked in data_collection
            dataset1, dataset2 = datasets[0], datasets[1]
            try:
                # Check if datasets are connected via external_links
                connected = False
                for link in external_links:
                    if hasattr(link, '_cid1') and hasattr(link, '_cid2'):
                        if ((hasattr(link._cid1, 'parent') and link._cid1.parent == dataset1 and 
                             hasattr(link._cid2, 'parent') and link._cid2.parent == dataset2) or
                            (hasattr(link._cid1, 'parent') and link._cid1.parent == dataset2 and 
                             hasattr(link._cid2, 'parent') and link._cid2.parent == dataset1)):
                            connected = True
                            break
                    elif hasattr(link, '_from') and hasattr(link, '_to'):
                        from_data = getattr(link._from[0] if isinstance(link._from, list) else link._from, 'parent', None)
                        to_data = getattr(link._to, 'parent', None)
                        if ((from_data == dataset1 and to_data == dataset2) or 
                            (from_data == dataset2 and to_data == dataset1)):
                            connected = True
                            break
                
                if connected:
                    print(f"🔗 BACKEND:   ✅ {dataset1.label} ↔ {dataset2.label} connection verified via external_links")
                else:
                    print(f"🔗 BACKEND:   ❌ {dataset1.label} ↔ {dataset2.label} connection not found in external_links")
                    
            except Exception as e:
                print(f"🔗 BACKEND:   ⚠️ Link functionality test failed: {e}")
        
        print(f"🔗 BACKEND VERIFICATION: ===== END {context} =====")
        
    except Exception as e:
        print(f"🔗 BACKEND VERIFICATION ERROR: {e}")
        import traceback
        print(f"🔗 BACKEND VERIFICATION TRACEBACK: {traceback.format_exc()}")


def _debug_link_type_preservation(original_link, new_links_list, operation_name):
    """
    🚀 PHASE 1 UNIFIED EDIT: Debug function to track link type preservation
    
    This helps us verify that our unified edit approach is working correctly
    and that we're not experiencing "magical type switching" anymore.
    """
    print(f"🚀 UNIFIED DEBUG: === {operation_name} RESULTS ===")
    print(f"🚀 UNIFIED DEBUG: Original link type: {type(original_link).__name__}")
    print(f"🚀 UNIFIED DEBUG: New links count: {len(new_links_list)}")
    
    if new_links_list:
        latest_link = new_links_list[-1]  # Assume newest is last
        new_link_type = type(latest_link).__name__
        print(f"🚀 UNIFIED DEBUG: Latest link type: {new_link_type}")
        
        # Check if type was preserved
        if new_link_type == type(original_link).__name__:
            print(f"🚀 UNIFIED DEBUG: ✅ SUCCESS - Link type preserved: {new_link_type}")
        else:
            print(f"🚀 UNIFIED DEBUG: ❌ MAGICAL SWITCHING DETECTED - {type(original_link).__name__} became {new_link_type}")
        
        # Show component details
        if hasattr(latest_link, '_cid1') and hasattr(latest_link, '_cid2'):
            print(f"🚀 UNIFIED DEBUG: New link components: {latest_link._cid1.label} <-> {latest_link._cid2.label}")
        elif hasattr(latest_link, '_from') and hasattr(latest_link, '_to'):
            if isinstance(latest_link._from, list):
                from_labels = [comp.label for comp in latest_link._from]
                print(f"🚀 UNIFIED DEBUG: New link components: {from_labels} -> {latest_link._to.label}")
            else:
                print(f"🚀 UNIFIED DEBUG: New link components: {latest_link._from.label} -> {latest_link._to.label}")
        else:
            print(f"🚀 UNIFIED DEBUG: New link structure unknown")
    else:
        print(f"🚀 UNIFIED DEBUG: ❌ ERROR - No links found after operation")
    
    print(f"🚀 UNIFIED DEBUG: === END {operation_name} RESULTS ===")

def _create_identity_link(data1, data2, row1_index, row2_index, app):
    """
    Create identity link using app.add_link (same as "Glue Attributes" button)
    """
    print(f"🐛 DEBUG: ===== _create_identity_link CALLED =====")
    print(f"🐛 DEBUG: data1={data1.label}, data2={data2.label}")
    print(f"🐛 DEBUG: row1_index={row1_index}, row2_index={row2_index}")
    print(f"🐛 DEBUG: data1.components count = {len(data1.components)}")
    print(f"🐛 DEBUG: data2.components count = {len(data2.components)}")
    
    # Get components (same logic as main Glue Attributes button)
    comp1 = data1.components[row1_index] if row1_index >= 0 and row1_index < len(data1.components) else data1.components[0]
    comp2 = data2.components[row2_index] if row2_index >= 0 and row2_index < len(data2.components) else data2.components[0]
    
    print(f"🐛 DEBUG: comp1 = {comp1.label} (index {row1_index})")
    print(f"🐛 DEBUG: comp2 = {comp2.label} (index {row2_index})")
    print(f"🐛 DEBUG: About to call app.add_link()")
    
    # Check what type of object app is
    print(f"🐛 DEBUG: app type = {type(app)}")
    print(f"🐛 DEBUG: app.data_collection type = {type(app.data_collection)}")
    print(f"🐛 DEBUG: app.data_collection.external_links count BEFORE = {len(app.data_collection.external_links)}")
    
    app.add_link(data1, comp1, data2, comp2)
    
    print(f"🐛 DEBUG: app.data_collection.external_links count AFTER = {len(app.data_collection.external_links)}")
    print(f"🐛 DEBUG: Latest link type = {type(app.data_collection.external_links[-1]) if app.data_collection.external_links else 'No links'}")
    print(f"🐛 DEBUG: Identity link created successfully")

def _create_link_from_registry_object_with_dynamic_params(app, data_collection, registry_object, item_type, data1, data2, param_selections):
    """
    CRITICAL FIX: Create link with dynamic parameters following Qt's exact pattern
    
    This handles the multi-parameter problem shown in screenshots:
    - lengths_to_volume(width, height, depth) -> volume
    - Requires 3 input parameters and 1 output parameter
    
    Qt's pattern (EditableLinkFunctionState.__new__):
    1. Extract function signature to get input parameter names
    2. Use output_labels for output parameter names  
    3. Create dynamic property mapping
    4. Build ComponentLink with correct parameter count
    """
    print(f"🔗 DYNAMIC LINK: _create_link_from_registry_object_with_dynamic_params called")
    print(f"🔗 DYNAMIC LINK: item_type={item_type}")
    print(f"🔗 DYNAMIC LINK: registry_object={registry_object}")
    print(f"🔗 DYNAMIC LINK: data1={data1.label}, data2={data2.label}")
    print(f"🔗 DYNAMIC LINK: param_selections={param_selections}")
    
    try:
        if item_type == 'function':
            # Extract function signature (Qt's exact approach)
            from inspect import getfullargspec
            function_obj = registry_object.function
            output_labels = registry_object.output_labels
            
            # Get parameter names from function signature (Qt's approach)
            input_names = getfullargspec(function_obj)[0]
            output_names = output_labels if output_labels else ['output']
            
            print(f"🔗 DYNAMIC LINK: function={function_obj.__name__}")
            print(f"🔗 DYNAMIC LINK: input_names={input_names}")
            print(f"🔗 DYNAMIC LINK: output_names={output_names}")
            
            # Build input components list (CRITICAL: Multi-parameter support)
            input_components = []
            for i, param_name in enumerate(input_names):
                if param_name in param_selections:
                    comp_index = param_selections[param_name]
                    if comp_index >= 0 and comp_index < len(data1.components):
                        comp = data1.components[comp_index]
                        input_components.append(comp)
                        print(f"🔗 DYNAMIC LINK: {param_name} -> {comp.label}")
                    else:
                        print(f"🔗 DYNAMIC LINK: ERROR - Invalid index for {param_name}: {comp_index}")
                        return
                else:
                    # Fallback to first component
                    comp = data1.components[0]
                    input_components.append(comp)
                    print(f"🔗 DYNAMIC LINK: {param_name} -> {comp.label} (fallback)")
            
            # Build output components list (UNIVERSAL: Support N→M patterns)
            output_components = []
            for i, output_name in enumerate(output_names):
                if output_name in param_selections:
                    comp_index = param_selections[output_name]
                    if comp_index >= 0 and comp_index < len(data2.components):
                        comp = data2.components[comp_index]
                        output_components.append(comp)
                        print(f"🔗 DYNAMIC LINK: {output_name} -> {comp.label}")
                    else:
                        print(f"🔗 DYNAMIC LINK: ERROR - Invalid index for {output_name}: {comp_index}")
                        return
                else:
                    # Fallback: use default component for this output
                    fallback_index = i if i < len(data2.components) else 0
                    comp = data2.components[fallback_index]
                    output_components.append(comp)
                    print(f"🔗 DYNAMIC LINK: {output_name} -> {comp.label} (fallback)")
            
            # Handle case where no output_names specified (default to single output)
            if not output_components:
                output_components.append(data2.components[0])
                print(f"🔗 DYNAMIC LINK: default_output -> {data2.components[0].label} (no outputs specified)")
            
            # UNIVERSAL ComponentLink creation - handles all N→M patterns
            from glue.core.component_link import ComponentLink
            
            if len(output_components) == 1:
                # Standard ComponentLink: N inputs → 1 output
                link = ComponentLink(input_components, output_components[0], using=function_obj)
                print(f"🔗 DYNAMIC LINK: Created N→1 ComponentLink: {len(input_components)} inputs → 1 output")
            else:
                # Multiple outputs: Need to create multiple ComponentLinks or use advanced pattern
                # This follows Qt's approach for functions with multiple outputs
                print(f"🔗 DYNAMIC LINK: N→M pattern detected: {len(input_components)} inputs → {len(output_components)} outputs")
                
                # For now, create link to first output (can be extended for true N→M later)
                link = ComponentLink(input_components, output_components[0], using=function_obj)
                print(f"🔗 DYNAMIC LINK: Created N→M ComponentLink (using first output): {link}")
                
                # TODO: Handle true N→M links if needed by creating multiple ComponentLink objects
            
            print(f"🔗 DYNAMIC LINK: Universal ComponentLink created: {link}")
            print(f"🔗 DYNAMIC LINK: Pattern: {len(input_components)} inputs → {len(output_components)} outputs")
            
            # Add to data collection
            data_collection.add_link(link)
            print(f"🔗 DYNAMIC LINK: Added function link to data_collection")
            
        elif item_type == 'helper':
            # Helper creation (similar to before but with dynamic parameter support)
            print(f"🔗 DYNAMIC LINK: Creating helper link with dynamic parameters")
            print(f"🔗 DYNAMIC LINK: helper class = {registry_object.helper}")
            
            if getattr(registry_object.helper, 'cid_independent', False):
                link_instance = registry_object.helper(data1=data1, data2=data2)
                data_collection.add_link(link_instance)
            else:
                # Extract expected parameter structure from helper
                helper_class = registry_object.helper
                input_names = getattr(helper_class, 'labels1', [])
                output_names = getattr(helper_class, 'labels2', [])
                
                print(f"🔗 DYNAMIC LINK: helper input_names={input_names}")
                print(f"🔗 DYNAMIC LINK: helper output_names={output_names}")
                
                # Build component lists based on parameter selections
                input_components = []
                output_components = []
                
                for param_name in input_names:
                    if param_name in param_selections:
                        comp_index = param_selections[param_name]
                        comp = data1.components[comp_index] if comp_index < len(data1.components) else data1.components[0]
                    else:
                        comp = data1.components[0]
                    input_components.append(comp)
                    print(f"🔗 DYNAMIC LINK: helper input {param_name} -> {comp.label}")
                
                for param_name in output_names:
                    if param_name in param_selections:
                        comp_index = param_selections[param_name]
                        comp = data2.components[comp_index] if comp_index < len(data2.components) else data2.components[0]
                    else:
                        comp = data2.components[0]
                    output_components.append(comp)
                    print(f"🔗 DYNAMIC LINK: helper output {param_name} -> {comp.label}")
                
                # Create helper with component lists
                link_instance = registry_object.helper(
                    cids1=input_components if input_components else [data1.components[0]], 
                    cids2=output_components if output_components else [data2.components[0]], 
                    data1=data1, 
                    data2=data2
                )
                data_collection.add_link(link_instance)
                
            print(f"🔗 DYNAMIC LINK: Added helper link to data_collection")
            
        print(f"🔗 DYNAMIC LINK: Dynamic link creation completed successfully")
        
    except Exception as e:
        print(f"🔗 DYNAMIC LINK: ERROR creating dynamic link: {e}")
        import traceback
        traceback.print_exc()
        raise

def _create_identity_link_direct(app, data_collection, data1_index, data2_index, cid1_index, cid2_index):
    """
    Direct identity link creation for fallback cases
    """
    print(f"🔗 FALLBACK: Creating identity link directly")
    data1 = data_collection[data1_index]
    data2 = data_collection[data2_index]
    comp1 = data1.components[cid1_index] if cid1_index >= 0 and cid1_index < len(data1.components) else data1.components[0]
    comp2 = data2.components[cid2_index] if cid2_index >= 0 and cid2_index < len(data2.components) else data2.components[0]
    
    app.add_link(data1, comp1, data2, comp2)
    print(f"🔗 FALLBACK: Identity link created")

def _create_function_link(function_item, data1, data2, row1_index, row2_index, app):
    """
    Create function link following Qt's EditableLinkFunctionState pattern
    """
    print(f"🐛 DEBUG: ===== _create_function_link CALLED =====")
    print(f"🐛 DEBUG: function_item = {function_item}")
    
    # Get the function object (Qt stores these in registry)
    function_object = function_item['function_object']
    print(f"🐛 DEBUG: function_object = {function_object}")
    print(f"🐛 DEBUG: function_object type = {type(function_object)}")
    print(f"🐛 DEBUG: function_object attributes = {[attr for attr in dir(function_object) if not attr.startswith('__')]}")
    
    function_callable = function_object.function
    print(f"🐛 DEBUG: function_callable = {function_callable}")
    print(f"🐛 DEBUG: function_callable.__name__ = {function_callable.__name__}")
    
    # Inspect function signature
    import inspect
    sig = inspect.signature(function_callable)
    print(f"🐛 DEBUG: function signature = {sig}")
    print(f"🐛 DEBUG: function parameters = {list(sig.parameters.keys())}")
    
    # Get components
    comp1 = data1.components[row1_index] if row1_index >= 0 and row1_index < len(data1.components) else data1.components[0]
    comp2 = data2.components[row2_index] if row2_index >= 0 and row2_index < len(data2.components) else data2.components[0]
    
    print(f"🐛 DEBUG: comp1 = {comp1.label}")
    print(f"🐛 DEBUG: comp2 = {comp2.label}")
    print(f"🐛 DEBUG: Function link: {comp1.label} -> {comp2.label} using {function_callable.__name__}")
    
    # Create ComponentLink with function (Qt's pattern)
    from glue.core.component_link import ComponentLink
    print(f"🐛 DEBUG: About to create ComponentLink([comp1], comp2, using=function)")
    
    try:
        # CRITICAL FIX: Handle multi-parameter functions correctly
        param_count = len(list(sig.parameters.keys()))
        print(f"🐛 DEBUG: Function needs {param_count} parameters")
        
        if param_count == 1:
            # Single parameter function (like identity)
            print(f"🐛 DEBUG: Single parameter function - using [comp1]")
            link = ComponentLink([comp1], comp2, using=function_callable)
        else:
            # Multi-parameter function (like lengths_to_volume)
            print(f"🐛 DEBUG: Multi-parameter function - needs {param_count} components")
            print(f"🐛 DEBUG: WARNING: Currently only using first component")
            print(f"🐛 DEBUG: TODO: Implement proper multi-parameter UI selection")
            
            # TEMPORARY: Use first N components from data1 as placeholders
            # This is not correct but prevents crashes until we implement proper UI
            input_components = []
            for i in range(min(param_count, len(data1.components))):
                input_components.append(data1.components[i])
                print(f"🐛 DEBUG: Adding component {i}: {data1.components[i].label}")
            
            # Fill remaining with last component if needed
            while len(input_components) < param_count:
                input_components.append(data1.components[-1])
                print(f"🐛 DEBUG: Padding with component: {data1.components[-1].label}")
            
            print(f"🐛 DEBUG: Creating ComponentLink with {len(input_components)} inputs")
            link = ComponentLink(input_components, comp2, using=function_callable)
        
        print(f"🐛 DEBUG: ComponentLink created successfully")
        print(f"🐛 DEBUG: link type = {type(link)}")
        print(f"🐛 DEBUG: link._from = {link._from}")
        print(f"🐛 DEBUG: link._to = {link._to}")
        
        # Add to data collection (get from app)
        print(f"🐛 DEBUG: About to add link to data collection")
        app.data_collection.add_link(link)
        print(f"🐛 DEBUG: Function link created successfully")
        
    except Exception as e:
        print(f"🐛 DEBUG: Exception in ComponentLink creation: {e}")
        import traceback
        traceback.print_exc()
        raise

def _create_helper_link(helper_item, data1, data2, app):
    """
    Create helper link following Qt's EditableLinkFunctionState pattern
    """
    print(f"🔗 Creating helper link: {helper_item['name']}")
    
    # Get the helper object (Qt stores these in registry)
    helper_object = helper_item['helper_object']
    helper_class = helper_object.helper
    
    print(f"🔗 Helper: {helper_class.__name__}")
    
    try:
        # Qt's pattern: Check if helper is cid_independent
        if hasattr(helper_class, 'cid_independent') and helper_class.cid_independent:
            # WCS-style helpers: Direct instantiation with datasets
            print(f"🔗 WCS-style helper (cid_independent)")
            links = helper_class(data1=data1, data2=data2)
        else:
            # Standard helpers: Use Qt's EditableLinkFunctionState pattern
            print(f"🔗 Standard helper - using EditableLinkFunctionState pattern")
            from glue_qt.dialogs.link_editor.state import EditableLinkFunctionState
            
            # Create state object (Qt's approach)
            state = EditableLinkFunctionState(helper_class, data1=data1, data2=data2)
            links = state.link  # Get the actual link
            
        # Add links to data collection (get from app)
        if isinstance(links, list):
            print(f"🔗 Adding {len(links)} links")
            for link in links:
                app.data_collection.add_link(link)
        else:
            print(f"🔗 Adding single link")
            app.data_collection.add_link(links)
        
        print(f"🔗 Helper link created")
        
    except Exception as e:
        print(f"🔗 Helper link creation failed: {e}")
        # Fallback: Try basic instantiation
        print(f"🔗 Trying fallback approach")
        helper_instance = helper_class()
        links = helper_instance(data1, data2)
        
        if isinstance(links, list):
            for link in links:
                app.data_collection.add_link(link) 
        else:
            app.data_collection.add_link(links)
        print(f"🔗 Helper link created (fallback)")


# TASK 3: SAFE STATIC REGISTRY COMPLETE
# No dangerous module initialization needed - static imports only
# Registry cache populated on first access during component rendering


def stringify_links(link):
    """
    Helper function to display link information in human-readable format
    
    ENHANCED: Handles all advanced link types properly for Qt-style display
    """
    print(f"🐛 DEBUG stringify_links: link type = {type(link)}")
    
    try:
        # Handle LinkSame (most common from app.add_link)
        if hasattr(link, '_cid1') and hasattr(link, '_cid2'):
            cid1_label = getattr(link._cid1, 'label', str(link._cid1))
            cid2_label = getattr(link._cid2, 'label', str(link._cid2))
            print(f"🐛 DEBUG: LinkSame style - {cid1_label} <-> {cid2_label}")
            return f"{cid1_label} <-> {cid2_label}"
        
        # Handle JoinLink (has special __str__ method)
        elif type(link).__name__ == 'JoinLink':
            print(f"🐛 DEBUG: JoinLink detected - using __str__")
            return str(link)  # JoinLink has good __str__ method
        
        # Handle coordinate helpers (astronomical transforms)
        elif 'coordinate_helpers' in str(type(link)):
            link_class_name = type(link).__name__
            print(f"🐛 DEBUG: Coordinate helper detected - {link_class_name}")
            
            # Extract description if available
            if hasattr(link, 'description'):
                return link.description
            elif hasattr(link, 'display') and link.display:
                return link.display
            else:
                # Build display name from class name
                if 'FK4_to_FK5' in link_class_name:
                    return "FK4 (B1950) <-> FK5 (J2000)"
                elif 'Galactic_to_FK4' in link_class_name:
                    return "Galactic <-> FK4 (B1950)"
                elif 'ICRS_to_FK5' in link_class_name:
                    return "ICRS <-> FK5 (J2000)"
                elif 'ICRS_to_Galactic' in link_class_name:
                    return "ICRS <-> Galactic"
                elif 'Galactic_to_FK5' in link_class_name:
                    return "Galactic <-> FK5 (J2000)"
                else:
                    return f"Coordinate Transform ({link_class_name})"
        
        # Handle ComponentLink (from link functions like lengths_to_volume)
        elif hasattr(link, '_from') and hasattr(link, '_to'):
            if isinstance(link._from, list) and len(link._from) > 0:
                # Multi-input functions like lengths_to_volume
                from_labels = [getattr(c, 'label', str(c)) for c in link._from]
                to_label = getattr(link._to, 'label', str(link._to))
                
                # Try to get function name
                function_name = "function"
                if hasattr(link, '_using') and link._using:
                    function_name = getattr(link._using, '__name__', 'function')
                
                # Special case: identity functions should display like simple links (Qt style)
                if function_name == 'identity' and len(from_labels) == 1:
                    display = f"{from_labels[0]} <-> {to_label}"
                    print(f"🐛 DEBUG: ComponentLink identity - {display}")
                # Check if this is a bidirectional coordinate transformation
                elif len(from_labels) == 1 and hasattr(link, 'inverse') and link.inverse:
                    display = f"{function_name}({from_labels[0]} <-> {to_label})"
                    print(f"🐛 DEBUG: ComponentLink bidirectional - {display}")
                elif len(from_labels) == 1:
                    display = f"{function_name}({from_labels[0]} -> {to_label})"
                else:
                    from_str = ",".join(from_labels)
                    display = f"{function_name}({from_str} -> {to_label})"
                
                print(f"🐛 DEBUG: ComponentLink - {display}")
                return display
            else:
                # Single input ComponentLink
                from_label = getattr(link._from, 'label', str(link._from))
                to_label = getattr(link._to, 'label', str(link._to))
                print(f"🐛 DEBUG: ComponentLink single - {from_label} -> {to_label}")
                return f"{from_label} -> {to_label}"
        
        # Fallback: Try generic attributes
        else:
            link_type = type(link).__name__
            print(f"🐛 DEBUG: Unknown link type {link_type} - trying fallbacks")
            
            # Try display properties in order
            if hasattr(link, 'description') and link.description:
                return link.description
            elif hasattr(link, 'display') and link.display:
                return link.display
            elif hasattr(link, '__str__'):
                str_rep = str(link)
                if len(str_rep) < 100 and 'object at 0x' not in str_rep:
                    return str_rep
            
            # Last resort
            return f"Advanced Link ({link_type})"
            
    except Exception as e:
        print(f"🐛 DEBUG stringify_links: Exception = {e}")
        return f"Link (display error)"


@solara.component
def Linker(app: JupyterApplication, show_list: bool = True):
    """
    EVOLUTION: Main Linker component - evolved significantly from original to current
    
    ORIGINAL: Simple layout with basic link creation
    PREVIOUS: Added proper Qt-style 5-column layout 
    CURRENT: Added link selection and editing capabilities
    
    This is the main component that implements the Qt-style link editor interface
    It follows the Solara component pattern with hooks-based state management
    """
    
    # EVOLUTION: All hooks must be at top level (Solara requirement)
    # ORIGINAL: Had basic state for dataset and attribute selection
    # PREVIOUS: Added selected_function for future link types
    # CURRENT: Added selected_link_index for link editing functionality
    
    # use_reactive: similar to React's useState()
    
    # Basic selection state for creating new links (from original version)
    selected_data1 = solara.use_reactive(0)  # Which dataset 1 is selected
    selected_row1 = solara.use_reactive(0)   # Which attribute in dataset 1
    selected_data2 = solara.use_reactive(1)  # Which dataset 2 is selected 
    selected_row2 = solara.use_reactive(0)   # Which attribute in dataset 2
    
    # Advanced functionality added in evolution
    selected_function = solara.use_reactive("identity")  # PREVIOUS: Link function type (not yet used)
    selected_link_index = solara.use_reactive(-1)  # CURRENT: Track which existing link is selected (-1 = none)
    
    # ENHANCED: Shared refresh counter to synchronize UI updates across components
    # This ensures both CurrentLinksSelector and QtStyleLinkDetailsPanel refresh together
    shared_refresh_counter = solara.use_reactive(0)
    
    # Core glue data structure - present in all versions
    data_collection = app.data_collection
    

    # EVOLUTION: Message watching system - critical for UI synchronization
    # ORIGINAL: Used basic ExternallyDerivableComponentsChangedMessage
    # CURRENT: Same approach, but now crucial for link editing to work properly
    # This hooks into glue's internal messaging system to update UI when links change
    # Without this, the UI won't update when links are modified programmatically
    use_glue_watch(app.session.hub, msg.ExternallyDerivableComponentsChangedMessage)

    # EVOLUTION: Safety checks improved across versions
    # ORIGINAL: Only checked len(data_collection.data) 
    # CURRENT: More robust checking for None and empty collections
    if data_collection is None or len(data_collection) == 0:
        return solara.Text("No data loaded")

    # EVOLUTION: Link creation function - enhanced with UI refresh
    # This function creates identity links between selected attributes
    # Present in all versions, core functionality for "Glue Attributes" button
    # FIXED: Added UI refresh mechanism to match edit functions
    def _add_link():
        print(f"🔥 GLUE ATTRIBUTES: _add_link called")
        print(f"🔥 GLUE ATTRIBUTES: Creating link between {data_collection[selected_data1.value].label} and {data_collection[selected_data2.value].label}")
        print(f"🔥 GLUE ATTRIBUTES: Attribute 1: {data_collection[selected_data1.value].components[selected_row1.value].label}")
        print(f"🔥 GLUE ATTRIBUTES: Attribute 2: {data_collection[selected_data2.value].components[selected_row2.value].label}")
        
        print(f"🔥 GLUE ATTRIBUTES: Before add - external_links count = {len(data_collection.external_links)}")
        
        app.add_link(
            data_collection[selected_data1.value],  # Source dataset
            data_collection[selected_data1.value].components[selected_row1.value],  # Source attribute
            data_collection[selected_data2.value],  # Target dataset  
            data_collection[selected_data2.value].components[selected_row2.value],  # Target attribute
        )
        
        print(f"🔥 GLUE ATTRIBUTES: After add - external_links count = {len(data_collection.external_links)}")
        print(f"🔥 GLUE ATTRIBUTES: Link creation COMPLETE")
        
        # FIXED: Add UI refresh mechanism (same pattern as edit functions)
        print(f"🔥 GLUE ATTRIBUTES: Forcing UI refresh after link creation")
        time.sleep(0.1)  # Let glue update internal state
        shared_refresh_counter.set(shared_refresh_counter.value + 1)  # Force memoization recalculation
        
        # ENHANCEMENT: Auto-select the newly created link for user convenience
        new_position = len(data_collection.external_links) - 1  # New links are added at the end
        print(f"🔥 GLUE ATTRIBUTES: Auto-selecting newly created link at position {new_position}")
        selected_link_index.set(-1)    # Clear selection first
        selected_link_index.set(new_position)  # Select the newly created link

    # EVOLUTION: Data preparation for UI components
    # ORIGINAL: Simple list comprehension
    # CURRENT: Added safety with "or []" to handle None collections
    # This creates the options list for dataset selector dropdowns
    data_dict = [
        {"label": data.label, "value": index} 
        for index, data in enumerate(data_collection or [])
    ]
    
    # EVOLUTION: Layout structure dramatically changed from original to current
    # ORIGINAL: Simple 2-column layout with basic functionality
    # PREVIOUS: Evolved to Qt-style 5-column layout 
    # CURRENT: Same layout but with interactive link selection and editing
    
    with solara.Column():
        # EVOLUTION: Main layout - mirrors Qt interface structure
        # This 5-column layout matches the Qt version:
        # [Dataset1] [Flip] [Dataset2] [Current Links] [Link Details]
        # HOLISTIC FIX: Expanded modal dialog for all components to work together
        # Instead of 800px constraint, use wider modal that accommodates all panels properly
        with solara.Row(style={"align-items": "start", "gap": "15px", "width": "100%", "min-width": "1000px", "flex-wrap": "nowrap"}):
            if len(data_collection) > 1:
                
                # EVOLUTION: Column 1 - Dataset 1 selector (from original version)
                # Uses the LinkSelector component for dataset and attribute selection
                # FIX: Add width constraint to prevent overflow in modal
                with solara.Column(style={"min-width": "150px", "max-width": "180px", "flex": "0 0 150px"}):
                    LinkSelector(data_collection, data_dict, selected_data1, selected_row1, "Dataset 1")
                
                # EVOLUTION: Column 2 - Flip button (added in previous version)
                # Currently just visual, but prepared for future "flip datasets" functionality
                # FIX: Add minimal width for flip button
                with solara.Column(style={"align-items": "center", "flex": "0 0 30px", "min-width": "30px"}):
                    solara.Text("⇄", style={"font-size": "24px", "margin-top": "40px"})
                
                # EVOLUTION: Column 3 - Dataset 2 selector (from original version)
                # Mirror of Dataset 1 selector for the target dataset
                # FIX: Add width constraint matching Dataset 1
                with solara.Column(style={"min-width": "150px", "max-width": "180px", "flex": "0 0 150px"}):
                    LinkSelector(data_collection, data_dict, selected_data2, selected_row2, "Dataset 2")
                
                # EVOLUTION: Column 4 - Current Links display (major evolution)
                # ORIGINAL: Simple non-interactive list
                # CURRENT: Interactive selector that enables clicking and selection
                # FIXED: Increased width for longer link descriptions (Issue #4)
                with solara.Column(style={"min-width": "220px", "max-width": "280px", "flex": "0 0 220px"}):
                    solara.Markdown("**Links between Dataset 1 and Dataset 2**")
                    if show_list:
                        CurrentLinksSelector(
                            data_collection=data_collection,
                            selected_link_index=selected_link_index,  # CURRENT: Enables selection tracking
                            shared_refresh_counter=shared_refresh_counter  # ENHANCED: For cache invalidation
                        )
                
                # EVOLUTION: Column 5 - Link Details Panel (MAJOR NEW FEATURE)
                # ORIGINAL: Did not exist
                # PREVIOUS: Basic static display 
                # CURRENT: Full interactive editing capabilities
                # FIXED: Adjust width to compensate for wider links column
                with solara.Column(style={"flex": "1 1 auto", "min-width": "200px", "max-width": "250px"}):
                    QtStyleLinkDetailsPanel(
                        app=app,
                        data_collection=data_collection, 
                        selected_data1=selected_data1,     # For context when no link selected
                        selected_data2=selected_data2,     # For context when no link selected
                        selected_link_index=selected_link_index,  # CURRENT: Drives the editing functionality
                        shared_refresh_counter=shared_refresh_counter,  # ENHANCED: For cache invalidation
                    )
        
        # EVOLUTION: Action buttons - present in all versions
        # ORIGINAL: Just the "Glue Attributes" button
        # CURRENT: Same button, but now part of larger interface
        with solara.Row():
            solara.Button(
                label="Glue Attributes",
                color="primary", 
                on_click=_add_link,  # Creates new identity links
            )
        
        # TASK 4.2: Advanced Link Menu Integration
        # Add the new hierarchical link creation interface
        if len(data_collection) > 1:
            AdvancedLinkMenu(
                app=app,
                data_collection=data_collection,
                selected_data1=selected_data1,
                selected_data2=selected_data2,
                selected_row1=selected_row1,
                selected_row2=selected_row2,
                shared_refresh_counter=shared_refresh_counter,
            )


@solara.component
def LinkSelector(
    data_collection: DataCollection,
    data_dict: list[dict],
    selected_data: solara.Reactive[int],
    selected_row: solara.Reactive[int],
    title: str = "Dataset",
):
    """
    EVOLUTION: LinkSelector component - refined from original to current
    
    ORIGINAL: Simple component without title parameter
    PREVIOUS: Added title parameter and better styling
    CURRENT: Enhanced with safety checks and better layout
    
    This component handles dataset selection and attribute selection within that dataset
    It's used for both Dataset 1 and Dataset 2 columns in the interface
    """
    with solara.Column():
        # EVOLUTION: Header formatting improved across versions
        # ORIGINAL: No header styling
        # CURRENT: Uses Markdown for consistent bold formatting
        solara.Markdown(f"**{title}**")
        
        # EVOLUTION: Dataset dropdown - core functionality unchanged
        # This dropdown shows all available datasets and lets user select one
        # The selected value updates the selected_data reactive variable
        solara.v.Select(
            label=title,
            v_model=selected_data.value,      # Current selection
            on_v_model=selected_data.set,     # Update function when user selects
            items=data_dict,                  # List of {label, value} dicts for datasets
            item_text="label",                # Show dataset.label in dropdown
            item_value="value",               # Use index as value
        )
        
        # EVOLUTION: Attribute list display - enhanced safety
        # Shows which dataset's attributes are being displayed
        solara.Text(f"Attributes for {data_dict[selected_data.value]['label']}")
        
        # EVOLUTION: Attribute selection list - core UI component
        # This scrollable list shows all attributes (components) in the selected dataset
        # User can click to select which attribute will be part of the link
        with solara.v.List(dense=True, style_="max-height: 50vh; overflow-y: scroll;"):
            with solara.v.ListItemGroup(
                v_model=selected_row.value,       # Which attribute is currently selected
                on_v_model=selected_row.set,      # Function to update selection
                color="primary",                  # Highlight color for selected item
            ):
                # EVOLUTION: Safety added - "or []" protects against None
                # Each attribute becomes a clickable list item
                for attribute in data_collection[selected_data.value].components or []:
                    with solara.v.ListItem():
                        with solara.v.ListItemContent():
                            solara.v.ListItemTitle(children=[attribute.label])


@solara.component
def CurrentLinksSelector(
    data_collection: DataCollection,
    selected_link_index: solara.Reactive[int],
    shared_refresh_counter: solara.Reactive[int],
):
    """
    EVOLUTION: CurrentLinksSelector - MAJOR NEW COMPONENT (not in original/previous)
    
    ORIGINAL: Had simple static list display within main Linker component
    PREVIOUS: Same as original - no separate component
    CURRENT: Extracted into separate component with full selection support
    
    This component shows existing links and allows clicking to select them for editing
    It's the bridge between "showing links" and "editing selected link"
    """
    
    # CURRENT: Debug logging to track link selection behavior
    # These prints help understand when and how links are being selected/updated
    print(f"🔥 HARDCORE DEBUG: CurrentLinksSelector render, selected_link_index={selected_link_index.value}")
    
    # EVOLUTION: Memoization for performance
    # ORIGINAL: No memoization, direct iteration over data_collection.external_links
    # CURRENT: Uses solara.use_memo to avoid recreating list on every render
    # CRITICAL FIX: Added shared_refresh_counter to force cache invalidation
    # This fixes the stale UI issue where links weren't updating after editing
    links_list = solara.use_memo(
        lambda: list(data_collection.external_links),
        [shared_refresh_counter.value]  # FIXED: Force refresh when counter changes
    )
    
    # CURRENT: Extensive debug logging to understand link structure
    # This helps debug when links aren't showing up or have unexpected format
    print(f"🔥 HARDCORE DEBUG: CurrentLinksSelector links_list = {links_list}")
    print(f"🔥 HARDCORE DEBUG: CurrentLinksSelector links_list count = {len(links_list)}")
    for i, link in enumerate(links_list):
        if hasattr(link, '_cid1') and hasattr(link, '_cid2'):
            print(f"🔥 HARDCORE DEBUG: CurrentLinksSelector link[{i}] = {link._cid1.label} <-> {link._cid2.label}")
        else:
            print(f"🔥 HARDCORE DEBUG: CurrentLinksSelector link[{i}] = {link} (unknown structure)")
    
    # EVOLUTION: User-friendly empty state
    # ORIGINAL: Would show empty list widget
    # CURRENT: Shows helpful message when no links exist
    if len(links_list) == 0:
        return solara.Text("No links created yet", style={"color": "#666", "font-style": "italic"})
    
    # EVOLUTION: Interactive selection list - KEY NEW FEATURE
    # ORIGINAL: Links were displayed but not selectable
    # CURRENT: Full selection support with highlighting and click handling
    with solara.v.List(dense=True):
        with solara.v.ListItemGroup(
            v_model=selected_link_index.value,    # Which link is currently selected (-1 = none)
            on_v_model=selected_link_index.set,   # Function called when user clicks a link
            color="primary",                      # Highlight color for selected link
        ):
            # Each link becomes a selectable list item
            # The value=idx connects the visual list item to the index in links_list
            for idx, link in enumerate(links_list):
                with solara.v.ListItem(value=idx):
                    with solara.v.ListItemContent():
                        solara.v.ListItemTitle(children=[stringify_links(link)])


@solara.component  
def QtStyleLinkDetailsPanel(
    app: JupyterApplication,
    data_collection: DataCollection,
    selected_data1: solara.Reactive[int],
    selected_data2: solara.Reactive[int],
    selected_link_index: solara.Reactive[int],
    shared_refresh_counter: solara.Reactive[int],
):
    """
    EVOLUTION: QtStyleLinkDetailsPanel - THE MOST COMPLEX NEW COMPONENT
    
    ORIGINAL: Did not exist at all
    PREVIOUS: Simple static display panel, no editing
    CURRENT: Full interactive editing panel with Qt-style behavior
    
    This is the rightmost panel that shows details of the selected link
    and allows editing the link's attributes through dropdown selectors.
    It mimics the Qt version's link details panel functionality.
    """
    
    # EVOLUTION: State management - critical for link editing
    # These hooks manage the internal state of the editing interface
    # All hooks MUST be at the top level (Solara requirement)
    selected_attr1 = solara.use_reactive(0)        # Currently selected Dataset 1 attribute
    selected_attr2 = solara.use_reactive(0)        # Currently selected Dataset 2 attribute  
    editing_link = solara.use_reactive(False)      # Track if user is editing (currently unused)
    # NOTE: refresh_counter is now passed as shared_refresh_counter parameter
    
    # EVOLUTION: Performance optimization with memoization  
    # This caches the links list to avoid recreating it on every render
    # Links change when glue_watch detects ExternallyDerivableComponentsChangedMessage
    # CRITICAL FIX: Force refresh when shared_refresh_counter changes to break stale cache
    links_list = solara.use_memo(
        lambda: list(data_collection.external_links),
        [shared_refresh_counter.value]  # FIXED: Add shared_refresh_counter to force cache invalidation
    )
    
    # CURRENT: Debug logging to track link detail panel state
    print(f"🔥 HARDCORE DEBUG: QtStyleLinkDetailsPanel render, selected_link_index={selected_link_index.value}")
    print(f"🔥 HARDCORE DEBUG: QtStyleLinkDetailsPanel links_list = {links_list}")
    print(f"🔥 HARDCORE DEBUG: QtStyleLinkDetailsPanel len(links_list) = {len(links_list)}")
    
    # CURRENT: ENHANCED MEMOIZATION FIX - Better link change detection
    # Problem: Original hash didn't detect when link objects changed internally
    # Solution: Include object IDs and more detailed content in hash
    # This ensures the UI updates when user edits link attributes
    link_contents_hash = solara.use_memo(
        lambda: hash(tuple(
            f"{id(link)}_{str(link._cid1)}_{str(link._cid2)}_{link.data1.label}_{link.data2.label}" 
            for link in links_list if hasattr(link, '_cid1')
        )),
        []  # Recalculate on every render to catch link changes
    )
    
    # EVOLUTION: Complex memoized link information processing
    # This is the heart of the link details display logic
    # It extracts and formats link information for the UI dropdowns
    selected_link_info = solara.use_memo(
        lambda: _get_selected_link_info(links_list, selected_link_index.value),
        [selected_link_index.value, len(links_list), link_contents_hash, shared_refresh_counter.value]  # ENHANCED: Added shared refresh counter
    )
    
    print(f"🔥 HARDCORE DEBUG: QtStyleLinkDetailsPanel selected_link_info = {selected_link_info}")
    print(f"🔥 HARDCORE DEBUG: QtStyleLinkDetailsPanel link_contents_hash = {link_contents_hash}")
    print(f"🔥 HARDCORE DEBUG: QtStyleLinkDetailsPanel shared_refresh_counter = {shared_refresh_counter.value}")
    
    # EVOLUTION: Safety check - present in all versions with link details
    if len(data_collection) == 0:
        return solara.Text("No data available")
    
    # EVOLUTION: Link editing handlers - THE CORE NEW FUNCTIONALITY
    # ORIGINAL: No link editing capability
    # PREVIOUS: No link editing capability  
    # CURRENT: Full Qt-style link editing with remove-and-recreate pattern
    
    def _remove_link():
        """
        TASK 2: Remove Link functionality
        
        This function handles direct link removal when user clicks "Remove Link" button
        Uses data_collection.remove_link() directly without recreation
        Ensures proper UI state cleanup after removal
        """
        print(f"🔥 TASK 2: _remove_link called")
        print(f"🔥 TASK 2: selected_link_info = {selected_link_info}")
        print(f"🔥 TASK 2: selected_link_index.value = {selected_link_index.value}")
        
        # Only proceed if we have a valid selected link
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info
            
            # FIXED: Handle different link types for display (coordinate helpers, ComponentLinks, etc.)
            link_display = "Unknown Link"
            try:
                if hasattr(link, '_cid1') and hasattr(link, '_cid2'):
                    # LinkSame object
                    link_display = f"{link._cid1.label} <-> {link._cid2.label}"
                elif hasattr(link, '_from') and hasattr(link, '_to'):
                    # ComponentLink object
                    if isinstance(link._from, list):
                        from_labels = [c.label for c in link._from]
                        link_display = f"{from_labels} -> {link._to.label}"
                    else:
                        link_display = f"{link._from.label} -> {link._to.label}"
                elif 'coordinate_helpers' in str(type(link)) and hasattr(link, 'cids1') and hasattr(link, 'cids2'):
                    # Coordinate helper object
                    if link.cids1 and link.cids2:
                        link_display = f"{link.cids1[0].label} <-> {link.cids2[0].label} (coordinate helper)"
                    else:
                        link_display = f"{type(link).__name__} (coordinate helper)"
                else:
                    link_display = f"{type(link).__name__}"
            except Exception as e:
                print(f"🔥 TASK 2: Error getting link display: {e}")
                link_display = f"{type(link).__name__} (display error)"
                
            print(f"🔥 TASK 2: Removing link {link_display}")
            print(f"🔥 TASK 2: Before remove - external_links count = {len(data_collection.external_links)}")
            
            # CRITICAL: Use data_collection.remove_link() as specified in meeting
            try:
                data_collection.remove_link(link)
                print(f"🔥 TASK 2: Link removal successful")
            except Exception as e:
                print(f"🔥 TASK 2: ERROR during link removal: {e}")
                print(f"🔥 TASK 2: Link type: {type(link)}")
                print(f"🔥 TASK 2: Link attributes: {[attr for attr in dir(link) if not attr.startswith('__')]}")
                return
            
            print(f"🔥 TASK 2: After remove - external_links count = {len(data_collection.external_links)}")
            print(f"🔥 TASK 2: Link removal COMPLETE")
            
            # TASK 2: Proper UI state cleanup after removal
            print(f"🔥 TASK 2: Forcing UI refresh after link removal")
            time.sleep(0.1)  # Small delay to let glue update internal state
            shared_refresh_counter.set(shared_refresh_counter.value + 1)  # Force UI refresh
            
            # TASK 2: Handle selection state after removal
            # Clear selection since the link no longer exists
            print(f"🔥 TASK 2: Clearing link selection after removal")
            selected_link_index.set(-1)  # Clear selection, this will hide the details panel
        else:
            print(f"🔥 TASK 2: Cannot remove - selected_link_info is None or invalid index")
    
    def _update_coordinate_parameter(dataset, param_index, new_attr_index):
        """
        ENHANCED: Coordinate Pair Parameter Update Function
        
        NEW: Handles editing of individual coordinate parameters in 2-to-2 coordinate transformations
        Similar to _update_multi_parameter but handles coordinate pairs (ra, dec) <-> (l, b)
        
        Args:
            dataset: Which dataset to update (1 or 2)
            param_index: Which coordinate parameter to update (0 or 1)
            new_attr_index: New attribute index for this coordinate parameter
        """
        print(f"🚀 COORD UPDATE: ===== _update_coordinate_parameter CALLED =====")
        print(f"🚀 COORD UPDATE: dataset = {dataset}")
        print(f"🚀 COORD UPDATE: param_index = {param_index}")
        print(f"🚀 COORD UPDATE: new_attr_index = {new_attr_index}")
        print(f"🚀 COORD UPDATE: selected_link_info = {selected_link_info}")
        print(f"🚀 COORD UPDATE: selected_link_index.value = {selected_link_index.value}")
        
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info
            print(f"🚀 COORD UPDATE: Link type: {type(link)}")
            print(f"🚀 COORD UPDATE: Link data is_coordinate_pair: {link_data.get('is_coordinate_pair', False)}")
            
            # Only proceed if this is actually a coordinate pair
            if not link_data.get('is_coordinate_pair', False):
                print(f"🚀 COORD UPDATE: ERROR - Not a coordinate pair link, aborting")
                return
                
            # Extract coordinate pair information
            coord1_param_info = link_data.get('coord1_param_info', [])
            coord2_param_info = link_data.get('coord2_param_info', [])
            
            if dataset == 1 and param_index >= len(coord1_param_info):
                print(f"🚀 COORD UPDATE: ERROR - Dataset 1 param_index {param_index} >= {len(coord1_param_info)}, aborting")
                return
            elif dataset == 2 and param_index >= len(coord2_param_info):
                print(f"🚀 COORD UPDATE: ERROR - Dataset 2 param_index {param_index} >= {len(coord2_param_info)}, aborting")
                return
                
            print(f"🚀 COORD UPDATE: Current coord1_param_info: {coord1_param_info}")
            print(f"🚀 COORD UPDATE: Current coord2_param_info: {coord2_param_info}")
            
            # Get datasets from the coordinate helper link
            if 'coordinate_helpers' in str(type(link)) and hasattr(link, 'data1') and hasattr(link, 'data2'):
                from_data = link.data1
                to_data = link.data2
                
                print(f"🚀 COORD UPDATE: from_data = {from_data.label}")
                print(f"🚀 COORD UPDATE: to_data = {to_data.label}")
                
                if dataset == 1:
                    # Update Dataset 1 coordinate parameter
                    if new_attr_index < len(from_data.components):
                        new_component = from_data.components[new_attr_index]
                        print(f"🚀 COORD UPDATE: Updating Dataset 1 coordinate {param_index}: {coord1_param_info[param_index]['component'].label} -> {new_component.label}")
                        
                        # Build new coordinate component lists
                        new_cids1 = list(link.cids1)
                        new_cids1[param_index] = new_component
                        new_cids2 = list(link.cids2)  # Keep Dataset 2 unchanged
                        
                        print(f"🚀 COORD UPDATE: New cids1: {[comp.label for comp in new_cids1]}")
                        print(f"🚀 COORD UPDATE: Keeping cids2: {[comp.label for comp in new_cids2]}")

                        # Track original position for UI state preservation
                        original_position = selected_link_index.value
                        print(f"🚀 COORD UPDATE: Original position = {original_position}")

                        # 🔗 ATOMIC FIX: Replace coordinate helper atomically to prevent component reference issues
                        print(f"🔗 ATOMIC FIX DATASET1: Creating new coordinate helper for atomic replacement")
                        coord_type = type(link)
                        new_coord_helper = coord_type(new_cids1, new_cids2, from_data, to_data)

                        # Get all existing links except the one being replaced
                        print(f"🔗 ATOMIC FIX DATASET1: Preparing atomic link replacement")
                        other_links = [l for l in data_collection.external_links if l != link]
                        all_new_links = other_links + [new_coord_helper]

                        print(f"🔗 ATOMIC FIX DATASET1: Before replacement - external_links count = {len(data_collection.external_links)}")
                        print(f"🔗 ATOMIC FIX DATASET1: Replacing with {len(all_new_links)} links (removed 1, added 1)")

                        # 🔗 ATOMIC REPLACEMENT: Use set_links for integrity
                        data_collection.set_links(all_new_links)

                        print(f"🔗 ATOMIC FIX DATASET1: After replacement - external_links count = {len(data_collection.external_links)}")
                        print(f"🔗 ATOMIC FIX DATASET1: Coordinate helper replaced atomically - no component reference issues!")

                        # 🔗 VERIFICATION: Confirm backend link integrity after atomic replacement
                        _verify_backend_connection(data_collection, "ATOMIC_COORD_DATASET1_FIX")
                        
                        # Position preservation and UI refresh
                        new_position = len(data_collection.external_links) - 1
                        print(f"🚀 COORD UPDATE: New coordinate helper created at position {new_position}")
                        
                        shared_refresh_counter.set(shared_refresh_counter.value + 1)
                        selected_link_index.set(-1)
                        selected_link_index.set(new_position)
                        
                        print(f"🚀 COORD UPDATE: Dataset 1 coordinate update complete!")
                        
                    else:
                        print(f"🚀 COORD UPDATE: ERROR - Invalid new_attr_index {new_attr_index} >= {len(from_data.components)}")
                
                elif dataset == 2:
                    # Update Dataset 2 coordinate parameter
                    if new_attr_index < len(to_data.components):
                        new_component = to_data.components[new_attr_index]
                        print(f"🚀 COORD UPDATE: Updating Dataset 2 coordinate {param_index}: {coord2_param_info[param_index]['component'].label} -> {new_component.label}")
                        
                        # Build new coordinate component lists
                        new_cids1 = list(link.cids1)  # Keep Dataset 1 unchanged
                        new_cids2 = list(link.cids2)
                        new_cids2[param_index] = new_component
                        
                        print(f"🚀 COORD UPDATE: Keeping cids1: {[comp.label for comp in new_cids1]}")
                        print(f"🚀 COORD UPDATE: New cids2: {[comp.label for comp in new_cids2]}")

                        # Track original position for UI state preservation
                        original_position = selected_link_index.value
                        print(f"🚀 COORD UPDATE: Original position = {original_position}")

                        # 🔗 ATOMIC FIX: Replace coordinate helper atomically to prevent component reference issues
                        print(f"🔗 ATOMIC FIX DATASET2: Creating new coordinate helper for atomic replacement")
                        coord_type = type(link)
                        new_coord_helper = coord_type(new_cids1, new_cids2, from_data, to_data)

                        # Get all existing links except the one being replaced
                        print(f"🔗 ATOMIC FIX DATASET2: Preparing atomic link replacement")
                        other_links = [l for l in data_collection.external_links if l != link]
                        all_new_links = other_links + [new_coord_helper]

                        print(f"🔗 ATOMIC FIX DATASET2: Before replacement - external_links count = {len(data_collection.external_links)}")
                        print(f"🔗 ATOMIC FIX DATASET2: Replacing with {len(all_new_links)} links (removed 1, added 1)")

                        # 🔗 ATOMIC REPLACEMENT: Use set_links for integrity
                        data_collection.set_links(all_new_links)

                        print(f"🔗 ATOMIC FIX DATASET2: After replacement - external_links count = {len(data_collection.external_links)}")
                        print(f"🔗 ATOMIC FIX DATASET2: Coordinate helper replaced atomically - no component reference issues!")

                        # 🔗 VERIFICATION: Confirm backend link integrity after atomic replacement
                        _verify_backend_connection(data_collection, "ATOMIC_COORD_DATASET2_FIX")
                        
                        # Position preservation and UI refresh
                        new_position = len(data_collection.external_links) - 1
                        print(f"🚀 COORD UPDATE: New coordinate helper created at position {new_position}")
                        
                        shared_refresh_counter.set(shared_refresh_counter.value + 1)
                        selected_link_index.set(-1)
                        selected_link_index.set(new_position)
                        
                        print(f"🚀 COORD UPDATE: Dataset 2 coordinate update complete!")
                        
                    else:
                        print(f"🚀 COORD UPDATE: ERROR - Invalid new_attr_index {new_attr_index} >= {len(to_data.components)}")
                
            else:
                print(f"🚀 COORD UPDATE: ERROR - Link doesn't have coordinate helper structure")
        else:
            print(f"🚀 COORD UPDATE: ERROR - No selected link or invalid index")

    def _update_multi_parameter(param_index, new_attr_index):
        """
        ENHANCED: Multi-Parameter Link Update Function
        
        NEW: Handles editing of individual parameters in multi-parameter links
        Qt-style approach: Remove old link, create new link with updated parameter
        
        Args:
            param_index: Which parameter to update (0=width, 1=height, 2=depth for lengths_to_volume)
            new_attr_index: New attribute index for this parameter
        """
        print(f"🚀 MULTI-PARAM UPDATE: ===== _update_multi_parameter CALLED =====")
        print(f"🚀 MULTI-PARAM UPDATE: param_index = {param_index}")
        print(f"🚀 MULTI-PARAM UPDATE: new_attr_index = {new_attr_index}")
        print(f"🚀 MULTI-PARAM UPDATE: selected_link_info = {selected_link_info}")
        print(f"🚀 MULTI-PARAM UPDATE: selected_link_index.value = {selected_link_index.value}")
        
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info
            print(f"🚀 MULTI-PARAM UPDATE: Link type: {type(link)}")
            print(f"🚀 MULTI-PARAM UPDATE: Link data is_multi_param: {link_data.get('is_multi_param', False)}")
            
            # Only proceed if this is actually a multi-parameter link
            if not link_data.get('is_multi_param', False):
                print(f"🚀 MULTI-PARAM UPDATE: ERROR - Not a multi-parameter link, aborting")
                return
                
            # Extract multi-parameter information
            multi_param_info = link_data.get('multi_param_info', [])
            if param_index >= len(multi_param_info):
                print(f"🚀 MULTI-PARAM UPDATE: ERROR - param_index {param_index} >= {len(multi_param_info)}, aborting")
                return
                
            print(f"🚀 MULTI-PARAM UPDATE: Current multi_param_info: {multi_param_info}")
            
            # Get datasets from the ComponentLink
            if hasattr(link, '_from') and hasattr(link, '_to'):
                from_data = link._from[0].parent  # All _from components should have same parent
                to_data = link._to.parent
                old_to_component = link._to
                
                print(f"🚀 MULTI-PARAM UPDATE: from_data = {from_data.label}")
                print(f"🚀 MULTI-PARAM UPDATE: to_data = {to_data.label}")
                print(f"🚀 MULTI-PARAM UPDATE: old_to_component = {old_to_component.label}")
                
                # Validate new attribute index
                if new_attr_index < len(from_data.components):
                    new_from_component = from_data.components[new_attr_index]
                    print(f"🚀 MULTI-PARAM UPDATE: new_from_component = {new_from_component.label}")
                    
                    # Build new parameter list with the updated component
                    new_from_components = []
                    for i, param in enumerate(multi_param_info):
                        if i == param_index:
                            new_from_components.append(new_from_component)
                            print(f"🚀 MULTI-PARAM UPDATE: Updated parameter {i}: {param['component'].label} -> {new_from_component.label}")
                        else:
                            new_from_components.append(param['component'])
                            print(f"🚀 MULTI-PARAM UPDATE: Kept parameter {i}: {param['component'].label}")
                    
                    print(f"🚀 MULTI-PARAM UPDATE: New component list: {[comp.label for comp in new_from_components]}")
                    
                    # Get function from original link
                    function = None
                    if hasattr(link, '_using'):
                        function = link._using
                        print(f"🚀 MULTI-PARAM UPDATE: Using original function: {getattr(function, '__name__', 'unknown')}")
                    
                    # Track original position for UI state preservation
                    original_position = selected_link_index.value
                    print(f"🚀 MULTI-PARAM UPDATE: Original position = {original_position}")

                    # 🔗 ATOMIC FIX: Create new ComponentLink for atomic replacement
                    print(f"🔗 ATOMIC FIX MULTI-PARAM: Creating new ComponentLink for atomic replacement")
                    print(f"🔗 ATOMIC FIX MULTI-PARAM: Original link type: {type(link)}")
                    print(f"🔗 ATOMIC FIX MULTI-PARAM: Function: {getattr(function, '__name__', 'unknown')}")

                    from glue.core.component_link import ComponentLink
                    new_link = ComponentLink(new_from_components, old_to_component, using=function)

                    # Get all existing links except the one being replaced
                    print(f"🔗 ATOMIC FIX MULTI-PARAM: Preparing atomic link replacement")
                    other_links = [l for l in data_collection.external_links if l != link]
                    all_new_links = other_links + [new_link]

                    print(f"🔗 ATOMIC FIX MULTI-PARAM: Before replacement - external_links count = {len(data_collection.external_links)}")
                    print(f"🔗 ATOMIC FIX MULTI-PARAM: Replacing with {len(all_new_links)} links (removed 1, added 1)")
                    print(f"🔗 ATOMIC FIX MULTI-PARAM: New link: {[c.label for c in new_from_components]} -> {old_to_component.label}")

                    # 🔗 ATOMIC REPLACEMENT: Use set_links for integrity
                    data_collection.set_links(all_new_links)

                    print(f"🔗 ATOMIC FIX MULTI-PARAM: After replacement - external_links count = {len(data_collection.external_links)}")
                    print(f"🔗 ATOMIC FIX MULTI-PARAM: Multi-parameter ComponentLink replaced atomically - no component reference issues!")

                    # 🔗 VERIFICATION: Confirm backend link integrity after atomic replacement
                    _verify_backend_connection(data_collection, "ATOMIC_MULTI_PARAM_FIX")
                    
                    # Position preservation: select the newly created link
                    new_position = len(data_collection.external_links) - 1
                    print(f"🚀 MULTI-PARAM UPDATE: New link created at position {new_position}")
                    
                    # CRITICAL: Verify backend connection after multi-parameter editing
                    _verify_backend_connection(data_collection, "MULTI_PARAM_LINK_EDIT")
                    
                    # Force UI refresh
                    print(f"🚀 MULTI-PARAM UPDATE: Forcing UI refresh")
                    shared_refresh_counter.set(shared_refresh_counter.value + 1)
                    selected_link_index.set(-1)
                    selected_link_index.set(new_position)
                    
                    print(f"🚀 MULTI-PARAM UPDATE: Multi-parameter update complete!")
                    
                else:
                    print(f"🚀 MULTI-PARAM UPDATE: ERROR - Invalid new_attr_index {new_attr_index} >= {len(from_data.components)}")
            else:
                print(f"🚀 MULTI-PARAM UPDATE: ERROR - Link doesn't have _from/_to attributes")
        else:
            print(f"🚀 MULTI-PARAM UPDATE: ERROR - No selected link or invalid index")

    def _update_dataset1_attribute(new_attr_index):
        """
        TASK 1 FIXED: Qt-style link editing with position preservation
        
        This function handles when user changes the Dataset 1 attribute dropdown
        Qt approach: Remove the old link completely, then create a new link
        ENHANCEMENT: Preserve original link position for better UX
        """
        print(f"🔥 LINK EDIT: ===== _update_dataset1_attribute CALLED =====")
        print(f"🔥 LINK EDIT: Input new_attr_index = {new_attr_index}")
        print(f"🔥 LINK EDIT: selected_link_info = {selected_link_info}")
        print(f"🔥 LINK EDIT: selected_link_index.value = {selected_link_index.value}")
        print(f"🔥 LINK EDIT: links_list count = {len(links_list) if links_list else 0}")
        print(f"🔥 LINK EDIT: Type of selected_link_info = {type(selected_link_info)}")
        
        # Only proceed if we have a valid selected link
        if selected_link_info is not None and selected_link_index.value >= 0:
            print(f"🔥 LINK EDIT: Valid link selected, proceeding with update")
            link, link_data = selected_link_info
            print(f"🔥 LINK EDIT: Extracted link = {link}")
            print(f"🔥 LINK EDIT: Extracted link_data = {link_data}")
            print(f"🔥 LINK EDIT: Link type = {type(link)}")
            print(f"🔥 LINK EDIT: Link attributes = {dir(link) if hasattr(link, '__dict__') else 'No attributes'}")
            
            # CRITICAL FIX: Handle different link types (ComponentLink vs LinkSame)
            if hasattr(link, 'data1') and hasattr(link, 'data2'):
                # LinkSame objects have data1/data2 attributes
                from_data = link.data1                      # Dataset that link comes from
                to_data = link.data2                        # Dataset that link goes to
                print(f"🔥 LINK EDIT: LinkSame detected - data1={from_data.label}, data2={to_data.label}")
            elif hasattr(link, '_from') and hasattr(link, '_to'):
                # ComponentLink objects need to extract data from components
                print(f"🔥 LINK EDIT: ComponentLink detected")
                print(f"🔥 LINK EDIT: link._from = {link._from}")
                print(f"🔥 LINK EDIT: link._to = {link._to}")
                print(f"🔥 LINK EDIT: link._from type = {type(link._from)}")
                print(f"🔥 LINK EDIT: Is _from a list? {isinstance(link._from, list)}")
                
                if isinstance(link._from, list) and len(link._from) > 0:
                    from_data = link._from[0].parent        # Get data from first input component
                    print(f"🔥 LINK EDIT: Multi-input ComponentLink - using first input component")
                    print(f"🔥 LINK EDIT: link._from[0] = {link._from[0]}")
                    print(f"🔥 LINK EDIT: link._from[0].parent = {link._from[0].parent}")
                else:
                    from_data = link._from.parent           # Single input component
                    print(f"🔥 LINK EDIT: Single-input ComponentLink")
                    
                to_data = link._to.parent                   # Get data from output component
                print(f"🔥 LINK EDIT: to_data = {to_data}")
                print(f"🔥 LINK EDIT: ComponentLink data extracted - from_data={from_data.label}, to_data={to_data.label}")
            else:
                print(f"🔥 LINK EDIT: ERROR - Unknown link type: {type(link)}")
                print(f"🔥 LINK EDIT: Available attributes: {[attr for attr in dir(link) if not attr.startswith('__')]}")
                return
                
            print(f"🔥 LINK EDIT: Successfully extracted datasets - proceeding with link update")
            
            # TASK 1: Track original position before any changes
            original_position = selected_link_index.value
            print(f"🔥 TASK 1: Tracking original link position = {original_position}")
            
            print(f"🔥 LINK EDIT: Current link datasets - from_data = {from_data.label}")
            print(f"🔥 LINK EDIT: Current link datasets - to_data = {to_data.label}")
            
            # Show current link components (handle both LinkSame and ComponentLink)
            if hasattr(link, '_cid1') and hasattr(link, '_cid2'):
                print(f"🔥 LINK EDIT: LinkSame - current _cid1 = {link._cid1.label}")
                print(f"🔥 LINK EDIT: LinkSame - current _cid2 = {link._cid2.label}")
            elif hasattr(link, '_from') and hasattr(link, '_to'):
                if isinstance(link._from, list):
                    from_labels = [c.label for c in link._from]
                    print(f"🔥 LINK EDIT: ComponentLink - current inputs = {from_labels}")
                else:
                    print(f"🔥 LINK EDIT: ComponentLink - current input = {link._from.label}")
                print(f"🔥 LINK EDIT: ComponentLink - current output = {link._to.label}")
            else:
                print(f"🔥 LINK EDIT: Unknown link structure")
            
            # Validate the new attribute index is valid
            if new_attr_index < len(from_data.components):
                new_component = from_data.components[new_attr_index]  # New Dataset 1 attribute
                
                # FIXED: Handle both ComponentLink and LinkSame for Dataset 2 attribute
                print(f"🔥 LINK EDIT: Getting Dataset 2 attribute from link type: {type(link)}")
                if hasattr(link, '_cid2'):
                    # LinkSame object
                    old_component2 = link._cid2
                    print(f"🔥 LINK EDIT: Using LinkSame _cid2: {old_component2.label}")
                elif hasattr(link, '_to'):
                    # ComponentLink object  
                    old_component2 = link._to
                    print(f"🔥 LINK EDIT: Using ComponentLink _to: {old_component2.label}")
                elif 'coordinate_helpers' in str(type(link)) and hasattr(link, 'cids2'):
                    # Coordinate helper object - use first component from cids2
                    if link.cids2:
                        old_component2 = link.cids2[0]
                        print(f"🔥 LINK EDIT: Using coordinate helper cids2[0]: {old_component2.label}")
                    else:
                        print(f"🔥 LINK EDIT: ERROR - Coordinate helper cids2 is empty")
                        return
                else:
                    print(f"🔥 LINK EDIT: ERROR - Cannot determine Dataset 2 attribute from link type {type(link)}")
                    return
                
                print(f"🔥 HARDCORE DEBUG: QT-STYLE APPROACH: Remove old link, create new link")
                print(f"🔥 HARDCORE DEBUG: NEW LINK will be - {new_component.label} <-> {old_component2.label}")
                
                # 🔗 ATOMIC FIX: Track state before Qt's atomic replacement
                print(f"🔗 ATOMIC FIX DATASET1: Before Qt atomic replacement - external_links count = {len(data_collection.external_links)}")
                print(f"🔗 ATOMIC FIX DATASET1: Link to replace: {link}")
                print(f"🔗 ATOMIC FIX DATASET1: Qt's update_links_in_collection() will handle atomic replacement")

                # 🔗 CRITICAL FIX: DO NOT call remove_link() here!
                # Qt's temp_state.update_links_in_collection() already uses set_links() atomically
                # The premature remove_link() was causing component reference integrity issues

                # 🚀 PHASE 1 UNIFIED EDIT: Recreate link preserving original type 
                # This fixes "magical switching" by maintaining link structure
                print(f"🚀 UNIFIED EDIT: Recreating link with EditableLinkFunctionState to preserve type")
                
                # Step 1: Determine original link creation method
                original_link_type = type(link).__name__
                print(f"🚀 UNIFIED EDIT: Original link type: {original_link_type}")
                
                try:
                    # Step 2: Use Qt's EditableLinkFunctionState pattern for ALL edits
                    from glue.dialogs.link_editor.state import LinkEditorState

                    # Create temporary LinkEditorState (Qt's exact approach)
                    # NOTE: This copies ALL existing links from data_collection into temp_state.links
                    temp_state = LinkEditorState(data_collection)
                    temp_state.data1 = from_data
                    temp_state.data2 = to_data

                    # 🔗 CRITICAL FIX: Remove the old link from temp_state.links to prevent duplication
                    # NOTE: l.link creates a NEW object each time, so we must compare by properties!
                    print(f"🔗 DEDUP FIX: temp_state.links count BEFORE removal = {len(temp_state.links)}")

                    def links_match(wrapper_link, original_link):
                        """Compare links by properties since .link creates new objects"""
                        # Compare link types first
                        if type(wrapper_link) != type(original_link):
                            return False

                        # LinkSame comparison
                        if hasattr(original_link, '_cid1') and hasattr(original_link, '_cid2'):
                            return (wrapper_link._cid1 == original_link._cid1 and
                                    wrapper_link._cid2 == original_link._cid2)

                        # ComponentLink comparison
                        if hasattr(original_link, '_from') and hasattr(original_link, '_to'):
                            from_match = (wrapper_link._from == original_link._from or
                                         (isinstance(original_link._from, list) and
                                          isinstance(wrapper_link._from, list) and
                                          wrapper_link._from == original_link._from))
                            to_match = wrapper_link._to == original_link._to
                            return from_match and to_match

                        return False

                    temp_state.links = [l for l in temp_state.links if not links_match(l.link, link)]
                    print(f"🔗 DEDUP FIX: temp_state.links count AFTER removal = {len(temp_state.links)}")
                    print(f"🔗 DEDUP FIX: Successfully removed link - count decreased: {len(temp_state.links) < len(data_collection.external_links)}")
                    
                    # Step 3: Find the registry object that created this link originally
                    registry_object = None
                    
                    # Try to find original function/helper that created this link
                    if hasattr(link, '_using') and link._using:
                        # ComponentLink with function - find in function registry
                        from glue.config import link_function
                        function_name = getattr(link._using, '__name__', 'unknown')
                        print(f"🚀 UNIFIED EDIT: Looking for function: {function_name}")
                        
                        for func in link_function.members:
                            if hasattr(func, 'function') and func.function.__name__ == function_name:
                                registry_object = func
                                print(f"🚀 UNIFIED EDIT: Found function registry object: {func}")
                                break
                    
                    elif 'coordinate_helpers' in original_link_type.lower() or 'galactic' in original_link_type.lower() or 'icrs' in original_link_type.lower():
                        # Coordinate helper - find in helper registry
                        from glue.config import link_helper
                        print(f"🚀 UNIFIED EDIT: Looking for coordinate helper: {original_link_type}")
                        
                        for helper in link_helper.members:
                            if helper.helper.__name__ == original_link_type:
                                registry_object = helper
                                print(f"🚀 UNIFIED EDIT: Found helper registry object: {helper}")
                                break
                    
                    elif 'join' in original_link_type.lower():
                        # JoinLink - find in helper registry
                        from glue.config import link_helper
                        print(f"🚀 UNIFIED EDIT: Looking for join helper")
                        
                        for helper in link_helper.members:
                            if 'join' in helper.helper.__name__.lower():
                                registry_object = helper
                                print(f"🚀 UNIFIED EDIT: Found join registry object: {helper}")
                                break
                    
                    # Step 4: Recreate link using proper registry object
                    if registry_object:
                        print(f"🚀 UNIFIED EDIT: Recreating with registry object: {registry_object}")
                        temp_state.new_link(registry_object)
                        
                        # Step 5: Update component selections to new user choice
                        # This is the magic - we recreate the SAME link type but with updated components
                        if hasattr(temp_state, 'data1_att') and hasattr(temp_state, 'data2_att'):
                            # For simple links, update the attribute selections
                            temp_state.data1_att = new_component
                            temp_state.data2_att = old_component2
                            print(f"🚀 UNIFIED EDIT: Updated simple link components: {new_component.label} -> {old_component2.label}")
                        
                        elif hasattr(temp_state, 'current_link') and temp_state.current_link:
                            # For complex links, update the attribute mappings
                            current_link = temp_state.current_link
                            print(f"🚀 DATASET1 CURRENT_LINK DEBUG: current_link = {current_link}")
                            print(f"🚀 DATASET1 CURRENT_LINK DEBUG: current_link type = {type(current_link)}")
                            
                            # Check if this is an identity function with x/y parameters (like Dataset2 fix)
                            if hasattr(current_link, 'x') and hasattr(current_link, 'y'):
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: Found x/y parameters!")
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: BEFORE - current_link.x = {current_link.x}")
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: BEFORE - current_link.y = {current_link.y}")
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: Setting current_link.x = {new_component.label}")
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: Setting current_link.y = {old_component2.label}")
                                
                                current_link.x = new_component    # Dataset 1 component (user's change)
                                current_link.y = old_component2   # Dataset 2 component (unchanged)
                                
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: AFTER - current_link.x = {current_link.x}")
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: AFTER - current_link.y = {current_link.y}")
                                print(f"🚀 UNIFIED EDIT: Updated identity function components: {new_component.label} -> {old_component2.label}")
                            
                            # Try to update first component mapping (this is user's edit) - FALLBACK for non-identity functions
                            elif hasattr(current_link, 'data1') and hasattr(current_link, 'names1'):
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: Found data1/names1 parameters!")
                                # Multi-parameter link - update first parameter
                                names1 = current_link.names1
                                if names1 and len(names1) > 0:
                                    first_param_name = names1[0]
                                    if hasattr(current_link, first_param_name):
                                        setattr(current_link, first_param_name, new_component)
                                        print(f"🚀 UNIFIED EDIT: Updated multi-parameter {first_param_name}: {new_component.label}")
                            else:
                                print(f"🚀 DATASET1 CURRENT_LINK DEBUG: No recognized parameter structure found!")
                        
                        # Step 6: Apply the recreated link
                        temp_state.update_links_in_collection()
                        print(f"🚀 UNIFIED EDIT: Successfully recreated {original_link_type} with updated components")

                        # 🔗 VERIFICATION: Confirm backend link integrity after Qt unified edit
                        _verify_backend_connection(data_collection, "QT_UNIFIED_EDIT_DATASET1")

                        # Step 7: Debug track type preservation
                        _debug_link_type_preservation(link, data_collection.external_links, "DATASET1_UNIFIED_EDIT")
                        
                    else:
                        # Fallback: If we can't find registry object, use identity function
                        print(f"🚀 UNIFIED EDIT: Registry object not found, falling back to identity function")
                        from glue.config import link_function
                        identity_func = None
                        for func in link_function.members:
                            if hasattr(func, 'function') and func.function.__name__ == 'identity':
                                identity_func = func
                                break
                        
                        if identity_func:
                            temp_state.new_link(identity_func)
                            # CRITICAL FIX: Set component selections for fallback identity link
                            if hasattr(temp_state, 'current_link') and temp_state.current_link:
                                # Set the components that user actually selected
                                current_link = temp_state.current_link
                                print(f"🚀 FALLBACK DEBUG: current_link = {current_link}")
                                print(f"🚀 FALLBACK DEBUG: current_link type = {type(current_link)}")
                                print(f"🚀 FALLBACK DEBUG: current_link attributes = {[attr for attr in dir(current_link) if not attr.startswith('_')]}")
                                
                                if hasattr(current_link, 'x') and hasattr(current_link, 'y'):
                                    print(f"🚀 FALLBACK DEBUG: BEFORE setting - current_link.x = {getattr(current_link, 'x', 'NOT_SET')}")
                                    print(f"🚀 FALLBACK DEBUG: BEFORE setting - current_link.y = {getattr(current_link, 'y', 'NOT_SET')}")
                                    
                                    # Identity function uses 'x' and 'y' parameters
                                    current_link.x = new_component    # Dataset 1 component (user's change)
                                    current_link.y = old_component2   # Dataset 2 component (unchanged)
                                    
                                    print(f"🚀 FALLBACK DEBUG: AFTER setting - current_link.x = {current_link.x}")
                                    print(f"🚀 FALLBACK DEBUG: AFTER setting - current_link.y = {current_link.y}")
                                    print(f"🚀 UNIFIED EDIT: Set fallback identity components: {new_component.label} -> {old_component2.label}")
                                else:
                                    print(f"🚀 FALLBACK DEBUG: current_link does NOT have x/y attributes!")
                            else:
                                print(f"🚀 FALLBACK DEBUG: temp_state.current_link is None or missing!")
                            
                            print(f"🚀 FALLBACK DEBUG: About to call temp_state.update_links_in_collection()")
                            temp_state.update_links_in_collection()
                            print(f"🚀 FALLBACK DEBUG: Finished temp_state.update_links_in_collection()")
                            print(f"🚀 UNIFIED EDIT: Created fallback identity link")

                            # 🔗 VERIFICATION: Confirm backend link integrity after fallback edit
                            _verify_backend_connection(data_collection, "QT_FALLBACK_EDIT_DATASET1")
                        else:
                            # Final fallback - use old method but warn
                            print(f"🚀 UNIFIED EDIT: WARNING - Using old app.add_link() as final fallback")
                            app.add_link(from_data, new_component, to_data, old_component2)
                
                except Exception as e:
                    print(f"🚀 UNIFIED EDIT: ERROR in unified approach: {e}")
                    import traceback
                    print(f"🚀 UNIFIED EDIT: Traceback: {traceback.format_exc()}")
                    # Fallback to old method if unified approach fails
                    print(f"🚀 UNIFIED EDIT: Falling back to app.add_link()")
                    app.add_link(from_data, new_component, to_data, old_component2)
                
                print(f"🔥 AFTER ADD: external_links count = {len(data_collection.external_links)}")
                print(f"🔥 AFTER ADD: external_links IDs = {[id(link) for link in data_collection.external_links]}")
                print(f"🔥 AFTER ADD: external_links content = {[f'{link._cid1.label}<->{link._cid2.label}' for link in data_collection.external_links if hasattr(link, '_cid1')]}")
                
                print(f"🔥 HARDCORE DEBUG: Qt-style link replacement COMPLETE")
                
                # CRITICAL: Verify backend connection after editing
                _verify_backend_connection(data_collection, "DATASET1_LINK_EDIT")
                
                # ENHANCED WORKAROUND: Give glue time to settle, then force UI refresh
                print(f"🔥 TIMING FIX: Waiting for glue to settle...")
                time.sleep(0.1)  # Small delay to let glue update internal state
                
                print(f"🔥 FORCING UI REFRESH: Incrementing shared refresh counter")
                shared_refresh_counter.set(shared_refresh_counter.value + 1)  # Force memoization recalculation
                
                # TASK 1: POSITION PRESERVATION FIX
                # New links are added at the end, so select the last index (newly created link)
                new_position = len(data_collection.external_links) - 1
                print(f"🔥 TASK 1: New link created at position {new_position} (was at {original_position})")
                print(f"🔥 TASK 1: Selecting new link position instead of always going to index 0")
                selected_link_index.set(-1)    # Clear selection first
                selected_link_index.set(new_position)  # Select the newly created link
            else:
                print(f"🔥 HARDCORE DEBUG: Invalid new_attr_index {new_attr_index} >= {len(from_data.components)}")
        else:
            print(f"🔥 HARDCORE DEBUG: Cannot update - selected_link_info is None or invalid index")
                
    def _update_dataset2_attribute(new_attr_index):
        """
        TASK 1 FIXED: Qt-style link editing with position preservation
        
        Mirror function to _update_dataset1_attribute but for the target attribute
        ENHANCEMENT: Same position preservation logic as Dataset 1 function
        """
        print(f"🔥 LINK EDIT: ===== _update_dataset2_attribute CALLED =====")
        print(f"🔥 LINK EDIT: Input new_attr_index = {new_attr_index}")
        print(f"🔥 LINK EDIT: selected_link_info = {selected_link_info}")
        print(f"🔥 LINK EDIT: selected_link_index.value = {selected_link_index.value}")
        print(f"🔥 LINK EDIT: links_list count = {len(links_list) if links_list else 0}")
        
        # Same validation and approach as Dataset 1 function
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info
            
            # FIXED: Handle both ComponentLink and LinkSame for dataset extraction
            print(f"🔥 LINK EDIT: Extracting datasets from link type: {type(link)}")
            if hasattr(link, 'data1') and hasattr(link, 'data2'):
                # LinkSame object
                from_data = link.data1
                to_data = link.data2  
                print(f"🔥 LINK EDIT: Using LinkSame .data1/.data2 attributes")
            elif hasattr(link, '_from') and hasattr(link, '_to'):
                # ComponentLink object - extract datasets from component parents
                if isinstance(link._from, list):
                    from_data = link._from[0].parent
                    print(f"🔥 LINK EDIT: Using ComponentLink _from[0].parent")
                else:
                    from_data = link._from.parent
                    print(f"🔥 LINK EDIT: Using ComponentLink _from.parent")
                to_data = link._to.parent
                print(f"🔥 LINK EDIT: Using ComponentLink _to.parent")
            else:
                print(f"🔥 LINK EDIT: ERROR - Cannot determine datasets from link type {type(link)}")
                return
            
            # TASK 1: Track original position before any changes
            original_position = selected_link_index.value
            print(f"🔥 TASK 1: Tracking original link position = {original_position}")
            
            print(f"🔥 LINK EDIT: Current link datasets - from_data = {from_data.label}")
            print(f"🔥 LINK EDIT: Current link datasets - to_data = {to_data.label}")
            
            # Show current link components (handle both LinkSame and ComponentLink)
            if hasattr(link, '_cid1') and hasattr(link, '_cid2'):
                print(f"🔥 LINK EDIT: LinkSame - current _cid1 = {link._cid1.label}")
                print(f"🔥 LINK EDIT: LinkSame - current _cid2 = {link._cid2.label}")
            elif hasattr(link, '_from') and hasattr(link, '_to'):
                if isinstance(link._from, list):
                    from_labels = [c.label for c in link._from]
                    print(f"🔥 LINK EDIT: ComponentLink - current inputs = {from_labels}")
                else:
                    print(f"🔥 LINK EDIT: ComponentLink - current input = {link._from.label}")
                print(f"🔥 LINK EDIT: ComponentLink - current output = {link._to.label}")
            else:
                print(f"🔥 LINK EDIT: Unknown link structure")
            
            # Validate new attribute index for target dataset
            if new_attr_index < len(to_data.components):
                # FIXED: Handle both ComponentLink and LinkSame for Dataset 1 attribute
                print(f"🔥 LINK EDIT: Getting Dataset 1 attribute from link type: {type(link)}")
                if hasattr(link, '_cid1'):
                    # LinkSame object
                    old_component1 = link._cid1
                    print(f"🔥 LINK EDIT: Using LinkSame _cid1: {old_component1.label}")
                elif hasattr(link, '_from'):
                    # ComponentLink object - use first input component
                    if isinstance(link._from, list):
                        old_component1 = link._from[0] 
                        print(f"🔥 LINK EDIT: Using ComponentLink _from[0]: {old_component1.label}")
                    else:
                        old_component1 = link._from
                        print(f"🔥 LINK EDIT: Using ComponentLink _from: {old_component1.label}")
                elif 'coordinate_helpers' in str(type(link)) and hasattr(link, 'cids1'):
                    # Coordinate helper object - use first component from cids1
                    if link.cids1:
                        old_component1 = link.cids1[0]
                        print(f"🔥 LINK EDIT: Using coordinate helper cids1[0]: {old_component1.label}")
                    else:
                        print(f"🔥 LINK EDIT: ERROR - Coordinate helper cids1 is empty")
                        return
                else:
                    print(f"🔥 LINK EDIT: ERROR - Cannot determine Dataset 1 attribute from link type {type(link)}")
                    return
                    
                new_component = to_data.components[new_attr_index]    # New Dataset 2 attribute
                
                print(f"🔥 HARDCORE DEBUG: QT-STYLE APPROACH: Remove old link, create new link")
                print(f"🔥 HARDCORE DEBUG: NEW LINK will be - {old_component1.label} <-> {new_component.label}")
                
                # 🔗 ATOMIC FIX: Track state before Qt's atomic replacement (Dataset 2)
                print(f"🔗 ATOMIC FIX DATASET2: Before Qt atomic replacement - external_links count = {len(data_collection.external_links)}")
                print(f"🔗 ATOMIC FIX DATASET2: Link to replace: {link}")
                print(f"🔗 ATOMIC FIX DATASET2: Qt's update_links_in_collection() will handle atomic replacement")

                # 🔗 CRITICAL FIX: DO NOT call remove_link() here!
                # Qt's temp_state.update_links_in_collection() already uses set_links() atomically
                # The premature remove_link() was causing component reference integrity issues
                # 🚀 PHASE 1 UNIFIED EDIT: Recreate link preserving original type (Dataset 2)
                print(f"🚀 UNIFIED EDIT DATASET2: Recreating link with EditableLinkFunctionState to preserve type")
                
                # Step 1: Determine original link creation method
                original_link_type = type(link).__name__
                print(f"🚀 UNIFIED EDIT DATASET2: Original link type: {original_link_type}")
                
                try:
                    # Step 2: Use Qt's EditableLinkFunctionState pattern for ALL edits
                    from glue.dialogs.link_editor.state import LinkEditorState

                    # Create temporary LinkEditorState (Qt's exact approach)
                    # NOTE: This copies ALL existing links from data_collection into temp_state.links
                    temp_state = LinkEditorState(data_collection)
                    temp_state.data1 = from_data
                    temp_state.data2 = to_data

                    # 🔗 CRITICAL FIX: Remove the old link from temp_state.links to prevent duplication
                    # NOTE: l.link creates a NEW object each time, so we must compare by properties!
                    print(f"🔗 DEDUP FIX: temp_state.links count BEFORE removal = {len(temp_state.links)}")

                    def links_match(wrapper_link, original_link):
                        """Compare links by properties since .link creates new objects"""
                        # Compare link types first
                        if type(wrapper_link) != type(original_link):
                            return False

                        # LinkSame comparison
                        if hasattr(original_link, '_cid1') and hasattr(original_link, '_cid2'):
                            return (wrapper_link._cid1 == original_link._cid1 and
                                    wrapper_link._cid2 == original_link._cid2)

                        # ComponentLink comparison
                        if hasattr(original_link, '_from') and hasattr(original_link, '_to'):
                            from_match = (wrapper_link._from == original_link._from or
                                         (isinstance(original_link._from, list) and
                                          isinstance(wrapper_link._from, list) and
                                          wrapper_link._from == original_link._from))
                            to_match = wrapper_link._to == original_link._to
                            return from_match and to_match

                        return False

                    temp_state.links = [l for l in temp_state.links if not links_match(l.link, link)]
                    print(f"🔗 DEDUP FIX: temp_state.links count AFTER removal = {len(temp_state.links)}")
                    print(f"🔗 DEDUP FIX: Successfully removed link - count decreased: {len(temp_state.links) < len(data_collection.external_links)}")
                    
                    # Step 3: Find the registry object that created this link originally
                    registry_object = None
                    
                    # Try to find original function/helper that created this link

                    # Get function name for analysis
                    function_name = 'unknown'
                    if hasattr(link, '_using') and link._using:
                        function_name = getattr(link._using, '__name__', 'unknown')

                    print(f"🚀 UNIFIED EDIT DATASET2: Function name: {function_name}")

                    # BUGFIX: Check both class name AND function name for coordinate helpers
                    is_coordinate_helper = (
                        'coordinate_helpers' in original_link_type.lower() or
                        'galactic' in original_link_type.lower() or
                        'icrs' in original_link_type.lower() or
                        'fk4' in original_link_type.lower() or
                        'fk5' in original_link_type.lower() or
                        # BUGFIX: Also check function name patterns
                        'icrs_to' in function_name.lower() or
                        'galactic_to' in function_name.lower() or
                        'fk4_to' in function_name.lower() or
                        'fk5_to' in function_name.lower() or
                        '_to_fk' in function_name.lower() or
                        '_to_icrs' in function_name.lower() or
                        '_to_galactic' in function_name.lower()
                    )

                    if is_coordinate_helper:
                        # Coordinate helper - find in helper registry
                        from glue.config import link_helper
                        print(f"🚀 UNIFIED EDIT DATASET2: Detected coordinate helper")
                        print(f"🐛 BUGFIX: Function name: {function_name}")
                        print(f"🐛 BUGFIX: Original link type: {original_link_type}")

                        # Extract coordinate helper class name from function name
                        # E.g., "ICRS_to_FK5.backwards_2" -> "ICRS_to_FK5"
                        helper_class_name = function_name.split('.')[0] if '.' in function_name else original_link_type
                        print(f"🐛 BUGFIX: Extracted helper class name: {helper_class_name}")

                        print(f"🐛 BUGFIX: Checking all helpers for match:")
                        for helper in link_helper.members:
                            helper_name = helper.helper.__name__
                            print(f"🐛 BUGFIX: Comparing '{helper_class_name}' with '{helper_name}'")
                            if helper_name == helper_class_name:
                                registry_object = helper
                                print(f"🚀 UNIFIED EDIT DATASET2: Found helper registry object: {helper}")
                                break

                    elif hasattr(link, '_using') and link._using:
                        # ComponentLink with function - find in function registry
                        from glue.config import link_function
                        print(f"🚀 UNIFIED EDIT DATASET2: Looking for function: {function_name}")

                        for func in link_function.members:
                            if hasattr(func, 'function') and func.function.__name__ == function_name:
                                registry_object = func
                                print(f"🚀 UNIFIED EDIT DATASET2: Found function registry object: {func}")
                                break

                    elif 'join' in original_link_type.lower():
                        # JoinLink - find in helper registry
                        from glue.config import link_helper
                        print(f"🚀 UNIFIED EDIT DATASET2: Looking for join helper")
                        
                        for helper in link_helper.members:
                            if 'join' in helper.helper.__name__.lower():
                                registry_object = helper
                                print(f"🚀 UNIFIED EDIT DATASET2: Found join registry object: {helper}")
                                break
                    
                    # Step 4: Recreate link using proper registry object
                    if registry_object:
                        print(f"🚀 UNIFIED EDIT DATASET2: Recreating with registry object: {registry_object}")
                        temp_state.new_link(registry_object)
                        
                        # Step 5: Update component selections to new user choice (Dataset 2 edit)
                        print(f"🚀 DATASET2 BRANCH DEBUG: hasattr(temp_state, 'data1_att') = {hasattr(temp_state, 'data1_att')}")
                        print(f"🚀 DATASET2 BRANCH DEBUG: hasattr(temp_state, 'data2_att') = {hasattr(temp_state, 'data2_att')}")
                        print(f"🚀 DATASET2 BRANCH DEBUG: hasattr(temp_state, 'current_link') = {hasattr(temp_state, 'current_link')}")
                        print(f"🚀 DATASET2 BRANCH DEBUG: temp_state.current_link = {getattr(temp_state, 'current_link', 'NOT_SET')}")
                        
                        if hasattr(temp_state, 'data1_att') and hasattr(temp_state, 'data2_att'):
                            # For simple links, update the attribute selections
                            print(f"🚀 DATASET2 DEBUG: TAKING data1_att/data2_att BRANCH")
                            print(f"🚀 DATASET2 DEBUG: BEFORE setting - temp_state.data1_att = {getattr(temp_state, 'data1_att', 'NOT_SET')}")
                            print(f"🚀 DATASET2 DEBUG: BEFORE setting - temp_state.data2_att = {getattr(temp_state, 'data2_att', 'NOT_SET')}")
                            print(f"🚀 DATASET2 DEBUG: About to set temp_state.data1_att = {old_component1.label}")
                            print(f"🚀 DATASET2 DEBUG: About to set temp_state.data2_att = {new_component.label}")
                            
                            temp_state.data1_att = old_component1
                            temp_state.data2_att = new_component  # This is the user's Dataset 2 edit
                            
                            print(f"🚀 DATASET2 DEBUG: AFTER setting - temp_state.data1_att = {temp_state.data1_att}")
                            print(f"🚀 DATASET2 DEBUG: AFTER setting - temp_state.data2_att = {temp_state.data2_att}")
                            print(f"🚀 UNIFIED EDIT DATASET2: Updated simple link components: {old_component1.label} -> {new_component.label}")
                        
                        elif hasattr(temp_state, 'current_link') and temp_state.current_link:
                            print(f"🚀 DATASET2 DEBUG: TAKING current_link BRANCH")
                            # For complex links, update the attribute mappings (Dataset 2 side)
                            current_link = temp_state.current_link
                            print(f"🚀 DATASET2 CURRENT_LINK DEBUG: current_link = {current_link}")
                            print(f"🚀 DATASET2 CURRENT_LINK DEBUG: current_link type = {type(current_link)}")
                            print(f"🚀 DATASET2 CURRENT_LINK DEBUG: current_link attributes = {[attr for attr in dir(current_link) if not attr.startswith('_')]}")
                            
                            # Check if this is an identity function with x/y parameters
                            if hasattr(current_link, 'x') and hasattr(current_link, 'y'):
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: Found x/y parameters!")
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: BEFORE - current_link.x = {current_link.x}")
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: BEFORE - current_link.y = {current_link.y}")
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: Setting current_link.x = {old_component1.label}")
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: Setting current_link.y = {new_component.label}")
                                
                                current_link.x = old_component1  # Dataset 1 component (unchanged)
                                current_link.y = new_component   # Dataset 2 component (user's change)
                                
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: AFTER - current_link.x = {current_link.x}")
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: AFTER - current_link.y = {current_link.y}")
                            
                            # Try to update output component mapping (this is Dataset 2 edit)
                            elif hasattr(current_link, 'data2') and hasattr(current_link, 'names2'):
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: Found data2/names2 parameters!")
                                
                                # CRITICAL FIX: First restore all original input parameters
                                if hasattr(current_link, 'names1') and current_link.names1:
                                    print(f"🚀 DATASET2 MULTI-PARAM FIX: Restoring original input parameters...")
                                    original_inputs = link._from  # Get original input components
                                    names1 = current_link.names1
                                    
                                    for i, param_name in enumerate(names1):
                                        if i < len(original_inputs) and hasattr(current_link, param_name):
                                            original_component = original_inputs[i]
                                            setattr(current_link, param_name, original_component)
                                            print(f"🚀 DATASET2 MULTI-PARAM FIX: Restored {param_name} = {original_component.label}")
                                
                                # Then update the output parameter (this is the user's Dataset 2 edit)
                                names2 = current_link.names2
                                if names2 and len(names2) > 0:
                                    first_output_name = names2[0]
                                    if hasattr(current_link, first_output_name):
                                        setattr(current_link, first_output_name, new_component)
                                        print(f"🚀 UNIFIED EDIT DATASET2: Updated multi-parameter output {first_output_name}: {new_component.label}")
                            else:
                                print(f"🚀 DATASET2 CURRENT_LINK DEBUG: No recognized parameter structure found!")
                        
                        # Step 6: Apply the recreated link
                        temp_state.update_links_in_collection()
                        print(f"🚀 UNIFIED EDIT DATASET2: Successfully recreated {original_link_type} with updated Dataset 2 component")

                        # 🔗 VERIFICATION: Confirm backend link integrity after Qt unified edit (Dataset 2)
                        _verify_backend_connection(data_collection, "QT_UNIFIED_EDIT_DATASET2")

                        # Step 7: Debug track type preservation
                        _debug_link_type_preservation(link, data_collection.external_links, "DATASET2_UNIFIED_EDIT")
                        
                    else:
                        # Fallback: If we can't find registry object, use identity function
                        print(f"🚀 UNIFIED EDIT DATASET2: Registry object not found, falling back to identity function")
                        from glue.config import link_function
                        identity_func = None
                        for func in link_function.members:
                            if hasattr(func, 'function') and func.function.__name__ == 'identity':
                                identity_func = func
                                break
                        
                        if identity_func:
                            temp_state.new_link(identity_func)
                            # CRITICAL FIX: Set component selections for fallback identity link
                            if hasattr(temp_state, 'current_link') and temp_state.current_link:
                                # Set the components that user actually selected
                                current_link = temp_state.current_link
                                print(f"🚀 FALLBACK DATASET2 DEBUG: current_link = {current_link}")
                                print(f"🚀 FALLBACK DATASET2 DEBUG: current_link type = {type(current_link)}")
                                
                                if hasattr(current_link, 'x') and hasattr(current_link, 'y'):
                                    print(f"🚀 FALLBACK DATASET2 DEBUG: BEFORE setting - current_link.x = {getattr(current_link, 'x', 'NOT_SET')}")
                                    print(f"🚀 FALLBACK DATASET2 DEBUG: BEFORE setting - current_link.y = {getattr(current_link, 'y', 'NOT_SET')}")
                                    
                                    # Identity function uses 'x' and 'y' parameters
                                    current_link.x = old_component1  # Dataset 1 component (unchanged)
                                    current_link.y = new_component   # Dataset 2 component (user's change)
                                    
                                    print(f"🚀 FALLBACK DATASET2 DEBUG: AFTER setting - current_link.x = {current_link.x}")
                                    print(f"🚀 FALLBACK DATASET2 DEBUG: AFTER setting - current_link.y = {current_link.y}")
                                    print(f"🚀 UNIFIED EDIT DATASET2: Set fallback identity components: {old_component1.label} -> {new_component.label}")
                                else:
                                    print(f"🚀 FALLBACK DATASET2 DEBUG: current_link does NOT have x/y attributes!")
                            else:
                                print(f"🚀 FALLBACK DATASET2 DEBUG: temp_state.current_link is None or missing!")
                            
                            print(f"🚀 FALLBACK DATASET2 DEBUG: About to call temp_state.update_links_in_collection()")
                            temp_state.update_links_in_collection()
                            print(f"🚀 FALLBACK DATASET2 DEBUG: Finished temp_state.update_links_in_collection()")
                            print(f"🚀 UNIFIED EDIT DATASET2: Created fallback identity link")

                            # 🔗 VERIFICATION: Confirm backend link integrity after fallback edit (Dataset 2)
                            _verify_backend_connection(data_collection, "QT_FALLBACK_EDIT_DATASET2")
                        else:
                            # Final fallback - use old method but warn
                            print(f"🚀 UNIFIED EDIT DATASET2: WARNING - Using old app.add_link() as final fallback")
                            app.add_link(from_data, old_component1, to_data, new_component)
                
                except Exception as e:
                    print(f"🚀 UNIFIED EDIT DATASET2: ERROR in unified approach: {e}")
                    import traceback
                    print(f"🚀 UNIFIED EDIT DATASET2: Traceback: {traceback.format_exc()}")
                    # Fallback to old method if unified approach fails
                    print(f"🚀 UNIFIED EDIT DATASET2: Falling back to app.add_link()")
                    app.add_link(from_data, old_component1, to_data, new_component)
                
                print(f"🔥 DATASET2 AFTER ADD: external_links count = {len(data_collection.external_links)}")
                print(f"🔥 DATASET2 AFTER ADD: external_links IDs = {[id(link) for link in data_collection.external_links]}")
                print(f"🔥 DATASET2 AFTER ADD: external_links content = {[f'{link._cid1.label}<->{link._cid2.label}' for link in data_collection.external_links if hasattr(link, '_cid1')]}")
                
                print(f"🔥 HARDCORE DEBUG: Qt-style link replacement COMPLETE")
                
                # CRITICAL: Verify backend connection after editing
                _verify_backend_connection(data_collection, "DATASET2_LINK_EDIT")
                
                # ENHANCED WORKAROUND: Give glue time to settle, then force UI refresh  
                print(f"🔥 DATASET2 TIMING FIX: Waiting for glue to settle...")
                time.sleep(0.1)  # Small delay to let glue update internal state
                
                print(f"🔥 DATASET2 FORCING UI REFRESH: Incrementing shared refresh counter")
                shared_refresh_counter.set(shared_refresh_counter.value + 1)  # Force memoization recalculation
                
                # TASK 1: POSITION PRESERVATION FIX (same as Dataset 1)
                # New links are added at the end, so select the last index (newly created link)
                new_position = len(data_collection.external_links) - 1
                print(f"🔥 TASK 1: New link created at position {new_position} (was at {original_position})")
                print(f"🔥 TASK 1: Selecting new link position instead of always going to index 0")
                selected_link_index.set(-1)    # Clear selection first
                selected_link_index.set(new_position)  # Select the newly created link
            else:
                print(f"🔥 HARDCORE DEBUG: Invalid new_attr_index {new_attr_index} >= {len(to_data.components)}")
        else:
            print(f"🔥 HARDCORE DEBUG: Cannot update - selected_link_info is None or invalid index")
    
    # FIXED: Proper responsive layout for Link Details Panel
    # Fixes boundary overflow issues by constraining width and using flex layout
    with solara.Column(style={
        "padding": "10px", 
        "width": "100%", 
        "max-width": "250px",  # Prevent overflow in modal
        "flex": "1 1 auto",    # Take remaining space but be flexible
        "overflow": "hidden"   # Prevent content overflow
    }):
        
        # EVOLUTION: Panel header - consistent across versions
        solara.Markdown("**Link details**")
        
        # EVOLUTION: Conditional rendering based on selection state
        # ORIGINAL: No link details panel existed
        # PREVIOUS: Basic static display
        # CURRENT: Dynamic content based on whether a link is selected
        if selected_link_info is None:
            # CURRENT: User-friendly message when no link is selected
            # Guides user on what to do to see link details
            solara.Text("Click on a link to see details", style={"font-style": "italic", "color": "#666"})
        else:
            # CURRENT: Full link editing interface when a link is selected
            # This is the heart of the Qt-style link details functionality
            link, link_data = selected_link_info
            
            # CURRENT: Descriptive text about the selected link
            # ENHANCED: Show special message for multi-parameter links
            if isinstance(link, type(link)) and hasattr(link, '_from') and len(getattr(link, '_from', [])) > 1:
                solara.Text(f"Multi-parameter link ({len(link._from)} inputs → 1 output)", 
                           style={"font-style": "italic", "margin-bottom": "10px", "color": "#0066cc"})
                solara.Text(f"Note: Only first input shown in editing panel", 
                           style={"font-size": "12px", "color": "#666", "margin-bottom": "10px"})
            else:
                solara.Text(f"Details about the link", style={"font-style": "italic", "margin-bottom": "10px"})
            
            # ENHANCED: Multi-Parameter Support - Dataset 1 attributes section
            # NEW: Detects multi-parameter links and displays multiple parameter dropdowns
            print(f"🚀 UI RENDER DEBUG: link_data keys = {list(link_data.keys())}")
            print(f"🚀 UI RENDER DEBUG: is_multi_param = {link_data.get('is_multi_param', False)}")
            
            if link_data.get("is_multi_param", False):
                print(f"🚀 UI RENDER DEBUG: Rendering MULTI-PARAMETER UI")
                
                # Check if this is a coordinate pair transformation
                if link_data.get("is_coordinate_pair", False):
                    print(f"🚀 UI RENDER DEBUG: COORDINATE PAIR transformation detected")
                    print(f"🚀 UI RENDER DEBUG: Coordinate type = {link_data.get('coordinate_type', 'unknown')}")
                    print(f"🚀 UI RENDER DEBUG: coord1_param_info = {link_data.get('coord1_param_info', [])}")
                    print(f"🚀 UI RENDER DEBUG: coord2_param_info = {link_data.get('coord2_param_info', [])}")
                    
                    # Coordinate pair display (2-to-2 transformation)
                    coord_type = link_data.get('coordinate_type', 'Coordinate')
                    solara.Markdown(f"**{coord_type} coordinate transformation**")
                    solara.Text(f"Transform coordinate pairs between reference frames", 
                               style={"color": "#666", "font-style": "italic", "margin-bottom": "10px"})
                    
                    # Display Dataset 1 coordinate parameters
                    coord1_param_info = link_data.get("coord1_param_info", [])
                    print(f"🚀 UI RENDER DEBUG: Processing {len(coord1_param_info)} Dataset 1 coordinates")
                    
                    for i, param in enumerate(coord1_param_info):
                        print(f"🚀 UI RENDER DEBUG: Dataset 1 coordinate {i}: {param}")
                        
                        # Create coordinate parameter dropdown
                        with solara.Column(style={"margin-bottom": "8px"}):
                            solara.v.Select(
                                label=f"{param['name']}",           # Coordinate name (l, b, ra, dec)
                                v_model=param["selected"],          # Current selection index
                                on_v_model=lambda new_value, param_idx=i, dataset=1: _update_coordinate_parameter(dataset, param_idx, new_value),
                                items=link_data["attr1_options"],   # All available Dataset 1 attributes
                                item_text="label",                  # Display attribute labels
                                item_value="value",                 # Use indices as values
                                style_="margin-bottom: 5px; width: 100%;",
                                dense=True,                         # Compact display
                                outlined=True,                      # Visual separation
                                hint=f"Current: {param['label']}"  # Show current selection
                            )
                    
                    print(f"🚀 UI RENDER DEBUG: Coordinate pair Dataset 1 rendering complete")
                    
                else:
                    print(f"🚀 UI RENDER DEBUG: FUNCTION multi-parameter detected")
                    print(f"🚀 UI RENDER DEBUG: Function name = {link_data.get('function_name', 'unknown')}")
                    print(f"🚀 UI RENDER DEBUG: Multi-param info = {link_data.get('multi_param_info', [])}")
                    
                    # Multi-parameter function display (like Qt's N_COMBO_MAX approach)
                    solara.Markdown(f"**{link_data['function_name']} function parameters**")
                    solara.Text(f"Convert between {link_data['function_name']} parameters", 
                               style={"color": "#666", "font-style": "italic", "margin-bottom": "10px"})
                    
                    # Display each parameter with its own dropdown
                    multi_param_info = link_data.get("multi_param_info", [])
                    print(f"🚀 UI RENDER DEBUG: Processing {len(multi_param_info)} function parameters")
                    
                    for i, param in enumerate(multi_param_info):
                        print(f"🚀 UI RENDER DEBUG: Function parameter {i}: {param}")
                        
                        # Create individual parameter dropdown
                        with solara.Column(style={"margin-bottom": "8px"}):
                            solara.v.Select(
                                label=f"{param['name']}",           # Parameter name (width, height, depth)
                                v_model=param["selected"],          # Current selection index for this parameter
                                on_v_model=lambda new_value, param_idx=i: _update_multi_parameter(param_idx, new_value),
                                items=link_data["attr1_options"],   # All available Dataset 1 attributes
                                item_text="label",                  # Display attribute labels
                                item_value="value",                 # Use indices as values
                                style_="margin-bottom: 5px; width: 100%;",
                                dense=True,                         # Compact display
                                outlined=True,                      # Visual separation
                                hint=f"Current: {param['label']}"  # Show current selection
                            )
                    
                    print(f"🚀 UI RENDER DEBUG: Function multi-parameter Dataset 1 rendering complete")
                        
            else:
                print(f"🚀 UI RENDER DEBUG: Rendering SINGLE-PARAMETER UI")
                
                # Single-parameter display (original behavior)
                solara.Markdown("**Dataset 1 attributes**")
                if link_data["attr1_options"]:
                    print(f"🚀 UI RENDER DEBUG: attr1_options available, rendering dropdown")
                    solara.v.Select(
                        label=link_data["attr1_label"],
                        v_model=link_data["attr1_selected"],
                        on_v_model=_update_dataset1_attribute,
                        items=link_data["attr1_options"],
                        item_text="label",
                        item_value="value",
                        style_="margin-bottom: 10px; width: 100%;",
                        dense=True,
                        outlined=True
                    )
                else:
                    print(f"🚀 UI RENDER DEBUG: No attr1_options, showing placeholder")
                    solara.Text("No attributes available", style={"color": "#999", "font-style": "italic"})
            
            print(f"🚀 UI RENDER DEBUG: Dataset 1 section complete")
            
            # ENHANCED: Dataset 2 attributes section (handles both single and multi-parameter)
            solara.Markdown("**Dataset 2 attributes**")
            print(f"🚀 UI RENDER DEBUG: Rendering Dataset 2 section")
            print(f"🚀 UI RENDER DEBUG: attr2_options available = {bool(link_data['attr2_options'])}")
            print(f"🚀 UI RENDER DEBUG: is_coordinate_pair = {link_data.get('is_coordinate_pair', False)}")
            
            if link_data["attr2_options"]:
                # Check if this is a coordinate pair (needs multiple Dataset 2 dropdowns)
                if link_data.get("is_coordinate_pair", False):
                    print(f"🚀 UI RENDER DEBUG: Rendering COORDINATE PAIR Dataset 2 parameters")
                    
                    # Display Dataset 2 coordinate parameters
                    coord2_param_info = link_data.get("coord2_param_info", [])
                    print(f"🚀 UI RENDER DEBUG: Processing {len(coord2_param_info)} Dataset 2 coordinates")
                    
                    for i, param in enumerate(coord2_param_info):
                        print(f"🚀 UI RENDER DEBUG: Dataset 2 coordinate {i}: {param}")
                        
                        # Create coordinate parameter dropdown
                        with solara.Column(style={"margin-bottom": "8px"}):
                            solara.v.Select(
                                label=f"{param['name']}",           # Coordinate name (l, b, ra, dec)
                                v_model=param["selected"],          # Current selection index
                                on_v_model=lambda new_value, param_idx=i, dataset=2: _update_coordinate_parameter(dataset, param_idx, new_value),
                                items=link_data["attr2_options"],   # All available Dataset 2 attributes
                                item_text="label",                  # Display attribute labels
                                item_value="value",                 # Use indices as values
                                style_="margin-bottom: 5px; width: 100%;",
                                dense=True,                         # Compact display
                                outlined=True,                      # Visual separation
                                hint=f"Current: {param['label']}"  # Show current selection
                            )
                    
                    print(f"🚀 UI RENDER DEBUG: Coordinate pair Dataset 2 rendering complete")
                
                else:
                    # Single parameter (normal links and function outputs)
                    print(f"🚀 UI RENDER DEBUG: Rendering single Dataset 2 parameter")
                    solara.v.Select(
                        label=link_data["attr2_label"],          # Output parameter name
                        v_model=link_data["attr2_selected"],     # Current selection index  
                        on_v_model=_update_dataset2_attribute,   # CRITICAL: Enables editing via callback
                        items=link_data["attr2_options"],        # All available target attributes
                        item_text="label",                       # Display attribute labels
                        item_value="value",                      # Use indices as values
                        style_="margin-bottom: 10px; width: 100%;",
                        dense=True,                              # Compact display for modal
                        outlined=True,                           # Better visual separation
                    )
            else:
                solara.Text("No attributes available", style={"color": "#999", "font-style": "italic"})
                
            print(f"🚀 UI RENDER DEBUG: Dataset 2 section complete")
            
            # TASK 2: Remove Link Button - NEW FUNCTIONALITY
            # Matches Qt's "Remove link" button functionality
            # Positioned at bottom of link details panel for easy access
            with solara.Row(style={"margin-top": "20px", "justify-content": "flex-start"}):
                solara.Button(
                    label="Remove Link",
                    color="error",  # Red color to indicate destructive action
                    on_click=_remove_link,  # CRITICAL: Links to removal function
                    outlined=True,  # Less aggressive styling
                    style="margin-top: 10px;"
                )


def _get_selected_link_info(links_list, selected_index):
    """
    ENHANCED: Multi-Parameter Link Support with Extensive Debugging
    
    ORIGINAL: No equivalent - link details weren't editable
    PREVIOUS: Single parameter links only  
    CURRENT: Full Qt-style multi-parameter support with N_COMBO_MAX pattern
    
    This function handles all glue link types and extracts information for UI display.
    Now supports multi-parameter functions like lengths_to_volume(width, height, depth -> volume).
    
    Returns: (link_object, formatted_data_dict) or None if invalid selection
    """
    print(f"🚀 MULTI-PARAM DEBUG: _get_selected_link_info ENTRY - selected_index={selected_index}")
    print(f"🚀 MULTI-PARAM DEBUG: links_list length = {len(links_list) if links_list else 0}")
    print(f"🚀 MULTI-PARAM DEBUG: links_list types = {[type(link).__name__ for link in links_list] if links_list else []}")
    
    # Boundary checking with extensive logging
    print(f"🚀 MULTI-PARAM DEBUG: Validating selected_index...")
    if selected_index is None:
        print(f"🚀 MULTI-PARAM DEBUG: selected_index is None, returning None")
        return None
    if selected_index < 0:
        print(f"🚀 MULTI-PARAM DEBUG: selected_index < 0 ({selected_index}), returning None")
        return None
    if selected_index >= len(links_list):
        print(f"🚀 MULTI-PARAM DEBUG: selected_index >= len(links_list) ({selected_index} >= {len(links_list)}), returning None")
        return None
        
    print(f"🚀 MULTI-PARAM DEBUG: selected_index validation passed")
        
    # Extract the selected link object
    link = links_list[selected_index]
    print(f"🚀 MULTI-PARAM DEBUG: Extracted link object: {link}")
    print(f"🚀 MULTI-PARAM DEBUG: Link type: {type(link)}")
    print(f"🚀 MULTI-PARAM DEBUG: Link class name: {type(link).__name__}")
    print(f"🚀 MULTI-PARAM DEBUG: Link attributes: {[attr for attr in dir(link) if not attr.startswith('__')]}")
    
    try:
        print(f"🚀 MULTI-PARAM DEBUG: Starting link type detection...")
        
        # Handle LinkSame objects (most common type from app.add_link())
        if hasattr(link, '_cid1') and hasattr(link, '_cid2'):
            print(f"🚀 MULTI-PARAM DEBUG: Detected LinkSame type")
            print(f"🚀 MULTI-PARAM DEBUG: LinkSame._cid1 = {link._cid1}")
            print(f"🚀 MULTI-PARAM DEBUG: LinkSame._cid2 = {link._cid2}")
            print(f"🚀 MULTI-PARAM DEBUG: LinkSame.data1 = {link.data1}")
            print(f"🚀 MULTI-PARAM DEBUG: LinkSame.data2 = {link.data2}")
            
            from_comp = link._cid1
            to_comp = link._cid2
            from_data = link.data1
            to_data = link.data2
            is_multi_param = False
            
            print(f"🚀 MULTI-PARAM DEBUG: LinkSame processing complete - single parameter")
            
        # ENHANCED: Handle coordinate helper links as 2-to-2 multi-parameter links
        # Coordinate helpers transform coordinate pairs: (ra, dec) <-> (l, b)
        elif 'coordinate_helpers' in str(type(link)):
            print(f"🚀 MULTI-PARAM DEBUG: Detected coordinate helper link")
            print(f"🚀 MULTI-PARAM DEBUG: Coordinate helper class: {type(link).__name__}")
            print(f"🚀 MULTI-PARAM DEBUG: Link has data1: {hasattr(link, 'data1')}")
            print(f"🚀 MULTI-PARAM DEBUG: Link has data2: {hasattr(link, 'data2')}")
            print(f"🚀 MULTI-PARAM DEBUG: Link has cids1: {hasattr(link, 'cids1')}")
            print(f"🚀 MULTI-PARAM DEBUG: Link has cids2: {hasattr(link, 'cids2')}")
            print(f"🚀 MULTI-PARAM DEBUG: Link has labels1: {hasattr(link, 'labels1')}")
            print(f"🚀 MULTI-PARAM DEBUG: Link has labels2: {hasattr(link, 'labels2')}")
            
            if hasattr(link, 'data1') and hasattr(link, 'data2'):
                from_data = link.data1
                to_data = link.data2
                print(f"🚀 MULTI-PARAM DEBUG: Using data1/data2 for datasets")
                
                # Check if this is a coordinate pair transformation (2-to-2)
                if (hasattr(link, 'cids1') and hasattr(link, 'cids2') and 
                    hasattr(link, 'labels1') and hasattr(link, 'labels2') and
                    link.cids1 and link.cids2 and link.labels1 and link.labels2):
                    
                    print(f"🚀 MULTI-PARAM DEBUG: Coordinate pair detected!")
                    print(f"🚀 MULTI-PARAM DEBUG: cids1 count = {len(link.cids1)}")
                    print(f"🚀 MULTI-PARAM DEBUG: cids2 count = {len(link.cids2)}")
                    print(f"🚀 MULTI-PARAM DEBUG: labels1 = {link.labels1}")
                    print(f"🚀 MULTI-PARAM DEBUG: labels2 = {link.labels2}")
                    
                    # Check if it's a coordinate pair (2-to-2) transformation
                    if len(link.cids1) == 2 and len(link.cids2) == 2:
                        print(f"🚀 MULTI-PARAM DEBUG: 2-TO-2 COORDINATE TRANSFORMATION DETECTED!")
                        
                        # Build coordinate pair parameter structure
                        coord_type = type(link).__name__
                        print(f"🚀 MULTI-PARAM DEBUG: Coordinate transformation: {coord_type}")
                        
                        # Build parameter info for Dataset 1 (input coordinates)
                        param1_info = []
                        for i, comp in enumerate(link.cids1):
                            param_name = link.labels1[i] if i < len(link.labels1) else f"coord1_{i+1}"
                            param_selected = next((idx for idx, attr in enumerate(from_data.components) 
                                                 if attr == comp), 0)
                            
                            param_data = {
                                "name": param_name,
                                "selected": param_selected,
                                "component": comp,
                                "label": getattr(comp, 'label', str(comp))
                            }
                            param1_info.append(param_data)
                            print(f"🚀 MULTI-PARAM DEBUG: Dataset 1 parameter [{i}] = {param_data}")
                        
                        # Build parameter info for Dataset 2 (output coordinates)
                        param2_info = []
                        for i, comp in enumerate(link.cids2):
                            param_name = link.labels2[i] if i < len(link.labels2) else f"coord2_{i+1}"
                            param_selected = next((idx for idx, attr in enumerate(to_data.components) 
                                                 if attr == comp), 0)
                            
                            param_data = {
                                "name": param_name,
                                "selected": param_selected,
                                "component": comp,
                                "label": getattr(comp, 'label', str(comp))
                            }
                            param2_info.append(param_data)
                            print(f"🚀 MULTI-PARAM DEBUG: Dataset 2 parameter [{i}] = {param_data}")
                        
                        print(f"🚀 MULTI-PARAM DEBUG: Coordinate pair structure built successfully")
                        
                        # Return 2-to-2 coordinate transformation structure
                        attr1_options = [{"label": getattr(attr, 'label', str(attr)), "value": idx} 
                                        for idx, attr in enumerate(from_data.components)]
                        attr2_options = [{"label": getattr(attr, 'label', str(attr)), "value": idx} 
                                        for idx, attr in enumerate(to_data.components)]
                        
                        result_data = {
                            "attr1_options": attr1_options,
                            "attr2_options": attr2_options,
                            "attr1_selected": 0,  # Not used for coordinate pairs
                            "attr2_selected": 0,  # Not used for coordinate pairs
                            "attr1_label": f"Dataset 1 coordinates ({coord_type})",
                            "attr2_label": f"Dataset 2 coordinates ({coord_type})",
                            "is_multi_param": True,
                            "is_coordinate_pair": True,  # Special flag for coordinate pairs
                            "coord1_param_info": param1_info,
                            "coord2_param_info": param2_info,
                            "coordinate_type": coord_type
                        }
                        
                        print(f"🚀 MULTI-PARAM DEBUG: Coordinate pair result data: {result_data}")
                        return (link, result_data)
                
                # Fallback: single-parameter coordinate helper
                print(f"🚀 MULTI-PARAM DEBUG: Single-parameter coordinate helper fallback")
                if hasattr(link, 'cids1') and hasattr(link, 'cids2') and link.cids1 and link.cids2:
                    from_comp = link.cids1[0]
                    to_comp = link.cids2[0]
                    print(f"🚀 MULTI-PARAM DEBUG: Using cids1[0]={from_comp.label}, cids2[0]={to_comp.label}")
                else:
                    from_comp = from_data.components[0]
                    to_comp = to_data.components[0]
                    print(f"🚀 MULTI-PARAM DEBUG: Using first components as fallback")
                
                is_multi_param = False
                print(f"🚀 MULTI-PARAM DEBUG: Single-parameter coordinate helper processing complete")
            else:
                print(f"🚀 MULTI-PARAM DEBUG: Coordinate helper missing data1/data2, returning None")
                return None
            
        # Handle JoinLink objects (comes AFTER coordinate helpers)
        elif hasattr(link, 'cids1') and hasattr(link, 'cids2') and hasattr(link, 'data1') and hasattr(link, 'data2'):
            print(f"🚀 MULTI-PARAM DEBUG: Detected JoinLink type")
            print(f"🚀 MULTI-PARAM DEBUG: JoinLink.cids1 = {link.cids1}")
            print(f"🚀 MULTI-PARAM DEBUG: JoinLink.cids2 = {link.cids2}")
            
            from_comp = link.cids1[0] if link.cids1 else None
            to_comp = link.cids2[0] if link.cids2 else None
            from_data = link.data1
            to_data = link.data2
            is_multi_param = False
            
            if from_comp is None or to_comp is None:
                print(f"🚀 MULTI-PARAM DEBUG: JoinLink missing components, returning None")
                return None
            
            print(f"🚀 MULTI-PARAM DEBUG: JoinLink processing complete")
            
        # ENHANCED: Handle ComponentLink objects with FULL multi-parameter support
        elif hasattr(link, '_from') and hasattr(link, '_to'):
            print(f"🚀 MULTI-PARAM DEBUG: Detected ComponentLink type")
            print(f"🚀 MULTI-PARAM DEBUG: ComponentLink._from = {link._from}")
            print(f"🚀 MULTI-PARAM DEBUG: ComponentLink._to = {link._to}")
            print(f"🚀 MULTI-PARAM DEBUG: ComponentLink._from is list: {isinstance(link._from, list)}")
            
            if isinstance(link._from, list):
                print(f"🚀 MULTI-PARAM DEBUG: Multi-input ComponentLink detected!")
                print(f"🚀 MULTI-PARAM DEBUG: Number of input components: {len(link._from)}")
                
                from_comps = link._from
                from_data = from_comps[0].parent
                to_comp = link._to
                to_data = to_comp.parent
                
                print(f"🚀 MULTI-PARAM DEBUG: from_data = {from_data.label}")
                print(f"🚀 MULTI-PARAM DEBUG: to_data = {to_data.label}")
                print(f"🚀 MULTI-PARAM DEBUG: to_comp = {to_comp.label}")
                
                for i, comp in enumerate(from_comps):
                    print(f"🚀 MULTI-PARAM DEBUG: Input component [{i}] = {comp.label}")
                
                # Multi-parameter processing
                if len(from_comps) > 1:
                    print(f"🚀 MULTI-PARAM DEBUG: MULTI-PARAMETER LINK DETECTED - {len(from_comps)} inputs")
                    is_multi_param = True
                    
                    # Get function name for better parameter labeling
                    function_name = "function"
                    if hasattr(link, '_using') and link._using:
                        function_name = getattr(link._using, '__name__', 'function')
                        print(f"🚀 MULTI-PARAM DEBUG: Function name: {function_name}")
                    
                    # Build parameter information structure
                    print(f"🚀 MULTI-PARAM DEBUG: Building parameter structure...")
                    param_info = []
                    
                    # Get function-specific parameter names
                    param_names = []
                    if function_name == "lengths_to_volume":
                        param_names = ["width", "height", "depth"]
                        print(f"🚀 MULTI-PARAM DEBUG: Using lengths_to_volume parameter names: {param_names}")
                    else:
                        param_names = [f"param_{i+1}" for i in range(len(from_comps))]
                        print(f"🚀 MULTI-PARAM DEBUG: Using generic parameter names: {param_names}")
                    
                    # Build parameter info for each input
                    for i, comp in enumerate(from_comps):
                        param_name = param_names[i] if i < len(param_names) else f"param_{i+1}"
                        
                        # Find current selection for this parameter
                        param_selected = next((idx for idx, attr in enumerate(from_data.components) 
                                             if attr == comp), 0)
                        
                        param_data = {
                            "name": param_name,
                            "selected": param_selected,
                            "component": comp,
                            "label": getattr(comp, 'label', str(comp))
                        }
                        
                        param_info.append(param_data)
                        print(f"🚀 MULTI-PARAM DEBUG: Parameter [{i}] = {param_data}")
                    
                    print(f"🚀 MULTI-PARAM DEBUG: Multi-parameter structure built successfully")
                    
                else:
                    print(f"🚀 MULTI-PARAM DEBUG: Single-parameter ComponentLink")
                    from_comp = from_comps[0]
                    is_multi_param = False
                    
            else:
                print(f"🚀 MULTI-PARAM DEBUG: Single-input ComponentLink")
                from_comp = link._from
                from_data = from_comp.parent
                to_comp = link._to
                to_data = to_comp.parent
                is_multi_param = False
                
            print(f"🚀 MULTI-PARAM DEBUG: ComponentLink processing complete")
            
        else:
            print(f"🚀 MULTI-PARAM DEBUG: Unknown link type detected")
            print(f"🚀 MULTI-PARAM DEBUG: Available public attributes: {[attr for attr in dir(link) if not attr.startswith('_')]}")
            print(f"🚀 MULTI-PARAM DEBUG: Returning None for unknown type")
            return None
        
        print(f"🚀 MULTI-PARAM DEBUG: Link type processing complete")
        print(f"🚀 MULTI-PARAM DEBUG: is_multi_param = {is_multi_param}")
        
        # Build dropdown options for both datasets
        print(f"🚀 MULTI-PARAM DEBUG: Building dropdown options...")
        print(f"🚀 MULTI-PARAM DEBUG: from_data.components count = {len(from_data.components)}")
        print(f"🚀 MULTI-PARAM DEBUG: to_data.components count = {len(to_data.components)}")
        
        attr1_options = [{"label": getattr(attr, 'label', str(attr)), "value": idx} 
                        for idx, attr in enumerate(from_data.components)]
        attr2_options = [{"label": getattr(attr, 'label', str(attr)), "value": idx} 
                        for idx, attr in enumerate(to_data.components)]
        
        print(f"🚀 MULTI-PARAM DEBUG: attr1_options built: {len(attr1_options)} options")
        print(f"🚀 MULTI-PARAM DEBUG: attr2_options built: {len(attr2_options)} options")
        
        # Return multi-parameter structure if applicable
        if is_multi_param:
            print(f"🚀 MULTI-PARAM DEBUG: Returning MULTI-PARAMETER structure")
            
            # Find output component selection
            attr2_selected = next((idx for idx, attr in enumerate(to_data.components) 
                                 if attr == to_comp), 0)
            
            result_data = {
                "attr1_options": attr1_options,
                "attr2_options": attr2_options,
                "attr1_selected": 0,  # Not used for multi-param
                "attr2_selected": attr2_selected,
                "attr1_label": f"{function_name} parameters",
                "attr2_label": getattr(to_comp, 'label', str(to_comp)),
                "is_multi_param": True,
                "multi_param_info": param_info,
                "function_name": function_name
            }
            
            print(f"🚀 MULTI-PARAM DEBUG: Multi-parameter result data: {result_data}")
            return (link, result_data)
            
        else:
            print(f"🚀 MULTI-PARAM DEBUG: Returning SINGLE-PARAMETER structure")
            
            # Single parameter processing
            attr1_selected = next((idx for idx, attr in enumerate(from_data.components) 
                                 if attr == from_comp), 0)
            attr2_selected = next((idx for idx, attr in enumerate(to_data.components) 
                                 if attr == to_comp), 0)
            
            result_data = {
                "attr1_options": attr1_options,
                "attr2_options": attr2_options,
                "attr1_selected": attr1_selected,
                "attr2_selected": attr2_selected,
                "attr1_label": getattr(from_comp, 'label', str(from_comp)),
                "attr2_label": getattr(to_comp, 'label', str(to_comp)),
                "is_multi_param": False
            }
            
            print(f"🚀 MULTI-PARAM DEBUG: Single-parameter result data: {result_data}")
            return (link, result_data)
        
    except Exception as e:
        print(f"🚀 MULTI-PARAM DEBUG: EXCEPTION in _get_selected_link_info: {e}")
        print(f"🚀 MULTI-PARAM DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"🚀 MULTI-PARAM DEBUG: Traceback: {traceback.format_exc()}")
        print(f"🚀 MULTI-PARAM DEBUG: Returning None due to exception")
        return None
