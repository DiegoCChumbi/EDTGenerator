import re
from PIL import Image, ImageDraw, ImageFont
import os
import sys

def parse_input(file_path):
    nodes = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^([\d\.]+)\s*(.*)', line)
            if match:
                id_str = match.group(1).rstrip('.')
                text = match.group(2).strip()
                nodes[id_str] = {'id': id_str, 'text': text, 'children': []}
    
    # Build tree
    top_level_nodes = []
    for id_str in sorted(nodes.keys(), key=lambda s: [int(x) for x in s.split('.')]):
        node = nodes[id_str]
        parts = id_str.split('.')
        if len(parts) == 1:
            top_level_nodes.append(node)
        else:
            parent_id = '.'.join(parts[:-1])
            if parent_id in nodes:
                nodes[parent_id]['children'].append(node)
    
    if len(top_level_nodes) > 1:
        # Create virtual root
        root = {'id': 'EDT', 'text': 'Proyecto', 'children': top_level_nodes}
    elif len(top_level_nodes) == 1:
        root = top_level_nodes[0]
    else:
        root = None
                
    return root

class LayoutNode:
    def __init__(self, node, level):
        self.node = node
        self.level = level
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.children = [LayoutNode(c, level + 1) for c in node['children']]
        self.total_width = 0
        self.total_height = 0

def get_box_height(text, font, width, min_h, line_h):
    words = text.split()
    lines = []
    curr_line = ""
    for w in words:
        test = curr_line + (" " if curr_line else "") + w
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] < (width - 60): # 60 is id_w + padding
            curr_line = test
        else:
            lines.append(curr_line)
            curr_line = w
    lines.append(curr_line)
    return max(min_h, len(lines) * line_h + 12), lines

def calculate_layout(lnode, box_w, min_h, h_spacing, v_spacing, font, line_h, start_x, start_y):
    # This function now sets ABSOLUTE coordinates for each node
    lnode.height, lnode.text_lines = get_box_height(lnode.node['text'], font, box_w, min_h, line_h)
    lnode.width = box_w
    lnode.x = start_x
    lnode.y = start_y
    
    if lnode.level == 1:
        # Children are horizontal. We don't set their X here, we do it in main for centering.
        # But we need their total size.
        total_w = 0
        max_h = 0
        for child in lnode.children:
            # Temporary layout to get dimensions
            calculate_layout(child, box_w, min_h, h_spacing, v_spacing, font, line_h, 0, 0)
            total_w += child.total_width + h_spacing
            max_h = max(max_h, child.total_height)
        lnode.total_width = max(box_w, total_w - h_spacing if lnode.children else 0)
        lnode.total_height = lnode.height + v_spacing * 4 + max_h
    else:
        # Sub-nodes are vertical
        current_y = start_y + lnode.height + v_spacing
        max_w = box_w
        indent = 35
        for child in lnode.children:
            calculate_layout(child, box_w, min_h, h_spacing, v_spacing, font, line_h, start_x + indent, current_y)
            current_y += child.total_height + v_spacing
            max_w = max(max_w, indent + child.total_width)
        lnode.total_width = max_w
        lnode.total_height = (current_y - start_y) - (0 if not lnode.children else v_spacing)

def draw_node(draw, lnode, ox, oy, font_id, font_text, BOX_W):
    bx, by = ox + lnode.x, oy + lnode.y
    bh, bw = lnode.height, lnode.width
    
    id_w = 40
    if len(lnode.node['id']) > 3: id_w = 55
    if len(lnode.node['id']) > 6: id_w = 70

    # Draw connectors to children (Vertical layout)
    if lnode.children and lnode.level >= 2:
        tx = bx + 22
        ty_start = by + bh
        last_child = lnode.children[-1]
        ty_end = oy + last_child.y + last_child.height/2
        draw.line([tx, ty_start, tx, ty_end], fill='black', width=1)
        for child in lnode.children:
            cy_mid = oy + child.y + child.height/2
            draw.line([tx, cy_mid, ox + child.x, cy_mid], fill='black', width=1)

    for child in lnode.children:
        draw_node(draw, child, ox, oy, font_id, font_text, BOX_W)

    # Box
    draw.rectangle([bx, by, bx + bw, by + bh], outline='black', width=1, fill='white')
    draw.line([bx + id_w, by, bx + id_w, by + bh], fill='black', width=1)
    
    # Text
    id_str = lnode.node['id']
    itw, ith = font_id.getbbox(id_str)[2], font_id.getbbox(id_str)[3]
    draw.text((bx + (id_w - itw)/2, by + (bh - ith)/2 - 2), id_str, fill='black', font=font_id)
    
    line_h = 13
    total_th = len(lnode.text_lines) * line_h
    sty = by + (bh - total_th)/2
    for i, line in enumerate(lnode.text_lines):
        draw.text((bx + id_w + 6, sty + i * line_h - 1), line, fill='black', font=font_text)

def main():
    if len(sys.argv) < 2:
        print("Uso: python generator_edt.py <archivo_input.txt>")
        return

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: El archivo '{input_file}' no existe.")
        return

    root = parse_input(input_file)
    if not root: 
        print("No se pudo cargar el EDT.")
        return
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{base_name}EDT.png"
    BOX_W, MIN_H, H_SPACE, V_SPACE, MARGIN = 210, 50, 45, 25, 60
    try:
        f_id = ImageFont.truetype("arial.ttf", 12)
        f_txt = ImageFont.truetype("arial.ttf", 10)
    except:
        f_id = f_txt = ImageFont.load_default()

    lroot = LayoutNode(root, 1)
    calculate_layout(lroot, BOX_W, MIN_H, H_SPACE, V_SPACE, f_txt, 13, 0, 0)

    # Re-calculate absolute positions for the whole tree
    # Row width
    row_w = sum(c.total_width for c in lroot.children) + H_SPACE * (len(lroot.children) - 1)
    canvas_w = max(lroot.total_width, row_w)
    
    lroot.x = (canvas_w - BOX_W) / 2
    lroot.y = 0
    
    cx = (canvas_w - row_w) / 2
    for child in lroot.children:
        # Offset all sub-nodes of this child
        dx = cx - 0 # relative to initial layout
        dy = (lroot.height + V_SPACE * 3) - 0
        def offset_subtree(n, ox, oy):
            n.x += ox
            n.y += oy
            for cc in n.children: offset_subtree(cc, ox, oy)
        offset_subtree(child, dx, dy)
        cx += child.total_width + H_SPACE

    img_w, img_h = int(canvas_w + 2*MARGIN), int(lroot.total_height + 2*MARGIN)
    img = Image.new('RGB', (img_w, img_h), color='white')
    draw = ImageDraw.Draw(img)
    for x in range(0, img_w, 20): draw.line([x,0,x,img_h], fill=(245,245,245))
    for y in range(0, img_h, 20): draw.line([0,y,img_w,y], fill=(245,245,245))

    # Connectors Level 1 -> Level 2
    rx, ry = MARGIN + lroot.x + BOX_W/2, MARGIN + lroot.y + lroot.height
    if lroot.children:
        by_bar = ry + V_SPACE * 1.5
        draw.line([rx, ry, rx, by_bar], fill='black', width=1)
        fc, lc = lroot.children[0], lroot.children[-1]
        draw.line([MARGIN+fc.x+BOX_W/2, by_bar, MARGIN+lc.x+BOX_W/2, by_bar], fill='black', width=1)
        for c in lroot.children:
            ccx = MARGIN + c.x + BOX_W/2
            draw.line([ccx, by_bar, ccx, MARGIN + c.y], fill='black', width=1)

    draw_node(draw, lroot, MARGIN, MARGIN, f_id, f_txt, BOX_W)
    img.save(output_file)
    print(f"Diagrama guardado: {output_file} ({img_w}x{img_h})")

if __name__ == "__main__":
    main()
