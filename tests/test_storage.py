"""Saves a fake run, reads it back, checks the columns match fake_history(), then deletes it."""
import logging
import uuid

from contract import fake_history, fake_triage
import storage

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

print("Backend:", storage.storage_backend())

result = fake_triage("https://github.com/test/storage-check", 10)
run_id = "test" + uuid.uuid4().hex[:8]
used = storage.save_results(run_id, result["repo"], result["prs"], result["model_used"])
print(f"Saved {len(result['prs'])} rows to: {used}")

df = storage.load_history()
assert list(df.columns) == list(fake_history().columns), (list(df.columns), list(fake_history().columns))
mine = df[df["run_id"] == run_id]
assert len(mine) == len(result["prs"]), len(mine)
assert "links_issue" in ",".join(mine["failed_checks"]), "failed_checks not saved"
assert str(df["scored_at"].dtype).startswith("datetime"), df["scored_at"].dtype
print(f"Loaded {len(df)} rows total; columns match fake_history(). Sample:")
print(mine[["repo", "pr_number", "final_score", "tier", "failed_checks"]].head(3).to_string(index=False))

storage.delete_run(run_id)
assert (storage.load_history()["run_id"] == run_id).sum() == 0
print("Cleaned up test rows. OK")
