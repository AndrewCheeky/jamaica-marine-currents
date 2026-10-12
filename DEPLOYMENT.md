# Deploy Jamaica Fishing Intelligence v3.8.42 (visible-file package)

**All 23 files in this ZIP are visible.** The GitHub Actions workflow is included as `github-workflows/currents.yml` rather than a hidden file.

**GitHub requires `.github/workflows/currents.yml` to execute Actions.** The supplied `install_workflow.py` creates that required hidden directory automatically. Simply uploading the ZIP through GitHub's web interface will NOT activate the workflow. You must run the installer and commit the generated workflow through Git.

## Deployment using Git (Mac, Windows or Linux)

1. Back up your existing `main` branch and **do not delete** `marine-observation-history`.
2. Clone the repository: `git clone https://github.com/AndrewCheeky/jamaica-marine-currents.git`.
3. Extract the ZIP to a temporary folder and copy its **visible** contents into the cloned `jamaica-marine-currents` folder, overwriting files. Do not remove the `.git` directory.
4. In Terminal, open the cloned repository folder and run:

```bash
python3 install_workflow.py
python3 -m unittest discover -s tests -v
git add -A
git commit -m "Deploy Jamaica Fishing Intelligence v3.8.42"
git push origin main
```

5. On GitHub, open `.github/workflows/currents.yml` and confirm it includes `contents: write`, `Restore persistent history`, `Save and verify persistent history`.
6. Run **Actions → Generate Jamaica currents map → Run workflow**. Check the restore, save and verification logs. Run it a second time to verify that history is restored.

**Important:** `github-workflows/currents.yml` is a visible master copy. GitHub executes only `.github/workflows/currents.yml`. If you edit the visible master later, rerun `python3 install_workflow.py` and commit both files.

The workflow may need repository **Settings → Actions → General → Workflow permissions → Read and write permissions**. GitHub policies can override requested permissions.
