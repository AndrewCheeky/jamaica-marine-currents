# Deploy the complete Jamaica Fishing Intelligence repository

This ZIP contains **all repository files**, including the hidden `.github/workflows/currents.yml` file. It is not a patch.

## Recommended: use Git to replace the repository contents

1. Back up the `main` branch and the separate `marine-observation-history` branch before deployment. Do **not** delete the history branch.
2. Clone the existing repository:

   ```bash
   git clone https://github.com/AndrewCheeky/jamaica-marine-currents.git
   cd jamaica-marine-currents
   ```

3. Extract this ZIP into a **separate temporary folder**. Copy all extracted files and folders, including the hidden `.github` directory, into the clone, overwriting existing files. Do not overwrite or delete the clone's `.git` directory. Check for obsolete tracked files separately; a normal copy does not remove them.
4. Confirm `.github/workflows/currents.yml` now contains `contents: write`, `Restore persistent history`, and `Save and verify persistent history`.
5. Commit and push:

   ```bash
   git add -A
   git commit -m "Deploy Fishing Intelligence v3.8.41 with persistent history workflow"
   git push origin main
   ```

6. Open GitHub > Actions > Generate Jamaica currents map > Run workflow (main).
7. Confirm the run includes **Run regression tests**, **Restore persistent history**, **Generate current map**, **Save and verify persistent history**, then **Deploy to Pages**.
8. Confirm logs contain `HISTORY RESTORE`, `HISTORY SAVE`, and `HISTORY VERIFY` (the first run may say the history branch did not yet exist). Run the workflow again to verify restoration from the saved branch.

## Permissions

The workflow declares:

```yaml
permissions:
  contents: write
  pages: write
  id-token: write
```

Repository or organization policy may still restrict writes. Verify GitHub Settings > Actions > General > Workflow permissions.

## Important safeguards

- Keep `marine-observation-history` intact. The dedicated branch is **not** meant to be copied into the main repository ZIP.
- The first run can initialize history; it cannot restore observations that were never stored.
- An Actions run failing during history restore/save should be investigated; do not disable the history steps just to get a green deployment.
- The ZIP is locally validated, but remote GitHub writes and live deployment require an actual Actions run.
