import os
from PIL import Image, ImageDraw

def create_brand_assets():
    source_jpg = "/Users/ryantruong/.gemini/antigravity-cli/brain/e63f244e-c1af-4b32-80e4-2ad528b55426/toeic_master_logo_1790944990292.jpg"
    public_dir = "/Users/ryantruong/Project/Tu_hoc_Toeic/apps/web/public"
    app_dir = "/Users/ryantruong/Project/Tu_hoc_Toeic/apps/web/app"
    os.makedirs(public_dir, exist_ok=True)
    os.makedirs(app_dir, exist_ok=True)

    src = Image.open(source_jpg).convert("RGB")

    # 1. Full brand logo (1024x1024 crop of emblem + text)
    full_box = (150, 160, 874, 860)
    full_logo = src.crop(full_box)
    full_rgba = full_logo.convert("RGBA")
    pdata = full_rgba.load()
    w, h = full_rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pdata[x, y]
            dist = ((255 - r)**2 + (255 - g)**2 + (255 - b)**2)**0.5
            if dist < 14:
                pdata[x, y] = (255, 255, 255, 0)
            elif dist < 38:
                alpha = int(255 * (dist - 14) / (38 - 14))
                pdata[x, y] = (r, g, b, alpha)
    
    full_rgba.save(os.path.join(public_dir, "logo.png"), "PNG")
    print("✓ Saved logo.png")

    # 2. Transparent Emblem (512x512)
    emblem_box = (320, 195, 705, 640)
    emblem = src.crop(emblem_box)
    ew, eh = emblem.size
    emblem_rgba = emblem.convert("RGBA")
    epdata = emblem_rgba.load()
    for y in range(eh):
        for x in range(ew):
            r, g, b, a = epdata[x, y]
            dist = ((255 - r)**2 + (255 - g)**2 + (255 - b)**2)**0.5
            if dist < 14:
                epdata[x, y] = (255, 255, 255, 0)
            elif dist < 38:
                alpha = int(255 * (dist - 14) / (38 - 14))
                epdata[x, y] = (r, g, b, alpha)

    mark_512 = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    scale = min(440 / ew, 440 / eh)
    nw, nh = int(ew * scale), int(eh * scale)
    emblem_resized = emblem_rgba.resize((nw, nh), Image.Resampling.LANCZOS)
    mark_512.paste(emblem_resized, ((512 - nw) // 2, (512 - nh) // 2), emblem_resized)
    mark_512.save(os.path.join(public_dir, "logo-mark.png"), "PNG")
    print("✓ Saved logo-mark.png")

    # 3. Modern Dark Squircle Tile (512x512)
    tile_512 = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile_512)
    bg_color = (15, 23, 42, 255) # slate-900
    border_color = (51, 65, 85, 255) # slate-700
    draw.rounded_rectangle([4, 4, 507, 507], radius=116, fill=bg_color, outline=border_color, width=5)

    tile_scale = min(360 / ew, 360 / eh)
    tnw, tnh = int(ew * tile_scale), int(eh * tile_scale)
    t_emblem = emblem_rgba.resize((tnw, tnh), Image.Resampling.LANCZOS)
    tile_512.paste(t_emblem, ((512 - tnw) // 2, (512 - tnh) // 2), t_emblem)
    tile_512.save(os.path.join(public_dir, "logo-tile.png"), "PNG")
    print("✓ Saved logo-tile.png")

    # 4. Apple Touch Icon (180x180)
    apple_icon = tile_512.resize((180, 180), Image.Resampling.LANCZOS)
    apple_icon.save(os.path.join(public_dir, "apple-touch-icon.png"), "PNG")
    print("✓ Saved apple-touch-icon.png")

    # 5. Multi-size Favicon (16, 32, 48, 64)
    fav_sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
    tile_512.save(os.path.join(public_dir, "favicon.ico"), format="ICO", sizes=fav_sizes)
    tile_512.save(os.path.join(app_dir, "favicon.ico"), format="ICO", sizes=fav_sizes)
    print("✓ Saved multi-size favicon.ico (public/ and app/)")

    # 6. Web Manifest Icon (192x192 & 512x512)
    tile_512.resize((192, 192), Image.Resampling.LANCZOS).save(os.path.join(public_dir, "icon-192.png"), "PNG")
    tile_512.save(os.path.join(public_dir, "icon-512.png"), "PNG")
    print("✓ Saved icon-192.png and icon-512.png")

create_brand_assets()
