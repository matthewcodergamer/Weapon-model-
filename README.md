# Project Strike Asset Uploader

**Current web version: V11**

Project Strike Asset Uploader is the model-ingestion and conversion front end for the browser FPS project **Project Strike**.

V11 is now the permanent production HTML entry. Future improvements should update `model-processor-v11.html` in place instead of creating `v12`, `v13`, or other duplicate HTML files. This keeps GitHub Pages, bookmarks, Safari caching, and debugging pointed at one source of truth.

## Web app

GitHub Pages:

`https://matthewcodergamer.github.io/Weapon-model-/`

The Pages root redirects to:

`model-processor-v11.html`

## What it accepts

- ZIP asset packages, including nested package folders
- GLB
- glTF + BIN + image dependencies
- FBX
- Blender `.blend` source packages
- PBR textures and reference images, including PNG, JPG/JPEG, TIFF, EXR, HDR, KTX2 and related image formats
- Mixamo/mocap FBX animation clips

## Pipeline

```text
Choose files / folder
        ↓
recursive package discovery
        ↓
model / animation / Blender / texture classification
        ↓
FBX + GLB browser validation and 3D preview
        ↓
organized upload to Fps-game-
        ↓
.blend packages trigger GitHub Actions
        ↓
headless Blender relinks package textures
        ↓
validated binary GLB export
        ↓
public/game-assets/<category>/<asset>.glb
```

## Blender assets

Three.js cannot natively render a `.blend` file in Safari. The uploader therefore preserves the original Blender package and all related textures under:

```text
assets-source/imports/<package>/
├── asset.json
└── raw/
    ├── model.blend
    └── textures/
```

The `Fps-game-` repository contains a headless Blender GitHub Actions pipeline that converts these packages to runtime GLB files.

The converter:

- searches the complete package for texture files;
- repairs broken Blender image paths by filename;
- preserves existing material node connections;
- can connect Base Color, Normal, Roughness and Metallic maps when the corresponding Principled BSDF input is otherwise unconnected;
- preserves meshes, hierarchy, skinning, armatures, animations and morph targets;
- exports binary GLB;
- verifies that a real GLB was generated and that it contains meshes;
- writes a JSON conversion report under `public/game-assets/manifests/conversion-reports/`.

## Project Strike destinations

Runtime models are organized under `public/game-assets/`, including:

```text
models/
├── weapons/
├── characters/
├── grenades/
├── environment/
└── props/

animations/
├── locomotion/
├── combat/
├── rifle/
├── pistol/
├── shotgun/
├── sniper/
├── grenade/
├── hit_reactions/
└── deaths/
```

The uploader keeps editable source assets separate from the optimized assets loaded by the game.

## Texture roles

The organizer recognizes common names for:

- Base Color / Albedo / Diffuse
- Normal
- Roughness
- Metallic
- AO
- ORM / ARM
- Height / Displacement
- Emissive
- Opacity / Alpha
- Specular
- Preview / reference images

## V11 production policy

V11 is the stable filename and production entry. New functionality is committed directly into `model-processor-v11.html`; the filename does not change just because the implementation improves. The FPS conversion workflow remains independently upgradeable in `Fps-game-` without requiring a new uploader HTML version.

## Related repository

Project Strike game:

`https://github.com/matthewcodergamer/Fps-game-`
