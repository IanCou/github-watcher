from github_watcher import services
from github_watcher.core import config_io

SAMPLE = """
channels:
  ntfy-main:
    url: "ntfy://${NTFY_TOKEN}@h/t"
watches:
  - name: bigtech-swe
    repo: SimplifyJobs/Summer2026-Internships
    branch: dev
    interval: 60
    channels: [ntfy-main]
    filters:
      files: { include: ["**/listings.json"] }
      diff: { include: ['(?i)"company_name":\\\\s*"Amazon"'] }
  - name: bigtech-issues
    repo: SimplifyJobs/Summer2026-Internships
    kind: issues
    channels: [ntfy-main]
    filters:
      message: { include: ["(?i)amazon"] }
"""


def test_import_then_export_roundtrip(fresh_db):
    n_ch, n_w = config_io.import_yaml(SAMPLE)
    assert (n_ch, n_w) == (1, 2)

    watches = {w.name: w for w in services.list_watches()}
    assert watches["bigtech-swe"].kind == "commits"
    assert watches["bigtech-issues"].kind == "issues"
    assert watches["bigtech-swe"].branch == "dev"

    exported = config_io.export_yaml()
    assert "bigtech-swe" in exported
    assert "kind: issues" in exported  # non-default kind is emitted
    assert "ntfy-main" in exported


def test_import_is_idempotent_upsert(fresh_db):
    config_io.import_yaml(SAMPLE)
    config_io.import_yaml(SAMPLE)  # second import updates, not duplicates
    assert len(services.list_watches()) == 2
    assert len(services.list_channels()) == 1


def test_import_replace_clears_existing(fresh_db):
    config_io.import_yaml(SAMPLE)
    config_io.import_yaml("channels: {}\nwatches: []\n", replace=True)
    assert services.list_watches() == []
    assert services.list_channels() == []
