"""Build and register the BC → ASTC 4x4 pretranscode pack for an Apple resource pack."""
import sys
from pathlib import Path

ASTC_PACK = "astc.pack"


def build_for_pack(c, romfs, pack_dir, platform_name):
    """Build astc.pack from the shared extraction RomFS and update the resource-pack index.

    The caller must invoke this after the base resource pack has been created and before
    its index_sha256 is copied into game.json. If there is no RomFS, leave the pack unchanged.
    """
    romfs = Path(romfs)
    pack_dir = Path(pack_dir)
    if not romfs.is_dir():
        c.emit(message=f"这款没有 RomFS，{platform_name}包不用预转贴图")
        return None

    c.begin(f"把贴图预转成{platform_name}能直接用的格式（BC → ASTC）")
    log = c.logs / (c.task + "-astc.log")
    c.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            c.engine / "pack/astc_pack.py",
            "build",
            romfs,
            pack_dir / ASTC_PACK,
        ],
        log,
        c.env(),
    )

    from sgrade_bf import add_to_pack

    return add_to_pack(pack_dir, ASTC_PACK, [ASTC_PACK])
