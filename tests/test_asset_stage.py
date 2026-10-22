"""Offline tests for the stage ledger. No network, no GPU."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import asset_stage as stage  # noqa: E402


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        stage.main(["init", str(self.root), "--name", "ants", "--target", "godot"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_then_edit_prompt_stales_downstream_only_after_files_exist(self):
        stage.main(["add", str(self.root), "01_fire", "fire ant, six legs"])
        project = stage.load(self.root)
        self.assertEqual(project["assets"]["01_fire"]["stages"]["prompt"]["status"], "ok")
        self.assertEqual(project["assets"]["01_fire"]["stages"]["image"]["status"], "missing")

        img = self.root / "images" / "01_fire.png"
        img.write_bytes(b"png-a")
        stage.main(["import", str(self.root), "01_fire", "--stage", "image", "--file", str(img), "--source", "flux"])
        mesh = self.root / "assets" / "glb" / "01_fire.glb"
        mesh.parent.mkdir(parents=True, exist_ok=True)
        mesh.write_bytes(b"glb-a")
        stage.main(["import", str(self.root), "01_fire", "--stage", "mesh", "--file", str(mesh), "--source", "trellis"])

        stage.main(["set-prompt", str(self.root), "01_fire", "ice ant, six legs"])
        project = stage.load(self.root)
        stages = project["assets"]["01_fire"]["stages"]
        self.assertEqual(stages["prompt"]["status"], "ok")
        self.assertEqual(stages["image"]["status"], "stale")
        self.assertEqual(stages["mesh"]["status"], "stale")
        self.assertEqual(project["assets"]["01_fire"]["prompt"], "ice ant, six legs")

    def test_mesh_edit_does_not_stale_the_image(self):
        stage.main(["add", str(self.root), "01_fire", "fire ant"])
        img = self.root / "images" / "01_fire.png"
        img.write_bytes(b"png")
        stage.main(["import", str(self.root), "01_fire", "--stage", "image", "--file", str(img)])
        mesh = self.root / "assets" / "glb" / "01_fire.glb"
        mesh.parent.mkdir(parents=True, exist_ok=True)
        mesh.write_bytes(b"glb-v1")
        stage.main(["import", str(self.root), "01_fire", "--stage", "mesh", "--file", str(mesh), "--source", "blender"])
        rig = self.root / "assets" / "rigged" / "01_fire_rigged.glb"
        rig.parent.mkdir(parents=True, exist_ok=True)
        rig.write_bytes(b"rig-v1")
        stage.main(["import", str(self.root), "01_fire", "--stage", "rig", "--file", str(rig)])

        mesh.write_bytes(b"glb-v2-blender-edit")
        stage.main(["refresh", str(self.root)])
        project = stage.load(self.root)
        stages = project["assets"]["01_fire"]["stages"]
        self.assertEqual(stages["image"]["status"], "ok")
        self.assertEqual(stages["mesh"]["source"], "external-edit")
        self.assertEqual(stages["rig"]["status"], "stale")
        self.assertEqual(stages["animation"]["status"], "missing")

    def test_plan_after_mesh_edit_is_rig_only(self):
        stage.main(["add", str(self.root), "01_fire", "fire ant"])
        img = self.root / "images" / "01_fire.png"
        img.write_bytes(b"png")
        stage.main(["import", str(self.root), "01_fire", "--stage", "image", "--file", str(img)])
        mask = self.root / "images_masked" / "01_fire.png"
        mask.parent.mkdir(parents=True, exist_ok=True)
        mask.write_bytes(b"mask")
        stage.main(["import", str(self.root), "01_fire", "--stage", "mask", "--file", str(mask)])
        mesh = self.root / "assets" / "glb" / "01_fire.glb"
        mesh.parent.mkdir(parents=True, exist_ok=True)
        mesh.write_bytes(b"glb")
        stage.main(["import", str(self.root), "01_fire", "--stage", "mesh", "--file", str(mesh)])
        rig = self.root / "assets" / "rigged" / "01_fire_rigged.glb"
        rig.parent.mkdir(parents=True, exist_ok=True)
        rig.write_bytes(b"rig")
        stage.main(["import", str(self.root), "01_fire", "--stage", "rig", "--file", str(rig)])
        mesh.write_bytes(b"edited")
        stage.main(["refresh", str(self.root)])
        project = stage.load(self.root)
        steps = stage.plan_asset(self.root, project, "01_fire", "rig")
        self.assertEqual([s["stage"] for s in steps], ["rig"])

    def test_adopt_skips_comments_and_matches_by_words_not_index(self):
        colony = self.root / "colony"
        (colony / "images").mkdir(parents=True)
        (colony / "prompts").mkdir()
        (colony / "images" / "01_fire_ant.png").write_bytes(b"a")
        (colony / "images" / "02_ice_ant.png").write_bytes(b"b")
        (colony / "prompts" / "ants.txt").write_text(
            "# this comment used to shift every prompt\n"
            "# another comment\n"
            "fire ant warrior, glowing ember carapace\n"
            "ice ant scout, frost carapace\n"
        )
        stage.main(["adopt", str(colony), "--name", "colony"])
        project = stage.load(colony)
        self.assertEqual(project["assets"]["01_fire_ant"]["prompt"], "fire ant warrior, glowing ember carapace")
        self.assertEqual(project["assets"]["02_ice_ant"]["prompt"], "ice ant scout, frost carapace")
        self.assertNotIn("comment", project["assets"]["01_fire_ant"]["prompt"])
        resolved = (colony / "prompts" / "resolved.txt").read_text().splitlines()
        self.assertEqual(resolved[0], "fire ant warrior, glowing ember carapace")

    def test_prompt_lines_drop_comments(self):
        p = self.root / "p.txt"
        p.write_text("# header\n\nfire ant\n# mid\nice ant\n")
        self.assertEqual(stage.prompt_lines(p), ["fire ant", "ice ant"])


if __name__ == "__main__":
    unittest.main()
