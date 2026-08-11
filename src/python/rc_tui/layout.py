from .text_utils import display_width, split_by_width, wrap_by_width


def parse_dim(val, parent_dim):
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.endswith("%") and parent_dim is not None:
        return int(parent_dim * float(val[:-1]) / 100)
    return None


def _normalize_spacing(val):
    if isinstance(val, (list, tuple)):
        if len(val) == 1:
            return val[0], val[0], val[0], val[0]
        if len(val) == 2:
            return val[0], val[1], val[0], val[1]
        if len(val) == 3:
            return val[0], val[1], val[2], val[1]
        if len(val) == 4:
            return tuple(val)
    return val, val, val, val


def get_spacing(node):
    pad = node.props.get("padding", 0)
    mar = node.props.get("margin", 0)

    if isinstance(pad, (list, tuple)):
        pt, pr, pb, pl = _normalize_spacing(pad)
    else:
        pt = node.props.get("padding_top", pad)
        pr = node.props.get("padding_right", pad)
        pb = node.props.get("padding_bottom", pad)
        pl = node.props.get("padding_left", pad)

    if isinstance(mar, (list, tuple)):
        mt, mr, mb, ml = _normalize_spacing(mar)
    else:
        mt = node.props.get("margin_top", mar)
        mr = node.props.get("margin_right", mar)
        mb = node.props.get("margin_bottom", mar)
        ml = node.props.get("margin_left", mar)

    if node.props.get("border"):
        pt += 1
        pb += 1
        pl += 1
        pr += 1
    else:
        if node.props.get("border_top"):
            pt += 1
        if node.props.get("border_bottom"):
            pb += 1
        if node.props.get("border_left"):
            pl += 1
        if node.props.get("border_right"):
            pr += 1

    return (pt, pb, pl, pr), (mt, mb, ml, mr)


def _apply_constraints(node, avail_w, avail_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    w = parse_dim(w_prop, avail_w) if w_prop is not None else avail_w
    h = parse_dim(h_prop, avail_h) if h_prop is not None else avail_h
    min_w = node.props.get("min_width", 0)
    max_w = node.props.get("max_width", avail_w)
    min_h = node.props.get("min_height", 0)
    max_h = node.props.get("max_height", avail_h)
    return max(min_w, min(w, max_w)), max(min_h, min(h, max_h))


def _get_flex_basis(child, measured_main):
    basis = child.props.get("flex_basis", "auto")
    if basis == "auto":
        return measured_main
    if isinstance(basis, int):
        return basis
    return measured_main


def measure(node, max_w, max_h):
    if node.type in ("text", "span"):
        text = str(node.props.get("text", ""))
        lines = text.split("\n")

        # If node has children (styled spans) with no own text, measure children inline (row)
        if node.children and not text:
            cw = 0
            ch = 0
            for child in node.children:
                if child is None:
                    continue
                mw, mh = measure(child, max_w, max_h)
                cw += mw
                ch = max(ch, mh)
            return cw, ch

        wrap = node.props.get("wrap_mode", "word")
        if max_w is not None and wrap != "none":
            wrapped_lines = []
            for line in lines:
                if display_width(line) > max_w:
                    if wrap == "char":
                        wrapped_lines.extend(split_by_width(line, max_w))
                    else:
                        wrapped_lines.extend(wrap_by_width(line, max_w))
                else:
                    wrapped_lines.append(line)
        else:
            wrapped_lines = lines
        w = max((display_width(line) for line in wrapped_lines), default=0)
        h = len(wrapped_lines)
        return w, h

        return w, h

    from .widgets import _MEASURE

    handler = _MEASURE.get(node.type)
    if handler:
        return handler(node, max_w, max_h)

    (pt, pb, pl, pr), (mt, mb, ml, mr) = get_spacing(node)
    inner_max_w = max_w - pl - pr - ml - mr if max_w is not None else None
    inner_max_h = max_h - pt - pb - mt - mb if max_h is not None else None

    if inner_max_h is not None and inner_max_h <= 0:
        return 0, 0
    if inner_max_w is not None and inner_max_w <= 0:
        return 0, 0

    flex_dir = node.props.get("flex_direction", "column")
    measured_w = 0
    measured_h = 0

    for child in node.children:
        if child is None:
            continue
        cw, ch = measure(child, inner_max_w, inner_max_h)
        (cpt, cpb, cpl, cpr), (cmt, cmb, cml, cmr) = get_spacing(child)
        child_main = (
            (ch + cpt + cpb + cmt + cmb) if flex_dir == "column" else (cw + cpl + cpr + cml + cmr)
        )
        child_cross = (
            (cw + cpl + cpr + cml + cmr) if flex_dir == "column" else (ch + cpt + cpb + cmt + cmb)
        )
        if flex_dir == "column":
            measured_w = max(measured_w, child_cross)
            measured_h += child_main
        else:
            measured_w += child_main
            measured_h = max(measured_h, child_cross)

    # Gaps between children contribute to the intrinsic size too.
    child_count = sum(1 for c in node.children if c is not None)
    gap = node.props.get("gap", 0)
    if child_count > 1 and gap:
        if flex_dir == "column":
            measured_h += gap * (child_count - 1)
        else:
            measured_w += gap * (child_count - 1)

    # Scroll containers clamp to the available space; overflowing content
    # scrolls instead of stretching the whole layout past the screen.
    if node.type == "scrollbox":
        if flex_dir == "column" and inner_max_h is not None:
            measured_h = min(measured_h, inner_max_h)
        elif flex_dir == "row" and inner_max_w is not None:
            measured_w = min(measured_w, inner_max_w)

    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    if w_prop is not None:
        w = max(0, parse_dim(w_prop, max_w) - pl - pr - ml - mr)
    else:
        w = measured_w
    if h_prop is not None:
        h = max(0, parse_dim(h_prop, max_h) - pt - pb - mt - mb)
    else:
        h = measured_h
    return w, h


def layout(node, x, y, avail_w, avail_h, parent_screen_x=0, parent_screen_y=0):
    (pt, pb, pl, pr), (mt, mb, ml, mr) = get_spacing(node)

    if node.type in ("dialog", "modal"):
        cw, ch = measure(node, avail_w, avail_h)
        cw, ch = _apply_constraints(node, avail_w - ml - mr, avail_h - mt - mb)
        if node.props.get("x") is None:
            x = (avail_w - cw) // 2
        if node.props.get("y") is None:
            y = (avail_h - ch) // 2
        avail_w = cw + ml + mr
        avail_h = ch + mt + mb

    # Absolute positioning: skip flex layout, use x/y directly
    pos_type = node.props.get("position", "relative")
    if pos_type == "absolute":
        abs_x = node.props.get("x", 0)
        abs_y = node.props.get("y", 0)
        has_w = node.props.get("width") is not None
        has_h = node.props.get("height") is not None
        if has_w:
            abs_w = parse_dim(node.props.get("width"), avail_w)
        else:
            abs_w = 0
        if has_h:
            abs_h = parse_dim(node.props.get("height"), avail_h)
        else:
            abs_h = 0
        if not (has_w and has_h):
            measured_w, measured_h = measure(node, avail_w, avail_h)
            if not has_w:
                abs_w = measured_w
            if not has_h:
                abs_h = measured_h
        assigned_w, assigned_h = _apply_constraints(
            node, abs_w if abs_w else avail_w, abs_h if abs_h else avail_h
        )
        node.x = x + ml + abs_x
        node.y = y + mt + abs_y
        node.w = assigned_w
        node.h = assigned_h
        node.screen_x = parent_screen_x + node.x
        node.screen_y = parent_screen_y + node.y
        # Layout children with the absolute-sized space
        inner_w = node.w - pl - pr
        inner_h = node.h - pt - pb
        if inner_w > 0 and inner_h > 0 and node.children:
            _layout_children(node, inner_w, inner_h, pl, pr, pt, pb)
        node.content_w = node.w
        node.content_h = node.h
        return

    assigned_w, assigned_h = _apply_constraints(node, avail_w - ml - mr, avail_h - mt - mb)

    node.x = x + ml
    node.y = y + mt
    node.w = assigned_w
    node.h = assigned_h
    node.screen_x = parent_screen_x + node.x
    node.screen_y = parent_screen_y + node.y

    inner_w = node.w - pl - pr
    inner_h = node.h - pt - pb

    if inner_w <= 0 or inner_h <= 0:
        node.content_w = 0
        node.content_h = 0
        return

    if not node.children:
        node.content_w = 0
        node.content_h = 0
        return

    # Text/span nodes with children layout spans inline (row)
    if node.type in ("text", "span") and node.children:
        curr_x = pl
        max_h = 0
        for child in node.children:
            if child is None:
                continue
            cw, ch = measure(child, inner_w, inner_h)
            layout(child, curr_x, pt, cw, ch, node.screen_x, node.screen_y)
            curr_x += cw
            max_h = max(max_h, ch + pt)
        node.content_w = curr_x - pl
        node.content_h = max_h
        return

    _layout_children(node, inner_w, inner_h, pl, pr, pt, pb)


def _layout_children(node, inner_w, inner_h, pl, pr, pt, pb):
    child_data = []
    for child in node.children:
        if child is None or child.props.get("position") == "absolute":
            continue
        grow = child.props.get("flex_grow", 0)
        shrink = child.props.get("flex_shrink", 1)
        cw, ch = measure(child, inner_w, inner_h)
        (cpt, cpb, cpl, cpr), (cmt, cmb, cml, cmr) = get_spacing(child)
        child_data.append((child, cw, ch, grow, shrink, cpt, cpb, cpl, cpr, cmt, cmb, cml, cmr))

    flex_dir = node.props.get("flex_direction", "column")
    gap = node.props.get("gap", 0)
    justify = node.props.get("justify_content", "flex-start")
    align = node.props.get("align_items", "stretch")

    # Phase 1: calculate initial sizes with flex_basis
    flex_grow_total = 0
    flex_shrink_total = 0
    total_basis_main = 0
    for _child, cw, ch, grow, shrink, cpt, cpb, cpl, cpr, cmt, cmb, cml, cmr in child_data:
        measured_main = (
            (ch + cpt + cpb + cmt + cmb) if flex_dir == "column" else (cw + cpl + cpr + cml + cmr)
        )
        basis = _get_flex_basis(_child, measured_main)
        total_basis_main += basis
        if grow > 0:
            flex_grow_total += grow
        if shrink > 0:
            flex_shrink_total += shrink

    gap_count = max(0, len(child_data) - 1)
    total_basis_main += gap_count * gap
    available_main = inner_h if flex_dir == "column" else inner_w

    overflow = total_basis_main - available_main

    # Scroll containers never shrink or stretch their children: content keeps
    # its natural size and overflows, scrolling inside the clip rect.
    if node.type == "scrollbox":
        overflow = 0

    # Phase 2: distribute
    justify_offset = 0
    justify_gap = gap

    if overflow > 0 and flex_shrink_total > 0:
        # Shrink mode: proportionally reduce children
        pass  # handled per-child below
    elif overflow < 0 and flex_grow_total > 0:
        remaining = -overflow
        justify_offset = 0
        justify_gap = gap
        if justify == "center":
            justify_offset = remaining // 2
        elif justify == "flex-end":
            justify_offset = remaining
        elif justify == "space-between" and len(child_data) > 1:
            justify_gap = remaining // (len(child_data) - 1)
        elif justify == "space-around" and len(child_data) > 0:
            justify_gap = remaining // len(child_data)
            justify_offset = justify_gap // 2
        elif justify == "space-evenly" and len(child_data) > 0:
            justify_gap = remaining // (len(child_data) + 1)
            justify_offset = justify_gap
    else:
        remaining = 0
        if justify == "center":
            justify_offset = (available_main - total_basis_main) // 2
        elif justify == "flex-end":
            justify_offset = available_main - total_basis_main
        elif justify == "space-between" and len(child_data) > 1:
            justify_gap = (
                (available_main - total_basis_main) // (len(child_data) - 1)
                if len(child_data) > 1
                else 0
            )
        elif justify == "space-around" and len(child_data) > 0:
            justify_gap = (available_main - total_basis_main) // len(child_data)
            justify_offset = justify_gap // 2
        elif justify == "space-evenly" and len(child_data) > 0:
            justify_gap = (available_main - total_basis_main) // (len(child_data) + 1)
            justify_offset = justify_gap

    # Pre-compute shrink shares so integer truncation and the minimum-size
    # floor (children never shrink below 1) don't leave containers overfull.
    shrink_shares = []
    if overflow > 0 and flex_shrink_total > 0:
        bases = []
        for child, cw, ch, _grow, _shrink, cpt, cpb, cpl, cpr, cmt, cmb, cml, cmr in child_data:
            measured_main = (
                (ch + cpt + cpb + cmt + cmb)
                if flex_dir == "column"
                else (cw + cpl + cpr + cml + cmr)
            )
            bases.append(_get_flex_basis(child, measured_main))

        remaining = overflow
        for idx, (
            _child,
            _cw,
            _ch,
            _grow,
            shrink,
            _cpt,
            _cpb,
            _cpl,
            _cpr,
            _cmt,
            _cmb,
            _cml,
            _cmr,
        ) in enumerate(child_data):
            if shrink <= 0:
                shrink_shares.append(0)
                continue
            share = min(int(overflow * (shrink / flex_shrink_total)), bases[idx] - 1)
            share = max(0, share)
            shrink_shares.append(share)
            remaining -= share

        # Redistribute the leftover (children that hit their floor released
        # their share) to the children with the most room left.
        while remaining > 0:
            best = None
            best_room = 0
            for idx, share in enumerate(shrink_shares):
                room = bases[idx] - 1 - share
                if room > best_room:
                    best_room = room
                    best = idx
            if best is None or best_room <= 0:
                break
            add = min(remaining, best_room)
            shrink_shares[best] += add
            remaining -= add
    else:
        shrink_shares = [0] * len(child_data)

    current_x = pl + (justify_offset if flex_dir == "row" else 0)
    current_y = pt + (justify_offset if flex_dir == "column" else 0)
    content_w = 0
    content_h = 0

    for (child, cw, ch, grow, shrink, cpt, cpb, cpl, cpr, cmt, cmb, cml, cmr), _shrunk in zip(
        child_data, shrink_shares
    ):
        measured_main = (
            (ch + cpt + cpb + cmt + cmb) if flex_dir == "column" else (cw + cpl + cpr + cml + cmr)
        )
        basis = _get_flex_basis(child, measured_main)

        if overflow > 0 and shrink > 0 and flex_shrink_total > 0:
            shrunk = max(1, basis - _shrunk)
            if flex_dir == "column":
                child_h = shrunk
                child_w = cw + cpl + cpr + cml + cmr
                if child.props.get("width") is None and _get_align(child, align) == "stretch":
                    child_w = inner_w
            else:
                child_w = shrunk
                child_h = ch + cpt + cpb + cmt + cmb
                if child.props.get("height") is None and _get_align(child, align) == "stretch":
                    child_h = inner_h
        elif overflow <= 0 and grow > 0 and flex_grow_total > 0:
            share = int((-overflow) * (grow / flex_grow_total)) if overflow < 0 else 0
            if flex_dir == "column":
                child_h = basis + share
                child_w = cw + cpl + cpr + cml + cmr
                if child.props.get("width") is None and _get_align(child, align) == "stretch":
                    child_w = inner_w
            else:
                child_w = basis + share
                child_h = ch + cpt + cpb + cmt + cmb
                if child.props.get("height") is None and _get_align(child, align) == "stretch":
                    child_h = inner_h
        else:
            if flex_dir == "column":
                child_h = basis
                child_w = cw + cpl + cpr + cml + cmr
                if child.props.get("width") is None and _get_align(child, align) == "stretch":
                    child_w = inner_w
            else:
                child_w = basis
                child_h = ch + cpt + cpb + cmt + cmb
                if child.props.get("height") is None and _get_align(child, align) == "stretch":
                    child_h = inner_h

        child_align = _get_align(child, align)
        cross_offset = 0
        if child_align == "center":
            if flex_dir == "column":
                cross_offset = (inner_w - child_w) // 2
            else:
                cross_offset = (inner_h - child_h) // 2
        elif child_align == "flex-end":
            if flex_dir == "column":
                cross_offset = inner_w - child_w
            else:
                cross_offset = inner_h - child_h
        elif child_align == "flex-start":
            cross_offset = 0

        scroll_off_y = node.scroll_y if node.type == "scrollbox" else 0
        scroll_off_x = node.scroll_x if node.type == "scrollbox" else 0

        layout(
            child,
            current_x + (cross_offset if flex_dir == "column" else 0),
            current_y + (cross_offset if flex_dir == "row" else 0),
            child_w,
            child_h,
            node.screen_x - scroll_off_x,
            node.screen_y - scroll_off_y,
        )

        if flex_dir == "column":
            current_y += child_h + justify_gap
            content_w = max(content_w, child_w)
            content_h += child_h
        else:
            current_x += child_w + justify_gap
            content_w += child_w
            content_h = max(content_h, child_h)

    node.content_w = content_w
    node.content_h = content_h

    # Layout absolute children (skipped from flex flow)
    for child in node.children:
        if child is None:
            continue
        if child.props.get("position") == "absolute":
            layout(child, node.x, node.y, inner_w, inner_h, node.screen_x, node.screen_y)


def _get_align(child, parent_align):
    return child.props.get("align_self", parent_align)


do_layout = layout
