# GitHub Environments for CI/CD

## `gcr` environment

Used by the **Build and Push to GCR** workflow to push Docker images to Google Container Registry.

### 1. Create the environment (if needed)

1. In your repo: **Settings** → **Environments** → **New environment**
2. Name it: **`gcr`** (must match `environment: gcr` in the workflow)
3. Optionally add protection rules (e.g. required reviewers, wait timer)

### 2. Add required secrets to the `gcr` environment

Go to **Settings** → **Environments** → **gcr** → **Environment secrets** and add:

| Secret name       | Description |
|------------------|-------------|
| `GCP_PROJECT_ID` | Your Google Cloud project ID (e.g. `my-project-123`) |
| `GCP_SA_KEY`     | Service account key JSON (full contents of the key file) |

**Creating a service account key for GCR:**

1. In [Google Cloud Console](https://console.cloud.google.com/): **IAM & Admin** → **Service Accounts**
2. Create or select a service account
3. Grant role: **Storage Admin** (or **Artifact Registry Admin** if using Artifact Registry)
4. **Keys** → **Add key** → **Create new key** → **JSON**
5. Copy the entire JSON and paste it as the value of the `GCP_SA_KEY` secret

### 3. Optional: use repository secrets instead

You can also set **Repository secrets** (Settings → Secrets and variables → Actions) with the same names (`GCP_PROJECT_ID`, `GCP_SA_KEY`). The workflow will use environment secrets first when the job has `environment: gcr`; if you only use repo secrets, the job will still run as long as the `gcr` environment exists (or remove `environment: gcr` from the workflow).
