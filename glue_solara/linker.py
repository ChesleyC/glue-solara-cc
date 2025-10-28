"""
Solara-based link editor for Glue data visualization.

Architecture:
  UI Layer:     Solara reactive components (this file)
  Logic Layer:  Qt's LinkEditorState (glue.dialogs.link_editor.state)
  Data Layer:   Glue-core DataCollection (glue.core.data_collection)

Key Pattern:
  Link editing uses Qt's atomic update pattern via LinkEditorState:
    1. Create temp_state = LinkEditorState(data_collection)
    2. Modify temp_state.links (add/remove/edit)
    3. Call temp_state.update_links_in_collection() - atomically applies changes

Performance:
  Registry access (.members) triggers lazy plugin loading - expensive and freezes UI.
  Solution: Cache all registry data at module import, never access during rendering.

Qt Reference: glue_qt/dialogs/link_editor/link_editor.py (LinkEditor, LinkMenu classes)
"""

import glue.core.message as msg
import solara
from glue.core import DataCollection
from glue.core.link_helpers import BaseMultiLink, JoinLink
from glue.dialogs.link_editor.state import LinkEditorState
from glue_jupyter import JupyterApplication

from .hooks import use_glue_watch

# ═══════════════════════════════════════════════════════════════════════════
#  REGISTRY CACHING - Performance Critical
# ═══════════════════════════════════════════════════════════════════════════
#
# Problem: link_function.members and link_helper.members trigger lazy plugin
#          loading (imports, object instantiation) - freezes Solara UI if
#          accessed during component rendering.
#
# Solution: Access registries ONCE at module import, cache results, never
#           access .members again. Same pattern as Qt's LinkMenu.__init__().
#
# Qt Reference: glue_qt/dialogs/link_editor/link_editor.py:27-48
# ═══════════════════════════════════════════════════════════════════════════

_CACHED_LINK_MENU_DATA = None


def get_function_name(registry_item):
    """Extract display name from link_function or link_helper registry item.

    Args:
        registry_item: LinkFunction or LinkHelper object from glue.config

    Returns:
        str: Display name for UI (e.g., "Convert to volume", "Join on keys")
    """
    if hasattr(registry_item, "display") and registry_item.display is not None:
        return registry_item.display
    elif hasattr(registry_item, "function"):
        return registry_item.function.__name__
    elif hasattr(registry_item, "helper"):
        if hasattr(registry_item.helper, "display") and registry_item.helper.display:
            return registry_item.helper.display
        else:
            return registry_item.helper.__name__
    else:
        return str(registry_item)


def _build_link_menu_cache():
    """Build hierarchical menu structure from glue registries.

    Accesses link_function.members and link_helper.members ONCE to build
    category-organized menu structure. Never call during rendering.

    Returns:
        dict: {category_name: [menu_items]}
              Each menu_item: {type, display, registry_object, description}

    Glue-core connections:
        - glue.config.link_function.members (transformation functions)
        - glue.config.link_helper.members (multi-component link collections)

    Qt Reference: glue_qt/dialogs/link_editor/link_editor.py:32-48
    """
    global _CACHED_LINK_MENU_DATA

    if _CACHED_LINK_MENU_DATA is not None:
        return _CACHED_LINK_MENU_DATA

    from glue.config import link_function, link_helper

    # Collect all unique categories, prioritizing "General" first
    categories = []
    function_count = 0
    for function in link_function.members:
        if len(function.output_labels) == 1:
            categories.append(function.category)
            function_count += 1

    helper_count = 0
    for helper in link_helper.members:
        categories.append(helper.category)
        helper_count += 1

    categories = ["General"] + sorted(set(categories) - set(["General"]))

    # Build menu structure: {category: [items]}
    menu_data = {}

    for category in categories:
        menu_data[category] = []

        for function in link_function.members:
            if function.category == category and len(function.output_labels) == 1:
                try:
                    display_name = get_function_name(function)
                    menu_data[category].append(
                        {
                            "type": "function",
                            "display": display_name,
                            "registry_object": function,
                            "description": getattr(function, "info", ""),
                        }
                    )
                except Exception:
                    pass

        for helper in link_helper.members:
            if helper.category == category:
                try:
                    display_name = get_function_name(helper)
                    menu_data[category].append(
                        {
                            "type": "helper",
                            "display": display_name,
                            "registry_object": helper,
                            "description": getattr(helper.helper, "description", ""),
                        }
                    )
                except Exception:
                    pass

    # Ensure identity function is available (used as fallback in editing)
    identity_function = None
    for function in link_function.members:
        if hasattr(function, "function") and function.function.__name__ == "identity":
            identity_function = function
            break

    if identity_function and "General" in menu_data:
        identity_already_added = any(item["display"] == "identity" for item in menu_data["General"])
        if not identity_already_added:
            menu_data["General"].append(
                {
                    "type": "function",
                    "display": "identity",
                    "registry_object": identity_function,
                    "description": "Identity link function",
                }
            )

    _CACHED_LINK_MENU_DATA = menu_data
    return menu_data


def get_link_menu_data():
    """Get cached registry data (safe for Solara components - no .members access)."""
    return _build_link_menu_cache()


# Module initialization: cache registry data before any component renders
try:
    pass
except Exception:
    pass

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
    """Hierarchical link creation UI (General/Astronomy/Join categories).

    Creates links using Qt's LinkEditorState pattern:
      temp_state.new_link(registry_object) → temp_state.update_links_in_collection()

    Args:
        app: JupyterApplication instance
        data_collection: Glue DataCollection
        selected_data1/2: Dataset indices
        selected_row1/2: Attribute indices (unused - future extension)
        shared_refresh_counter: UI refresh trigger

    Glue-core connections:
        - glue.dialogs.link_editor.state.LinkEditorState (Qt's state manager)

    Qt Reference: glue_qt/dialogs/link_editor/link_editor.py:25-49 (LinkMenu)
    """

    selected_category = solara.use_reactive("general")
    selected_link_item = solara.use_reactive("")

    categories = get_link_menu_data()
    category_names = list(categories.keys())
    current_category_items = categories.get(selected_category.value, [])
    item_names = [item["display"] for item in current_category_items]

    def create_advanced_link():
        """Create link using Qt's LinkEditorState.new_link() method."""
        if not selected_link_item.value or selected_data1.value == -1 or selected_data2.value == -1:
            return

        selected_item = None
        for item in current_category_items:
            if item["display"] == selected_link_item.value:
                selected_item = item
                break

        if not selected_item:
            return

        data1 = data_collection[selected_data1.value]
        data2 = data_collection[selected_data2.value]
        registry_object = selected_item["registry_object"]
        helper_class = getattr(registry_object, "helper", None)
        helper_class_name = helper_class.__name__ if helper_class else ""
        is_join_request = helper_class_name == "JoinLink"

        try:
            temp_state = LinkEditorState(data_collection)
            temp_state.data1 = data1
            temp_state.data2 = data2

            try:
                temp_state.new_link(registry_object)
            except Exception:
                shared_refresh_counter.set(shared_refresh_counter.value + 1)
                return

            # JoinLink duplicate detection (JoinLink.__eq__ treats similar links as identical)
            if is_join_request and temp_state.links:
                candidate_state = temp_state.links[-1]
                candidate_link = candidate_state.link

                duplicate_link = next(
                    (
                        existing
                        for existing in data_collection.external_links
                        if existing == candidate_link
                    ),
                    None,
                )

                if duplicate_link is not None:
                    print(
                        f"⚠️ ADVANCED: Duplicate JoinLink detected between {data1.label} and {data2.label}"
                    )
                    print(
                        f"⚠️ ADVANCED: Existing link {duplicate_link} blocks creation of identical join"
                    )
                    shared_refresh_counter.set(shared_refresh_counter.value + 1)
                    return

            try:
                temp_state.update_links_in_collection()
            except Exception as e:
                error_msg = str(e)
                if "inverse" in error_msg.lower() or "JoinLink" in error_msg:
                    print(
                        f"⚠️ ADVANCED: Cannot create duplicate JoinLink between {data1.label} and {data2.label}"
                    )
                    print("⚠️ ADVANCED: A JoinLink with these parameters already exists")
                    print(
                        "⚠️ ADVANCED: Hint: JoinLinks are unique - only one join per dataset pair is allowed"
                    )
                shared_refresh_counter.set(shared_refresh_counter.value + 1)
                return
            shared_refresh_counter.set(shared_refresh_counter.value + 1)

        except Exception:
            raise

    with solara.Card(title="Create Advanced Link", elevation=2):
        with solara.Column():
            solara.Select(
                label="Link Category",
                value=selected_category,
                values=category_names,
            )

            if current_category_items:
                solara.Select(
                    label=f"{selected_category.value.title()} Links",
                    value=selected_link_item,
                    values=item_names,
                )

                if selected_link_item.value:
                    selected_item = next(
                        (
                            item
                            for item in current_category_items
                            if item["display"] == selected_link_item.value
                        ),
                        None,
                    )
                    if selected_item and selected_item.get("description"):
                        solara.Text(
                            f"Description: {selected_item['description']}",
                            style={"font-style": "italic"},
                        )

                with solara.Row():
                    solara.Button(
                        "Create Link",
                        on_click=create_advanced_link,
                        disabled=not selected_link_item.value
                        or selected_data1.value == -1
                        or selected_data2.value == -1,
                        color="primary",
                    )
            else:
                solara.Text(
                    f"No links available in '{selected_category.value}' category",
                    style={"color": "gray"},
                )


def _create_identity_link(data1, data2, row1_index, row2_index, app):
    """Legacy helper: Create identity link using app.add_link()."""
    comp1 = (
        data1.components[row1_index]
        if row1_index >= 0 and row1_index < len(data1.components)
        else data1.components[0]
    )
    comp2 = (
        data2.components[row2_index]
        if row2_index >= 0 and row2_index < len(data2.components)
        else data2.components[0]
    )
    app.add_link(data1, comp1, data2, comp2)


# ═══════════════════════════════════════════════════════════════════════════
#  LEGACY HELPER FUNCTIONS - Not Used (Replaced by LinkEditorState)
# ═══════════════════════════════════════════════════════════════════════════
# Note: Current code uses temp_state.new_link() from Qt's LinkEditorState.
#       These functions remain for potential future use or custom extensions.
# ═══════════════════════════════════════════════════════════════════════════


def _create_link_from_registry_object_with_dynamic_params(
    app, data_collection, registry_object, item_type, data1, data2, param_selections
):
    """Legacy: Create link with dynamic multi-parameter support.

    Supports N→1 patterns like lengths_to_volume(width, height, depth) → volume.
    Current code uses temp_state.new_link() instead.
    """
    try:
        if item_type == "function":
            from inspect import getfullargspec

            function_obj = registry_object.function
            output_labels = registry_object.output_labels
            input_names = getfullargspec(function_obj)[0]
            output_names = output_labels if output_labels else ["output"]

            input_components = []
            for i, param_name in enumerate(input_names):
                if param_name in param_selections:
                    comp_index = param_selections[param_name]
                    if comp_index >= 0 and comp_index < len(data1.components):
                        comp = data1.components[comp_index]
                        input_components.append(comp)
                    else:
                        return
                else:
                    comp = data1.components[0]
                    input_components.append(comp)

            output_components = []
            for i, output_name in enumerate(output_names):
                if output_name in param_selections:
                    comp_index = param_selections[output_name]
                    if comp_index >= 0 and comp_index < len(data2.components):
                        comp = data2.components[comp_index]
                        output_components.append(comp)
                    else:
                        return
                else:
                    fallback_index = i if i < len(data2.components) else 0
                    comp = data2.components[fallback_index]
                    output_components.append(comp)

            if not output_components:
                output_components.append(data2.components[0])
            from glue.core.component_link import ComponentLink

            if len(output_components) == 1:
                link = ComponentLink(input_components, output_components[0], using=function_obj)
            else:
                link = ComponentLink(input_components, output_components[0], using=function_obj)
            data_collection.add_link(link)

        elif item_type == "helper":
            if getattr(registry_object.helper, "cid_independent", False):
                link_instance = registry_object.helper(data1=data1, data2=data2)
                data_collection.add_link(link_instance)
            else:
                helper_class = registry_object.helper
                input_names = getattr(helper_class, "labels1", [])
                output_names = getattr(helper_class, "labels2", [])
                input_components = []
                output_components = []

                for param_name in input_names:
                    if param_name in param_selections:
                        comp_index = param_selections[param_name]
                        comp = (
                            data1.components[comp_index]
                            if comp_index < len(data1.components)
                            else data1.components[0]
                        )
                    else:
                        comp = data1.components[0]
                    input_components.append(comp)

                for param_name in output_names:
                    if param_name in param_selections:
                        comp_index = param_selections[param_name]
                        comp = (
                            data2.components[comp_index]
                            if comp_index < len(data2.components)
                            else data2.components[0]
                        )
                    else:
                        comp = data2.components[0]
                    output_components.append(comp)

                link_instance = registry_object.helper(
                    cids1=input_components if input_components else [data1.components[0]],
                    cids2=output_components if output_components else [data2.components[0]],
                    data1=data1,
                    data2=data2,
                )
                data_collection.add_link(link_instance)
    except Exception:
        raise


def _create_identity_link_direct(
    app, data_collection, data1_index, data2_index, cid1_index, cid2_index
):
    """Legacy: Direct identity link creation."""
    data1 = data_collection[data1_index]
    data2 = data_collection[data2_index]
    comp1 = (
        data1.components[cid1_index]
        if cid1_index >= 0 and cid1_index < len(data1.components)
        else data1.components[0]
    )
    comp2 = (
        data2.components[cid2_index]
        if cid2_index >= 0 and cid2_index < len(data2.components)
        else data2.components[0]
    )
    app.add_link(data1, comp1, data2, comp2)


def _create_function_link(function_item, data1, data2, row1_index, row2_index, app):
    """Legacy: Create function link with automatic multi-parameter handling."""
    function_object = function_item["function_object"]
    function_callable = function_object.function
    import inspect

    sig = inspect.signature(function_callable)
    comp1 = (
        data1.components[row1_index]
        if row1_index >= 0 and row1_index < len(data1.components)
        else data1.components[0]
    )
    comp2 = (
        data2.components[row2_index]
        if row2_index >= 0 and row2_index < len(data2.components)
        else data2.components[0]
    )

    from glue.core.component_link import ComponentLink

    try:
        param_count = len(list(sig.parameters.keys()))
        if param_count == 1:
            link = ComponentLink([comp1], comp2, using=function_callable)
        else:
            input_components = []
            for i in range(min(param_count, len(data1.components))):
                input_components.append(data1.components[i])
            while len(input_components) < param_count:
                input_components.append(data1.components[-1])
            link = ComponentLink(input_components, comp2, using=function_callable)
        app.data_collection.add_link(link)
    except Exception:
        raise


def stringify_links(link):
    """Format link for display in UI.

    Handles all glue link types:
        LinkSame: "width <-> height"
        JoinLink: Uses __str__() method
        Coordinate helpers: "ICRS <-> Galactic"
        ComponentLink (single): "function(width -> volume)"
        ComponentLink (multi): "lengths_to_volume(w,h,d -> vol)"

    Args:
        link: Any glue link object

    Returns:
        str: Human-readable link description
    """
    try:
        if hasattr(link, "_cid1") and hasattr(link, "_cid2"):
            cid1_label = getattr(link._cid1, "label", str(link._cid1))
            cid2_label = getattr(link._cid2, "label", str(link._cid2))
            return f"{cid1_label} <-> {cid2_label}"

        elif isinstance(link, JoinLink):
            return str(link)

        elif isinstance(link, BaseMultiLink):
            # All coordinate helpers have .display or .description attributes
            if hasattr(link, "description"):
                return link.description
            elif hasattr(link, "display") and link.display:
                return link.display
            else:
                # Fallback (should rarely be reached)
                return f"Coordinate Transform ({type(link).__name__})"

        elif hasattr(link, "_from") and hasattr(link, "_to"):
            if isinstance(link._from, list) and len(link._from) > 0:
                from_labels = [getattr(c, "label", str(c)) for c in link._from]
                to_label = getattr(link._to, "label", str(link._to))
                function_name = "function"
                if hasattr(link, "_using") and link._using:
                    function_name = getattr(link._using, "__name__", "function")

                if function_name == "identity" and len(from_labels) == 1:
                    display = f"{from_labels[0]} <-> {to_label}"

                elif len(from_labels) == 1 and hasattr(link, "inverse") and link.inverse:
                    display = f"{function_name}({from_labels[0]} <-> {to_label})"
                elif len(from_labels) == 1:
                    display = f"{function_name}({from_labels[0]} -> {to_label})"
                else:
                    from_str = ",".join(from_labels)
                    display = f"{function_name}({from_str} -> {to_label})"

                return display
            else:
                from_label = getattr(link._from, "label", str(link._from))
                to_label = getattr(link._to, "label", str(link._to))
                return f"{from_label} -> {to_label}"

        else:
            link_type = type(link).__name__
            if hasattr(link, "description") and link.description:
                return link.description
            elif hasattr(link, "display") and link.display:
                return link.display
            elif hasattr(link, "__str__"):
                str_rep = str(link)
                if len(str_rep) < 100 and "object at 0x" not in str_rep:
                    return str_rep
            return f"Advanced Link ({link_type})"

    except Exception:
        return "Link (display error)"


@solara.component
def Linker(app: JupyterApplication, show_list: bool = True):
    """Main link editor component orchestrating UI panels.

    Layout: [Dataset1] ⇄ [Dataset2] [Links List] [Link Details]

    Args:
        app: JupyterApplication instance
        show_list: Whether to display existing links list

    Glue-core connections:
        - app.data_collection.external_links (link storage)
        - use_glue_watch() monitors ExternallyDerivableComponentsChangedMessage

    Qt Reference: glue_qt/dialogs/link_editor/link_editor.py (LinkEditor class)
    """

    selected_data1 = solara.use_reactive(0)
    selected_row1 = solara.use_reactive(0)
    selected_data2 = solara.use_reactive(1)
    selected_row2 = solara.use_reactive(0)
    selected_link_index = solara.use_reactive(-1)
    shared_refresh_counter = solara.use_reactive(0)

    data_collection = app.data_collection

    # Monitor glue message bus for link changes
    use_glue_watch(app.session.hub, msg.ExternallyDerivableComponentsChangedMessage)

    if data_collection is None or len(data_collection) == 0:
        return solara.Text("No data loaded")

    def _add_link():
        """Create identity link and auto-select it."""
        app.add_link(
            data_collection[selected_data1.value],
            data_collection[selected_data1.value].components[selected_row1.value],
            data_collection[selected_data2.value],
            data_collection[selected_data2.value].components[selected_row2.value],
        )
        shared_refresh_counter.set(shared_refresh_counter.value + 1)
        new_position = len(data_collection.external_links) - 1
        selected_link_index.set(-1)
        selected_link_index.set(new_position)

    data_dict = [
        {"label": data.label, "value": index} for index, data in enumerate(data_collection or [])
    ]

    with solara.Column():
        with solara.Row(
            style={
                "align-items": "start",
                "gap": "15px",
                "width": "100%",
                "min-width": "1000px",
                "flex-wrap": "nowrap",
            }
        ):
            if len(data_collection) > 1:
                with solara.Column(
                    style={"min-width": "150px", "max-width": "180px", "flex": "0 0 150px"}
                ):
                    LinkSelector(
                        data_collection, data_dict, selected_data1, selected_row1, "Dataset 1"
                    )

                with solara.Column(
                    style={"align-items": "center", "flex": "0 0 30px", "min-width": "30px"}
                ):
                    solara.Text("⇄", style={"font-size": "24px", "margin-top": "40px"})

                with solara.Column(
                    style={"min-width": "150px", "max-width": "180px", "flex": "0 0 150px"}
                ):
                    LinkSelector(
                        data_collection, data_dict, selected_data2, selected_row2, "Dataset 2"
                    )

                with solara.Column(
                    style={"min-width": "380px", "max-width": "340px", "flex": "0 0 260px"}
                ):
                    solara.Markdown("**Links between Dataset 1 and Dataset 2**")
                    if show_list:
                        CurrentLinksSelector(
                            data_collection=data_collection,
                            selected_link_index=selected_link_index,
                            shared_refresh_counter=shared_refresh_counter,
                        )

                with solara.Column(
                    style={"flex": "1 1 auto", "min-width": "200px", "max-width": "250px"}
                ):
                    LinkDetailsPanel(
                        app=app,
                        data_collection=data_collection,
                        selected_data1=selected_data1,
                        selected_data2=selected_data2,
                        selected_link_index=selected_link_index,
                        shared_refresh_counter=shared_refresh_counter,
                    )

        with solara.Row():
            solara.Button(
                label="Glue Attributes",
                color="primary",
                on_click=_add_link,
            )

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
    """Dataset and attribute selector panel.

    UI: Dataset dropdown + scrollable attribute list

    Args:
        data_collection: Glue DataCollection
        data_dict: List of {label, value} for dataset dropdown
        selected_data: Reactive dataset index
        selected_row: Reactive attribute index within dataset
        title: Panel header text
    """
    with solara.Column():
        solara.Markdown(f"**{title}**")

        solara.v.Select(
            label=title,
            v_model=selected_data.value,
            on_v_model=selected_data.set,
            items=data_dict,
            item_text="label",
            item_value="value",
        )

        solara.Text(f"Attributes for {data_dict[selected_data.value]['label']}")

        with solara.v.List(dense=True, style_="max-height: 50vh; overflow-y: scroll;"):
            with solara.v.ListItemGroup(
                v_model=selected_row.value,
                on_v_model=selected_row.set,
                color="primary",
            ):
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
    """Clickable list of existing links.

    Bridges link display and editing: user clicks link → details panel updates.

    Args:
        data_collection: Glue DataCollection
        selected_link_index: Reactive index of selected link (-1 = none)
        shared_refresh_counter: Forces re-render when links change

    Note: use_memo with shared_refresh_counter ensures UI updates after edits.
    """

    links_list = solara.use_memo(
        lambda: list(data_collection.external_links), [shared_refresh_counter.value]
    )

    if len(links_list) == 0:
        return solara.Text("No links created yet", style={"color": "#666", "font-style": "italic"})

    with solara.v.List(dense=True):
        with solara.v.ListItemGroup(
            v_model=selected_link_index.value,
            on_v_model=selected_link_index.set,
            color="primary",
        ):
            for idx, link in enumerate(links_list):
                with solara.v.ListItem(value=idx):
                    with solara.v.ListItemContent():
                        solara.v.ListItemTitle(children=[stringify_links(link)])


@solara.component
def LinkDetailsPanel(
    app: JupyterApplication,
    data_collection: DataCollection,
    selected_data1: solara.Reactive[int],
    selected_data2: solara.Reactive[int],
    selected_link_index: solara.Reactive[int],
    shared_refresh_counter: solara.Reactive[int],
):
    """Link details and editing panel (right side of UI).

    Core editing pattern: Remove old link → Recreate with new parameters
    Uses Qt's LinkEditorState for atomic operations.

    Key functions:
        _remove_link(): Delete selected link
        _update_dataset1/2_attribute(): Edit link by recreating
        _update_coordinate_parameter(): Edit 2-to-2 coordinate transforms

    Args:
        app: JupyterApplication
        data_collection: Glue DataCollection
        selected_data1/2: Dataset indices (unused, for future features)
        selected_link_index: Which link is selected (-1 = none)
        shared_refresh_counter: UI refresh trigger

    Glue-core connections:
        - glue.dialogs.link_editor.state.LinkEditorState (Qt's state manager)
        - glue.config.link_function/link_helper.members (registry lookup)
        - data_collection.set_links() (atomic update method)

    Qt Reference: glue_qt/dialogs/link_editor/link_editor.py (link details panel)
    """

    links_list = solara.use_memo(
        lambda: list(data_collection.external_links), [shared_refresh_counter.value]
    )

    # Hash includes object IDs to detect when links are recreated
    link_contents_hash = solara.use_memo(
        lambda: hash(
            tuple(
                f"{id(link)}_{str(link._cid1)}_{str(link._cid2)}_{link.data1.label}_{link.data2.label}"
                for link in links_list
                if hasattr(link, "_cid1")
            )
        ),
        [],
    )

    selected_link_info = solara.use_memo(
        lambda: _get_selected_link_info(links_list, selected_link_index.value),
        [
            selected_link_index.value,
            len(links_list),
            link_contents_hash,
            shared_refresh_counter.value,
        ],
    )

    if len(data_collection) == 0:
        return solara.Text("No data available")

    def _remove_link():
        """Remove selected link using Qt's atomic pattern.

        Uses LinkEditorState to maintain glue-core metadata consistency.
        """
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info

            try:
                links_in_collection = list(data_collection.external_links)
                target_index = None

                # Primary: object identity
                for idx, existing in enumerate(links_in_collection):
                    if existing is link:
                        target_index = idx
                        break

                # Fallback: equality
                if target_index is None:
                    for idx, existing in enumerate(links_in_collection):
                        if existing == link:
                            target_index = idx
                            break

                if target_index is None:
                    return

                temp_state = LinkEditorState(data_collection)

                if target_index >= len(temp_state.links):
                    return

                # Remove the link from temp_state's list
                temp_state.links.pop(target_index)

                temp_state.update_links_in_collection()

            except Exception:
                return

            shared_refresh_counter.set(shared_refresh_counter.value + 1)
            selected_link_index.set(-1)

    def _update_coordinate_parameter(dataset, param_index, new_attr_index):
        """Edit individual coordinate in 2-to-2 transforms (e.g., ra/dec <-> l/b).

        Args:
            dataset: Which side to update (1 or 2)
            param_index: Which coordinate (0 or 1)
            new_attr_index: New component index
        """
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info

            if not link_data.get("is_coordinate_pair", False):
                return

            coord1_param_info = link_data.get("coord1_param_info", [])
            coord2_param_info = link_data.get("coord2_param_info", [])

            if dataset == 1 and param_index >= len(coord1_param_info):
                return
            elif dataset == 2 and param_index >= len(coord2_param_info):
                return

            if (
                isinstance(link, BaseMultiLink)
                and hasattr(link, "data1")
                and hasattr(link, "data2")
            ):
                from_data = link.data1
                to_data = link.data2

                if dataset == 1:
                    if new_attr_index < len(from_data.components):
                        new_component = from_data.components[new_attr_index]
                        new_cids1 = list(link.cids1)
                        new_cids1[param_index] = new_component
                        new_cids2 = list(link.cids2)

                        coord_type = type(link)
                        new_coord_helper = coord_type(new_cids1, new_cids2, from_data, to_data)
                        other_links = [
                            item for item in data_collection.external_links if item is not link
                        ]
                        all_new_links = other_links + [new_coord_helper]
                        data_collection.set_links(all_new_links)

                        new_position = len(data_collection.external_links) - 1
                        shared_refresh_counter.set(shared_refresh_counter.value + 1)
                        selected_link_index.set(-1)
                        selected_link_index.set(new_position)

                elif dataset == 2:
                    if new_attr_index < len(to_data.components):
                        new_component = to_data.components[new_attr_index]
                        new_cids1 = list(link.cids1)
                        new_cids2 = list(link.cids2)
                        new_cids2[param_index] = new_component

                        coord_type = type(link)
                        new_coord_helper = coord_type(new_cids1, new_cids2, from_data, to_data)
                        other_links = [
                            item for item in data_collection.external_links if item is not link
                        ]
                        all_new_links = other_links + [new_coord_helper]
                        data_collection.set_links(all_new_links)

                        new_position = len(data_collection.external_links) - 1
                        shared_refresh_counter.set(shared_refresh_counter.value + 1)
                        selected_link_index.set(-1)
                        selected_link_index.set(new_position)

    def _update_multi_parameter(param_index, new_attr_index):
        """Edit individual parameter in N→1 functions (e.g., lengths_to_volume).

        Args:
            param_index: Which parameter (0=width, 1=height, 2=depth)
            new_attr_index: New component index
        """
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info

            if not link_data.get("is_multi_param", False):
                return

            multi_param_info = link_data.get("multi_param_info", [])
            if param_index >= len(multi_param_info):
                return

            if hasattr(link, "_from") and hasattr(link, "_to"):
                from_data = link._from[0].parent
                old_to_component = link._to

                if new_attr_index < len(from_data.components):
                    new_from_component = from_data.components[new_attr_index]

                    new_from_components = []
                    for i, param in enumerate(multi_param_info):
                        if i == param_index:
                            new_from_components.append(new_from_component)
                        else:
                            new_from_components.append(param["component"])

                    function = None
                    if hasattr(link, "_using"):
                        function = link._using

                    from glue.core.component_link import ComponentLink

                    new_link = ComponentLink(new_from_components, old_to_component, using=function)

                    other_links = [
                        item for item in data_collection.external_links if item is not link
                    ]
                    all_new_links = other_links + [new_link]
                    data_collection.set_links(all_new_links)

                    new_position = len(data_collection.external_links) - 1
                    shared_refresh_counter.set(shared_refresh_counter.value + 1)
                    selected_link_index.set(-1)
                    selected_link_index.set(new_position)

    def _update_dataset1_attribute(new_attr_index):
        """Edit Dataset 1 attribute using Qt's remove-and-recreate pattern.

        Core algorithm:
          1. Extract datasets from link (handles LinkSame, ComponentLink, JoinLink, coord helpers)
          2. Remove old link from LinkEditorState
          3. Find original registry object (link_function or link_helper)
          4. Recreate link via temp_state.new_link(registry_object)
          5. Update component selections to user's choice
          6. Apply via temp_state.update_links_in_collection()

        Special handling:
          - JoinLink: Remove from data_collection first (JoinLink.__eq__ issues)
          - Registry lookup: Checks link_function, link_helper by type/name
          - Fallback: Uses identity function if original not found

        Args:
            new_attr_index: New Dataset 1 component index
        """
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info

            # Extract datasets from link
            if hasattr(link, "data1") and hasattr(link, "data2"):
                from_data = link.data1
                to_data = link.data2
            elif hasattr(link, "_from") and hasattr(link, "_to"):
                if isinstance(link._from, list) and len(link._from) > 0:
                    from_data = link._from[0].parent
                else:
                    from_data = link._from.parent
                to_data = link._to.parent
            else:
                return

            if new_attr_index < len(from_data.components):
                new_component = from_data.components[new_attr_index]

                # Extract Dataset 2 component (unchanged)
                if hasattr(link, "_cid2"):
                    old_component2 = link._cid2
                elif hasattr(link, "_to"):
                    old_component2 = link._to
                elif isinstance(link, BaseMultiLink) and hasattr(link, "cids2"):
                    if link.cids2:
                        old_component2 = link.cids2[0]
                    else:
                        return
                elif isinstance(link, JoinLink) and hasattr(link, "cids2"):
                    if link.cids2:
                        old_component2 = link.cids2[0]
                    else:
                        return
                else:
                    return

                original_link_type = type(link).__name__

                # JoinLink special case: remove first due to __eq__ treating similar links as identical
                if isinstance(link, JoinLink):
                    try:
                        data_collection.remove_link(link)
                    except Exception:
                        pass

                try:
                    temp_state = LinkEditorState(data_collection)
                    temp_state.data1 = from_data
                    temp_state.data2 = to_data

                    # Remove old link by index (object identity)
                    original_index = None
                    for i, item in enumerate(data_collection.external_links):
                        if item is link:
                            original_index = i
                            break

                    if original_index is not None and original_index < len(temp_state.links):
                        temp_state.links.pop(original_index)

                    # Registry lookup: find original function/helper
                    registry_object = None

                    if hasattr(link, "_using") and link._using:
                        from glue.config import link_function

                        function_name = getattr(link._using, "__name__", "unknown")
                        for func in link_function.members:
                            if (
                                hasattr(func, "function")
                                and func.function.__name__ == function_name
                            ):
                                registry_object = func
                                break

                    elif (
                        "coordinate_helpers" in original_link_type.lower()
                        or "galactic" in original_link_type.lower()
                        or "icrs" in original_link_type.lower()
                    ):
                        from glue.config import link_helper

                        for helper in link_helper.members:
                            if helper.helper.__name__ == original_link_type:
                                registry_object = helper
                                break

                    elif "join" in original_link_type.lower():
                        from glue.config import link_helper

                        for helper in link_helper.members:
                            if "join" in helper.helper.__name__.lower():
                                registry_object = helper
                                break

                    elif "linksame" in original_link_type.lower():
                        from glue.config import link_helper

                        for helper in link_helper.members:
                            if helper.helper.__name__ == "LinkSame":
                                registry_object = helper
                                break

                    # Recreate link with updated components
                    if registry_object:
                        temp_state.new_link(registry_object)

                        if hasattr(temp_state, "data1_att") and hasattr(temp_state, "data2_att"):
                            temp_state.data1_att = new_component
                            temp_state.data2_att = old_component2

                        elif hasattr(temp_state, "current_link") and temp_state.current_link:
                            current_link = temp_state.current_link

                            if hasattr(current_link, "x") and hasattr(current_link, "y"):
                                current_link.x = new_component
                                current_link.y = old_component2

                            elif (
                                isinstance(link, JoinLink)
                                and hasattr(current_link, "data1")
                                and hasattr(current_link, "names1")
                            ):
                                input_param_name = (
                                    current_link.names1[0] if current_link.names1 else None
                                )
                                if input_param_name and hasattr(current_link, input_param_name):
                                    setattr(current_link, input_param_name, new_component)
                                if hasattr(link, "cids2") and link.cids2:
                                    output_param_name = (
                                        current_link.names2[0] if current_link.names2 else None
                                    )
                                    if output_param_name and hasattr(
                                        current_link, output_param_name
                                    ):
                                        setattr(current_link, output_param_name, link.cids2[0])

                            elif hasattr(current_link, "data1") and hasattr(current_link, "names1"):
                                names1 = current_link.names1
                                if names1 and len(names1) > 0:
                                    first_param_name = names1[0]
                                    if hasattr(current_link, first_param_name):
                                        setattr(current_link, first_param_name, new_component)

                            elif hasattr(current_link, "names1") and hasattr(
                                current_link, "names2"
                            ):
                                if current_link.names1 and len(current_link.names1) > 0:
                                    first_param_name = current_link.names1[0]
                                    if hasattr(current_link, first_param_name):
                                        setattr(current_link, first_param_name, new_component)
                                if (
                                    hasattr(link, "_to")
                                    and current_link.names2
                                    and len(current_link.names2) > 0
                                ):
                                    output_param_name = current_link.names2[0]
                                    if hasattr(current_link, output_param_name):
                                        setattr(current_link, output_param_name, link._to)

                        temp_state.update_links_in_collection()

                    else:
                        # Fallback: use identity function if registry object not found
                        from glue.config import link_function

                        identity_func = None
                        for func in link_function.members:
                            if hasattr(func, "function") and func.function.__name__ == "identity":
                                identity_func = func
                                break

                        if identity_func:
                            temp_state.new_link(identity_func)
                            if hasattr(temp_state, "current_link") and temp_state.current_link:
                                current_link = temp_state.current_link
                                if hasattr(current_link, "x") and hasattr(current_link, "y"):
                                    current_link.x = new_component
                                    current_link.y = old_component2
                            temp_state.update_links_in_collection()
                        else:
                            app.add_link(from_data, new_component, to_data, old_component2)

                except Exception:
                    app.add_link(from_data, new_component, to_data, old_component2)

                # Small delay to let glue update internal state
                shared_refresh_counter.set(shared_refresh_counter.value + 1)
                new_position = len(data_collection.external_links) - 1
                selected_link_index.set(-1)
                selected_link_index.set(new_position)

    def _update_dataset2_attribute(new_attr_index):
        """Edit Dataset 2 (output) attribute using Qt's remove-and-recreate pattern.

        This is the mirror function of _update_dataset1_attribute for editing the
        target/output side of links. It handles all link types (LinkSame, ComponentLink,
        JoinLink, coordinate helpers) by recreating the link with updated Dataset 2 component.

        Algorithm (6 steps):
          1. Extract datasets from link (handles all link type variations)
          2. Extract Dataset 1 component (kept unchanged during Dataset 2 edit)
          3. Create LinkEditorState and remove old link by object identity
          4. Find original registry object (link_function or link_helper)
          5. Recreate link via temp_state.new_link() and update Dataset 2 component
          6. Apply atomically via temp_state.update_links_in_collection()

        Special cases:
          - JoinLink: Pre-remove from data_collection due to __eq__ treating similar links as identical
          - Coordinate helpers: Detect by class name AND function name patterns
          - Multi-parameter functions: Restore all N input components, only update 1 output
          - Registry lookup failure: Falls back to identity function then app.add_link()

        Args:
            new_attr_index: Index of new Dataset 2 component in to_data.components

        Parent function: LinkDetailsPanel (line 750)
        Called by: solara.v.Select on_v_model callback (line 1555)
        Calls: LinkEditorState, temp_state.new_link(), temp_state.update_links_in_collection()

        Glue-core connections:
            - glue.dialogs.link_editor.state.LinkEditorState (Qt's atomic state manager)
            - glue.config.link_function.members (transformation function registry)
            - glue.config.link_helper.members (LinkCollection registry)
            - temp_state.new_link() (creates EditableLinkFunctionState from registry object)
            - temp_state.update_links_in_collection() (atomic commit to data_collection)

        Performance note:
            ⚠️ Accesses link_function.members and link_helper.members during edit (10+ times)
            This triggers lazy plugin loading - should use cached registry data instead
        """
        if selected_link_info is not None and selected_link_index.value >= 0:
            link, link_data = selected_link_info

            # Step 1: Extract datasets - handle both LinkCollection and ComponentLink patterns
            if hasattr(link, "data1") and hasattr(link, "data2"):
                # LinkCollection types: LinkSame, JoinLink, coordinate helpers
                from_data = link.data1
                to_data = link.data2
            elif hasattr(link, "_from") and hasattr(link, "_to"):
                # ComponentLink types: identity, function, coordinate transforms
                if isinstance(link._from, list):
                    from_data = link._from[0].parent  # Multi-input: get parent from first
                else:
                    from_data = link._from.parent  # Single input
                to_data = link._to.parent
            else:
                return  # Unknown link structure

            if new_attr_index < len(to_data.components):
                # Step 2: Extract Dataset 1 component (remains unchanged during Dataset 2 edit)
                # Handle all link type variations with priority order
                if hasattr(link, "_cid1"):
                    # LinkSame: Has _cid1 and _cid2 attributes
                    old_component1 = link._cid1
                elif hasattr(link, "_from"):
                    # ComponentLink: _from can be single ComponentID or list
                    if isinstance(link._from, list):
                        old_component1 = link._from[
                            0
                        ]  # Use first input for multi-parameter functions
                    else:
                        old_component1 = link._from
                elif isinstance(link, BaseMultiLink) and hasattr(link, "cids1"):
                    # Coordinate helpers: cids1 is always a list (2-to-2 or 3-to-3 transforms)
                    if link.cids1:
                        old_component1 = link.cids1[0]
                    else:
                        return  # Invalid coordinate helper without cids1
                elif isinstance(link, JoinLink) and hasattr(link, "cids1"):
                    # JoinLink: cids1 is a list with single element (key column)
                    if link.cids1:
                        old_component1 = link.cids1[0]
                    else:
                        return  # Invalid JoinLink without cids1
                else:
                    return  # Unknown link type - cannot extract component

                new_component = to_data.components[new_attr_index]
                original_link_type = type(link).__name__

                # JoinLink special handling: Remove before recreating
                # JoinLink.__eq__ treats similar links as identical, causing issues with temp_state
                if isinstance(link, JoinLink):
                    try:
                        data_collection.remove_link(link)
                    except Exception:
                        pass  # Link may already be removed

                try:
                    # Step 3: Create temporary state and remove old link
                    temp_state = LinkEditorState(data_collection)
                    temp_state.data1 = from_data
                    temp_state.data2 = to_data

                    # Remove old link by index using object identity (not equality)
                    # This prevents removing multiple identical links
                    original_index = None
                    for i, item in enumerate(data_collection.external_links):
                        if item is link:  # Object identity check
                            original_index = i
                            break

                    if original_index is not None and original_index < len(temp_state.links):
                        temp_state.links.pop(original_index)

                    # Step 4: Find original registry object by link type
                    registry_object = None

                    # Extract function name for registry lookup
                    function_name = "unknown"
                    if hasattr(link, "_using") and link._using:
                        function_name = getattr(link._using, "__name__", "unknown")

                    # Detect coordinate helpers by both class name and function name patterns
                    is_coordinate_helper = (
                        "coordinate_helpers" in original_link_type.lower()
                        or "galactic" in original_link_type.lower()
                        or "icrs" in original_link_type.lower()
                        or "fk4" in original_link_type.lower()
                        or "fk5" in original_link_type.lower()
                        or "icrs_to" in function_name.lower()
                        or "galactic_to" in function_name.lower()
                        or "fk4_to" in function_name.lower()
                        or "fk5_to" in function_name.lower()
                        or "_to_fk" in function_name.lower()
                        or "_to_icrs" in function_name.lower()
                        or "_to_galactic" in function_name.lower()
                    )

                    if is_coordinate_helper:
                        # Coordinate helper lookup in link_helper registry
                        from glue.config import link_helper

                        # Extract class name from function name (e.g., "ICRS_to_FK5.backwards_2" -> "ICRS_to_FK5")
                        helper_class_name = (
                            function_name.split(".")[0]
                            if "." in function_name
                            else original_link_type
                        )

                        for helper in link_helper.members:
                            helper_name = helper.helper.__name__
                            if helper_name == helper_class_name:
                                registry_object = helper
                                break

                    elif hasattr(link, "_using") and link._using:
                        # ComponentLink with transformation function
                        from glue.config import link_function

                        for func in link_function.members:
                            if (
                                hasattr(func, "function")
                                and func.function.__name__ == function_name
                            ):
                                registry_object = func
                                break

                    elif "join" in original_link_type.lower():
                        # JoinLink lookup
                        from glue.config import link_helper

                        for helper in link_helper.members:
                            if "join" in helper.helper.__name__.lower():
                                registry_object = helper
                                break

                    elif "linksame" in original_link_type.lower():
                        # LinkSame (identity bidirectional link)
                        from glue.config import link_helper

                        for helper in link_helper.members:
                            if helper.helper.__name__ == "LinkSame":
                                registry_object = helper
                                break

                    # Step 5: Recreate link and update Dataset 2 component
                    if registry_object:
                        temp_state.new_link(registry_object)

                        # Update component selections based on EditableLinkFunctionState structure
                        if hasattr(temp_state, "data1_att") and hasattr(temp_state, "data2_att"):
                            # Simple links (LinkSame): Direct attribute setters
                            temp_state.data1_att = old_component1  # Keep Dataset 1 unchanged
                            temp_state.data2_att = new_component  # Update Dataset 2 (user's change)

                        elif hasattr(temp_state, "current_link") and temp_state.current_link:
                            # Complex links: Update via current_link state object
                            current_link = temp_state.current_link

                            if hasattr(current_link, "x") and hasattr(current_link, "y"):
                                # Identity function pattern (x/y parameters)
                                current_link.x = old_component1  # Input (unchanged)
                                current_link.y = new_component  # Output (user's change)

                            elif (
                                isinstance(link, JoinLink)
                                and hasattr(current_link, "data2")
                                and hasattr(current_link, "names2")
                            ):
                                # JoinLink: Single input/output in cids1/cids2 lists
                                # Restore input (Dataset 1), update output (Dataset 2)
                                if hasattr(link, "cids1") and link.cids1:
                                    input_param_name = (
                                        current_link.names1[0] if current_link.names1 else None
                                    )
                                    if input_param_name and hasattr(current_link, input_param_name):
                                        setattr(current_link, input_param_name, link.cids1[0])

                                output_param_name = (
                                    current_link.names2[0] if current_link.names2 else None
                                )
                                if output_param_name and hasattr(current_link, output_param_name):
                                    setattr(current_link, output_param_name, new_component)

                            elif hasattr(current_link, "data2") and hasattr(current_link, "names2"):
                                # Multi-parameter functions: Restore ALL inputs, update ONE output
                                if hasattr(current_link, "names1") and current_link.names1:
                                    original_inputs = (
                                        link._from
                                    )  # List of original input components
                                    names1 = current_link.names1

                                    for i, param_name in enumerate(names1):
                                        if i < len(original_inputs) and hasattr(
                                            current_link, param_name
                                        ):
                                            original_component = original_inputs[i]
                                            setattr(current_link, param_name, original_component)

                                # Update output parameter (Dataset 2 edit)
                                names2 = current_link.names2
                                if names2 and len(names2) > 0:
                                    first_output_name = names2[0]
                                    if hasattr(current_link, first_output_name):
                                        setattr(current_link, first_output_name, new_component)

                            elif hasattr(current_link, "names1") and hasattr(
                                current_link, "names2"
                            ):
                                # link_function with multiple parameters (e.g., lengths_to_volume)
                                if isinstance(link._from, list) and len(link._from) > 0:
                                    for i, param_name in enumerate(current_link.names1):
                                        if i < len(link._from) and hasattr(
                                            current_link, param_name
                                        ):
                                            original_component = link._from[i]
                                            setattr(current_link, param_name, original_component)

                                if current_link.names2 and len(current_link.names2) > 0:
                                    output_param_name = current_link.names2[0]
                                    if hasattr(current_link, output_param_name):
                                        setattr(current_link, output_param_name, new_component)

                        # Step 6: Apply changes atomically
                        temp_state.update_links_in_collection()

                    else:
                        # Fallback: Registry lookup failed - use identity function
                        from glue.config import link_function

                        identity_func = None
                        for func in link_function.members:
                            if hasattr(func, "function") and func.function.__name__ == "identity":
                                identity_func = func
                                break

                        if identity_func:
                            temp_state.new_link(identity_func)
                            if hasattr(temp_state, "current_link") and temp_state.current_link:
                                current_link = temp_state.current_link

                                if hasattr(current_link, "x") and hasattr(current_link, "y"):
                                    current_link.x = old_component1
                                    current_link.y = new_component
                            temp_state.update_links_in_collection()

                        else:
                            # Final fallback: Use legacy add_link method
                            app.add_link(from_data, old_component1, to_data, new_component)

                except Exception:
                    # Exception handler fallback
                    app.add_link(from_data, old_component1, to_data, new_component)

                # Small delay to allow glue-core to update internal derivation cache

                # Force UI refresh by incrementing shared counter (invalidates memoization)
                shared_refresh_counter.set(shared_refresh_counter.value + 1)

                # Select the newly created link (always at the end of list)
                new_position = len(data_collection.external_links) - 1
                selected_link_index.set(-1)  # Clear selection
                selected_link_index.set(new_position)  # Select new link

    # UI Layout: Link Details Panel (right column)
    # Responsive flex layout with overflow protection for modal display
    with solara.Column(
        style={
            "padding": "10px",
            "width": "100%",
            "max-width": "250px",  # Constrain width to prevent modal overflow
            "flex": "1 1 auto",  # Flexible sizing
            "overflow": "hidden",  # Clip overflowing content
        }
    ):
        # Panel header
        solara.Markdown("**Link details**")

        # Content: Show instructions or editing interface based on selection state
        if selected_link_info is None:
            # No link selected: Show helpful message
            solara.Text(
                "Click on a link to see details", style={"font-style": "italic", "color": "#666"}
            )
        else:
            # Link selected: Show full editing interface (Qt-style link details panel)
            link, link_data = selected_link_info

            # Descriptive text: Special message for multi-parameter links
            if (
                isinstance(link, type(link))
                and hasattr(link, "_from")
                and len(getattr(link, "_from", [])) > 1
            ):
                solara.Text(
                    f"Multi-parameter link ({len(link._from)} inputs → 1 output)",
                    style={"font-style": "italic", "margin-bottom": "10px", "color": "#0066cc"},
                )
                solara.Text(
                    "Note: Only first input shown in editing panel",
                    style={"font-size": "12px", "color": "#666", "margin-bottom": "10px"},
                )
            else:
                solara.Text(
                    "Details about the link",
                    style={"font-style": "italic", "margin-bottom": "10px"},
                )

            # Dataset 1 attributes section: Multi-parameter or single-parameter display
            if link_data.get("is_multi_param", False):
                if link_data.get("is_coordinate_pair", False):
                    # Coordinate pair transformation (2-to-2, 3-to-3, etc.)
                    coord_type = link_data.get("coordinate_type", "Coordinate")
                    solara.Markdown(f"**{coord_type} coordinate transformation**")
                    solara.Text(
                        "Transform coordinate pairs between reference frames",
                        style={"color": "#666", "font-style": "italic", "margin-bottom": "10px"},
                    )

                    # Display Dataset 1 coordinate parameters (e.g., ra, dec)
                    coord1_param_info = link_data.get("coord1_param_info", [])

                    for i, param in enumerate(coord1_param_info):
                        with solara.Column(style={"margin-bottom": "8px"}):
                            solara.v.Select(
                                label=f"{param['name']}",
                                v_model=param["selected"],
                                on_v_model=lambda new_value,
                                param_idx=i,
                                dataset=1: _update_coordinate_parameter(
                                    dataset, param_idx, new_value
                                ),
                                items=link_data["attr1_options"],
                                item_text="label",
                                item_value="value",
                                style_="margin-bottom: 5px; width: 100%;",
                                dense=True,
                                outlined=True,
                                hint=f"Current: {param['label']}",
                            )

                else:
                    # Multi-parameter function (e.g., lengths_to_volume with width, height, depth)
                    # Implements Qt's N_COMBO_MAX pattern with dynamic parameter dropdowns
                    solara.Markdown(f"**{link_data['function_name']} function parameters**")
                    solara.Text(
                        f"Convert between {link_data['function_name']} parameters",
                        style={"color": "#666", "font-style": "italic", "margin-bottom": "10px"},
                    )

                    multi_param_info = link_data.get("multi_param_info", [])

                    for i, param in enumerate(multi_param_info):
                        with solara.Column(style={"margin-bottom": "8px"}):
                            solara.v.Select(
                                label=f"{param['name']}",
                                v_model=param["selected"],
                                on_v_model=lambda new_value, param_idx=i: _update_multi_parameter(
                                    param_idx, new_value
                                ),
                                items=link_data["attr1_options"],
                                item_text="label",
                                item_value="value",
                                style_="margin-bottom: 5px; width: 100%;",
                                dense=True,
                                outlined=True,
                                hint=f"Current: {param['label']}",
                            )

            else:
                # Single-parameter link: Simple dropdown for Dataset 1 attribute
                solara.Markdown("**Dataset 1 attributes**")
                if link_data["attr1_options"]:
                    solara.v.Select(
                        label=link_data["attr1_label"],
                        v_model=link_data["attr1_selected"],
                        on_v_model=_update_dataset1_attribute,
                        items=link_data["attr1_options"],
                        item_text="label",
                        item_value="value",
                        style_="margin-bottom: 10px; width: 100%;",
                        dense=True,
                        outlined=True,
                    )
                else:
                    solara.Text(
                        "No attributes available", style={"color": "#999", "font-style": "italic"}
                    )

            # Dataset 2 attributes section
            solara.Markdown("**Dataset 2 attributes**")

            if link_data["attr2_options"]:
                if link_data.get("is_coordinate_pair", False):
                    # Coordinate pair: Display Dataset 2 coordinate parameters (e.g., l, b)
                    coord2_param_info = link_data.get("coord2_param_info", [])

                    for i, param in enumerate(coord2_param_info):
                        with solara.Column(style={"margin-bottom": "8px"}):
                            solara.v.Select(
                                label=f"{param['name']}",
                                v_model=param["selected"],
                                on_v_model=lambda new_value,
                                param_idx=i,
                                dataset=2: _update_coordinate_parameter(
                                    dataset, param_idx, new_value
                                ),
                                items=link_data["attr2_options"],
                                item_text="label",
                                item_value="value",
                                style_="margin-bottom: 5px; width: 100%;",
                                dense=True,
                                outlined=True,
                                hint=f"Current: {param['label']}",
                            )

                else:
                    # Single output parameter: For normal links and function outputs
                    solara.v.Select(
                        label=link_data["attr2_label"],
                        v_model=link_data["attr2_selected"],
                        on_v_model=_update_dataset2_attribute,  # Callback to edit function
                        items=link_data["attr2_options"],
                        item_text="label",
                        item_value="value",
                        style_="margin-bottom: 10px; width: 100%;",
                        dense=True,
                        outlined=True,
                    )
            else:
                solara.Text(
                    "No attributes available", style={"color": "#999", "font-style": "italic"}
                )

            # Remove Link button: Matches Qt's link removal functionality
            with solara.Row(style={"margin-top": "20px", "justify-content": "flex-start"}):
                solara.Button(
                    label="Remove Link",
                    color="error",  # Red color indicates destructive action
                    on_click=_remove_link,
                    outlined=True,
                    style="margin-top: 10px;",
                )


def _get_selected_link_info(links_list, selected_index):
    """Extract comprehensive link information for UI display and editing.

    This function analyzes a selected link and returns structured data for the link details panel.
    It handles all glue link types (LinkSame, ComponentLink, JoinLink, coordinate helpers) and
    detects multi-parameter patterns (N→1 functions, 2-to-2 coordinate transforms).

    Algorithm:
      1. Validate selection index (boundary checks)
      2. Detect link type by attribute pattern matching (priority order matters!)
      3. Extract components and datasets based on link type structure
      4. For multi-parameter links: Build parameter info arrays with current selections
      5. Build dropdown options for both datasets
      6. Return (link_object, formatted_data_dict) tuple

    Link type priority order (detection sequence):
      1. LinkSame: Has _cid1 and _cid2 attributes
      2. Coordinate helpers: Class name contains 'coordinate_helpers'
      3. JoinLink: Has cids1, cids2, data1, data2 (but check AFTER coord helpers)
      4. ComponentLink: Has _from and _to (can be single or list)

    Multi-parameter patterns detected:
      - N→1 functions: link._from is list with len > 1 (e.g., lengths_to_volume)
      - 2-to-2 coordinate transforms: len(cids1) >= 2 and len(cids2) >= 2 (e.g., ICRS↔Galactic)
      - 3-to-3 transforms: Same pattern with 3 coordinates (e.g., Galactocentric)

    Args:
        links_list: List of link objects from data_collection.external_links
        selected_index: Index of selected link in the list (-1 = none selected)

    Returns:
        None: If selection invalid or link type unknown
        (link, data_dict): Tuple containing:
            - link: Original link object reference
            - data_dict: Dictionary with keys:
                - attr1_options: List[{label, value}] for Dataset 1 dropdowns
                - attr2_options: List[{label, value}] for Dataset 2 dropdowns
                - attr1_selected: Current selection index for Dataset 1
                - attr2_selected: Current selection index for Dataset 2
                - attr1_label: Display label for Dataset 1
                - attr2_label: Display label for Dataset 2
                - is_multi_param: Boolean flag for multi-parameter detection
                - is_coordinate_pair: Boolean flag for coordinate transforms (optional)
                - multi_param_info: List[param_data] for N→1 functions (optional)
                - coord1_param_info: List[param_data] for Dataset 1 coords (optional)
                - coord2_param_info: List[param_data] for Dataset 2 coords (optional)
                - function_name: Function name for display (optional)
                - coordinate_type: Coordinate system name (optional)

    Parent function: LinkDetailsPanel (line 750)
    Called by: solara.use_memo dependency (line 801)
    Used by: UI rendering logic (lines 1454-1587)

    Qt reference: glue_qt/dialogs/link_editor/state.py (EditableLinkFunctionState)
    Implements Qt's N_COMBO_MAX dynamic parameter pattern for Solara
    """
    # Step 1: Validate selection index
    if selected_index is None:
        return None
    if selected_index < 0:
        return None
    if selected_index >= len(links_list):
        return None

    link = links_list[selected_index]

    try:
        # Step 2: Link type detection (priority order matters!)

        # Type 1: LinkSame (most common from app.add_link())
        if hasattr(link, "_cid1") and hasattr(link, "_cid2"):
            from_comp = link._cid1
            to_comp = link._cid2
            from_data = link.data1
            to_data = link.data2
            is_multi_param = False

        # Type 2: Coordinate helpers (2-to-2 or 3-to-3 transforms)
        # Must check BEFORE JoinLink (both have cids1/cids2)
        elif isinstance(link, BaseMultiLink):
            if hasattr(link, "data1") and hasattr(link, "data2"):
                from_data = link.data1
                to_data = link.data2

                # Detect N-to-N coordinate transformation
                if (
                    hasattr(link, "cids1")
                    and hasattr(link, "cids2")
                    and hasattr(link, "labels1")
                    and hasattr(link, "labels2")
                    and link.cids1
                    and link.cids2
                    and link.labels1
                    and link.labels2
                ):
                    if len(link.cids1) >= 2 and len(link.cids2) >= 2:
                        # Multi-parameter coordinate pair detected
                        coord_type = type(link).__name__

                        # Build Dataset 1 coordinate parameter info
                        param1_info = []
                        for i, comp in enumerate(link.cids1):
                            param_name = (
                                link.labels1[i] if i < len(link.labels1) else f"coord1_{i+1}"
                            )
                            param_selected = next(
                                (
                                    idx
                                    for idx, attr in enumerate(from_data.components)
                                    if attr == comp
                                ),
                                0,
                            )

                            param_data = {
                                "name": param_name,
                                "selected": param_selected,
                                "component": comp,
                                "label": getattr(comp, "label", str(comp)),
                            }
                            param1_info.append(param_data)

                        # Build Dataset 2 coordinate parameter info
                        param2_info = []
                        for i, comp in enumerate(link.cids2):
                            param_name = (
                                link.labels2[i] if i < len(link.labels2) else f"coord2_{i+1}"
                            )
                            param_selected = next(
                                (
                                    idx
                                    for idx, attr in enumerate(to_data.components)
                                    if attr == comp
                                ),
                                0,
                            )

                            param_data = {
                                "name": param_name,
                                "selected": param_selected,
                                "component": comp,
                                "label": getattr(comp, "label", str(comp)),
                            }
                            param2_info.append(param_data)

                        # Build dropdown options
                        attr1_options = [
                            {"label": getattr(attr, "label", str(attr)), "value": idx}
                            for idx, attr in enumerate(from_data.components)
                        ]
                        attr2_options = [
                            {"label": getattr(attr, "label", str(attr)), "value": idx}
                            for idx, attr in enumerate(to_data.components)
                        ]

                        result_data = {
                            "attr1_options": attr1_options,
                            "attr2_options": attr2_options,
                            "attr1_selected": 0,  # Not used for coordinate pairs
                            "attr2_selected": 0,  # Not used for coordinate pairs
                            "attr1_label": f"Dataset 1 coordinates ({coord_type})",
                            "attr2_label": f"Dataset 2 coordinates ({coord_type})",
                            "is_multi_param": True,
                            "is_coordinate_pair": True,
                            "coord1_param_info": param1_info,
                            "coord2_param_info": param2_info,
                            "coordinate_type": coord_type,
                        }

                        return (link, result_data)

                # Fallback: Single-parameter coordinate helper
                if hasattr(link, "cids1") and hasattr(link, "cids2") and link.cids1 and link.cids2:
                    from_comp = link.cids1[0]
                    to_comp = link.cids2[0]
                else:
                    from_comp = from_data.components[0]
                    to_comp = to_data.components[0]

                is_multi_param = False
            else:
                return None  # Invalid coordinate helper structure

        # Type 3: JoinLink (database-style join on key columns)
        elif (
            hasattr(link, "cids1")
            and hasattr(link, "cids2")
            and hasattr(link, "data1")
            and hasattr(link, "data2")
        ):
            # JoinLink: cids1 and cids2 are single-element lists
            from_comp = link.cids1[0] if link.cids1 else None
            to_comp = link.cids2[0] if link.cids2 else None
            from_data = link.data1
            to_data = link.data2
            is_multi_param = False

            if from_comp is None or to_comp is None:
                return None  # Invalid JoinLink without key columns

        # Type 4: ComponentLink (transformation functions)
        elif hasattr(link, "_from") and hasattr(link, "_to"):
            if isinstance(link._from, list):
                # Multi-input ComponentLink (e.g., lengths_to_volume)
                from_comps = link._from
                from_data = from_comps[0].parent
                to_comp = link._to
                to_data = to_comp.parent

                # Detect multi-parameter function (N→1 pattern)
                if len(from_comps) > 1:
                    is_multi_param = True

                    # Extract function name for parameter labeling
                    function_name = "function"
                    if hasattr(link, "_using") and link._using:
                        function_name = getattr(link._using, "__name__", "function")

                    # Get function-specific parameter names
                    param_names = []
                    if function_name == "lengths_to_volume":
                        param_names = ["width", "height", "depth"]
                    else:
                        param_names = [f"param_{i+1}" for i in range(len(from_comps))]

                    # Build parameter info for each input component
                    param_info = []
                    for i, comp in enumerate(from_comps):
                        param_name = param_names[i] if i < len(param_names) else f"param_{i+1}"

                        # Find current selection index
                        param_selected = next(
                            (idx for idx, attr in enumerate(from_data.components) if attr == comp),
                            0,
                        )

                        param_data = {
                            "name": param_name,
                            "selected": param_selected,
                            "component": comp,
                            "label": getattr(comp, "label", str(comp)),
                        }

                        param_info.append(param_data)

                else:
                    # Single-input ComponentLink
                    from_comp = from_comps[0]
                    is_multi_param = False

            else:
                # Single ComponentID (not a list)
                from_comp = link._from
                from_data = from_comp.parent
                to_comp = link._to
                to_data = to_comp.parent
                is_multi_param = False

        else:
            return None  # Unknown link type

        # Step 3: Build dropdown options for both datasets
        # Create list of {label, value} dicts for Solara v.Select components
        attr1_options = [
            {"label": getattr(attr, "label", str(attr)), "value": idx}
            for idx, attr in enumerate(from_data.components)
        ]
        attr2_options = [
            {"label": getattr(attr, "label", str(attr)), "value": idx}
            for idx, attr in enumerate(to_data.components)
        ]

        # Step 4: Build return data structure based on link complexity
        if is_multi_param:
            # Multi-parameter link: Return structure with parameter info arrays
            # Find current selection for output component
            attr2_selected = next(
                (idx for idx, attr in enumerate(to_data.components) if attr == to_comp), 0
            )

            result_data = {
                "attr1_options": attr1_options,
                "attr2_options": attr2_options,
                "attr1_selected": 0,  # Not used for multi-param (individual params have selections)
                "attr2_selected": attr2_selected,
                "attr1_label": f"{function_name} parameters",
                "attr2_label": getattr(to_comp, "label", str(to_comp)),
                "is_multi_param": True,
                "multi_param_info": param_info,  # List of parameter data dicts
                "function_name": function_name,
            }

            return (link, result_data)

        else:
            # Single-parameter link: Return simple structure
            # Find current selections for both components
            attr1_selected = next(
                (idx for idx, attr in enumerate(from_data.components) if attr == from_comp), 0
            )
            attr2_selected = next(
                (idx for idx, attr in enumerate(to_data.components) if attr == to_comp), 0
            )

            result_data = {
                "attr1_options": attr1_options,
                "attr2_options": attr2_options,
                "attr1_selected": attr1_selected,
                "attr2_selected": attr2_selected,
                "attr1_label": getattr(from_comp, "label", str(from_comp)),
                "attr2_label": getattr(to_comp, "label", str(to_comp)),
                "is_multi_param": False,
            }

            return (link, result_data)

    except Exception:
        # Exception handler: Return None if any errors occur during link analysis
        return None
