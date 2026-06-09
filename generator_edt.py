import re
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import argparse

SCALE = 3

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

def get_id_width(id_str):
    id_w = 40 * SCALE
    if len(id_str) > 3: id_w = 55 * SCALE
    if len(id_str) > 6: id_w = 70 * SCALE
    return id_w

def get_box_height(text, font, avail_w, min_h, line_h):
    words = text.split()
    lines = []
    curr_line = ""
    for w in words:
        test = curr_line + (" " if curr_line else "") + w
        bbox = font.getbbox(test)
        tw = bbox[2] - bbox[0]
        if tw <= avail_w:
            curr_line = test
        else:
            if curr_line:
                lines.append(curr_line)
            curr_line = w
    if curr_line:
        lines.append(curr_line)
    
    # Add padding for top and bottom
    needed_h = len(lines) * line_h + 15 * SCALE
    return max(min_h, needed_h), lines

def calculate_layout(lnode, box_w, min_h, h_spacing, v_spacing, font, line_h, start_x, start_y):
    # This function now sets ABSOLUTE coordinates for each node
    id_w = get_id_width(lnode.node['id'])
    avail_w = box_w - id_w - 12 * SCALE # 6px padding on each side of text
    lnode.height, lnode.text_lines = get_box_height(lnode.node['text'], font, avail_w, min_h, line_h)
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
        indent = 35 * SCALE
        for child in lnode.children:
            calculate_layout(child, box_w, min_h, h_spacing, v_spacing, font, line_h, start_x + indent, current_y)
            current_y += child.total_height + v_spacing
            max_w = max(max_w, indent + child.total_width)
        lnode.total_width = max_w
        lnode.total_height = (current_y - start_y) - (0 if not lnode.children else v_spacing)

def draw_node(draw, lnode, ox, oy, font_id, font_text, BOX_W):
    bx, by = ox + lnode.x, oy + lnode.y
    bh, bw = lnode.height, lnode.width
    
    id_w = get_id_width(lnode.node['id'])

    # Draw connectors to children (Vertical layout)
    line_thickness = max(1, SCALE // 2)
    if lnode.children and lnode.level >= 2:
        tx = bx + 22 * SCALE
        ty_start = by + bh
        last_child = lnode.children[-1]
        ty_end = oy + last_child.y + last_child.height/2
        draw.line([tx, ty_start, tx, ty_end], fill='black', width=line_thickness)
        for child in lnode.children:
            cy_mid = oy + child.y + child.height/2
            draw.line([tx, cy_mid, ox + child.x, cy_mid], fill='black', width=line_thickness)

    for child in lnode.children:
        draw_node(draw, child, ox, oy, font_id, font_text, BOX_W)

    # Colors by level
    level_colors = {
        1: '#E2E8F0', # Root
        2: '#BFDBFE', # Nivel 1
        3: '#BBF7D0', # Nivel 2
        4: '#FEF08A', # Nivel 3
        5: '#FED7AA', # Nivel 4
        6: '#FECACA'  # Nivel 5
    }
    bg_color = level_colors.get(lnode.level, '#F3F4F6')

    # Box
    draw.rectangle([bx, by, bx + bw, by + bh], outline='black', width=line_thickness, fill=bg_color)
    draw.line([bx + id_w, by, bx + id_w, by + bh], fill='black', width=line_thickness)
    
    # Text
    id_str = lnode.node['id']
    itw, ith = font_id.getbbox(id_str)[2], font_id.getbbox(id_str)[3]
    draw.text((bx + (id_w - itw)/2, by + (bh - ith)/2 - 2 * SCALE), id_str, fill='black', font=font_id)
    
    line_h = 13 * SCALE
    total_th = len(lnode.text_lines) * line_h
    sty = by + (bh - total_th)/2
    for i, line in enumerate(lnode.text_lines):
        draw.text((bx + id_w + 6 * SCALE, sty + i * line_h - 1 * SCALE), line, fill='black', font=font_text)

def main():
    parser = argparse.ArgumentParser(description="Generador de diagramas EDT.")
    parser.add_argument("input_file", help="Archivo de entrada (CSV o TXT)")
    parser.add_argument("--summary", "-s", action="store_true", default=True, help="Dibujar el resumen de actividades (por defecto: True)")
    parser.add_argument("--no-summary", action="store_false", dest="summary", help="No dibujar el resumen de actividades")
    parser.add_argument("--pos", "-p", choices=["left", "right"], default="right", help="Posición del resumen (derecha o izquierda, por defecto: right)")
    
    args = parser.parse_args()

    input_file = args.input_file
    if not os.path.exists(input_file):
        print(f"Error: El archivo '{input_file}' no existe.")
        return

    root = parse_input(input_file)
    if not root: 
        print("No se pudo cargar el EDT.")
        return
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{base_name}EDT.png"
    BOX_W, MIN_H, H_SPACE, V_SPACE, MARGIN = 210 * SCALE, 50 * SCALE, 45 * SCALE, 25 * SCALE, 60 * SCALE
    
    font_paths = [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf"
    ]
    
    f_id, f_txt = None, None
    successful_font_path = None
    for path in font_paths:
        try:
            f_id = ImageFont.truetype(path, 12 * SCALE)
            f_txt = ImageFont.truetype(path, 10 * SCALE)
            successful_font_path = path
            break
        except Exception as e:
            pass
            
    if not f_id:
        print("Aviso: No se encontraron fuentes con soporte para tildes. Usando fuente por defecto.")
        f_id = f_txt = ImageFont.load_default()

    lroot = LayoutNode(root, 1)
    calculate_layout(lroot, BOX_W, MIN_H, H_SPACE, V_SPACE, f_txt, 13 * SCALE, 0, 0)

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
    grid_spacing = 20 * SCALE
    for x in range(0, img_w, grid_spacing): draw.line([x,0,x,img_h], fill=(245,245,245))
    for y in range(0, img_h, grid_spacing): draw.line([0,y,img_w,y], fill=(245,245,245))

    # Connectors Level 1 -> Level 2
    rx, ry = MARGIN + lroot.x + BOX_W/2, MARGIN + lroot.y + lroot.height
    if lroot.children:
        by_bar = ry + V_SPACE * 1.5
        line_thickness = max(1, SCALE // 2)
        draw.line([rx, ry, rx, by_bar], fill='black', width=line_thickness)
        fc, lc = lroot.children[0], lroot.children[-1]
        draw.line([MARGIN+fc.x+BOX_W/2, by_bar, MARGIN+lc.x+BOX_W/2, by_bar], fill='black', width=line_thickness)
        for c in lroot.children:
            ccx = MARGIN + c.x + BOX_W/2
            draw.line([ccx, by_bar, ccx, MARGIN + c.y], fill='black', width=line_thickness)

    draw_node(draw, lroot, MARGIN, MARGIN, f_id, f_txt, BOX_W)

    if args.summary:
        # --- Resumen de actividades ---
        level_counts = {}
        leaf_count = 0
        def count_nodes(n):
            nonlocal leaf_count
            edt_level = n.level - 1
            if edt_level > 0:
                level_counts[edt_level] = level_counts.get(edt_level, 0) + 1
            if not n.children and edt_level > 0:
                leaf_count += 1
            for c in n.children:
                count_nodes(c)
                
        count_nodes(lroot)
        
        summary_lines = ["Resumen de actividades:"]
        total_activities = sum(level_counts.values())
        for lvl in sorted(level_counts.keys()):
            summary_lines.append(f" - Nivel {lvl}: {level_counts[lvl]} actividades")
        summary_lines.append(f" Total actividades: {total_activities}")
        summary_lines.append(f" Total tareas finales (hojas): {leaf_count}")
        # Create a 3x larger font for the summary
        try:
            if successful_font_path:
                f_summary = ImageFont.truetype(successful_font_path, 12 * SCALE * 3)
            else:
                f_summary = ImageFont.truetype("arial.ttf", 12 * SCALE * 3)
        except:
            f_summary = f_id

        pad = 45 * SCALE # 3x larger padding
        line_spacing = 24 * SCALE # 3x larger line spacing
        
        # Calcular tamaño de texto
        line_heights = [f_summary.getbbox(line)[3] - f_summary.getbbox(line)[1] for line in summary_lines]
        line_height = max(line_heights)
        
        sw = max(f_summary.getbbox(line)[2] - f_summary.getbbox(line)[0] for line in summary_lines)
        sh = len(summary_lines) * line_height + (len(summary_lines) - 1) * line_spacing
        
        if args.pos == "right":
            sx = img_w - MARGIN - sw - pad * 2
        else:
            sx = MARGIN
            
        sy = img_h - MARGIN - sh - pad * 2
        
        # Dibujar caja de fondo (blanco/gris claro) con sombra o borde
        border_width = max(3, SCALE * 3 // 2)
        draw.rectangle([sx, sy, sx + sw + pad * 2, sy + sh + pad * 2], fill='#FFFFFF', outline='black', width=border_width)
        
        # Escribir texto
        cy = sy + pad
        for line in summary_lines:
            draw.text((sx + pad, cy), line, fill='black', font=f_summary)
            cy += line_height + line_spacing
        # ------------------------------

    img.save(output_file)
    print(f"Diagrama guardado: {output_file} ({img_w}x{img_h})")

if __name__ == "__main__":
    main()
