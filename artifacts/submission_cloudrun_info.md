# NAOMI Cloud Run Submission Info

## Open Source Repository URL

```text
https://github.com/ユーザー名/naomi-human-adaptive-ai
```

Replace `ユーザー名` after the GitHub repository is created.

## Hosted Project URL

```text
https://xxxxx.run.app
```

Replace this with the Cloud Run service URL after deployment.

Expected service:

```text
naomi
```

Expected region:

```text
asia-northeast1
```

## Google Cloud Products Used

If Gemini API is configured in production:

```text
Google Cloud Run
Google Cloud Build
Google Cloud Artifact Registry
Google Gemini API / Google AI Studio
```

If Gemini API is not configured for the submitted demo:

```text
Google Cloud Run
Google Cloud Build
Google Cloud Artifact Registry

The prototype is designed to support Gemini API integration, with fallback behavior when no API key is configured.
```

## Other Tools / Products Used

```text
Python
Streamlit
GitHub
Docker
Generative AI
Prompt Engineering
Human-Adaptive interaction design
```

## Cloud Run Deploy Command

Recommended fastest path when a Cloud Build image already exists:

```powershell
$PROJECT_ID = "naomi-rapid-agent"
$REGION = "asia-northeast1"
$BUILD_ID = "3ffb3006-4ea4-4caf-946f-c64f2cded033"

gcloud builds describe $BUILD_ID `
  --region=$REGION `
  --format="json(results.images,images,substitutions)"
```

Copy the built image name or digest from the output, then deploy that image directly:

```powershell
$IMAGE = "asia-northeast1-docker.pkg.dev/naomi-rapid-agent/cloud-run-source-deploy/IMAGE_NAME_OR_DIGEST"

gcloud run deploy naomi `
  --image=$IMAGE `
  --region=$REGION `
  --allow-unauthenticated `
  --memory=2Gi `
  --cpu=1 `
  --max-instances=2 `
  --port=8080
```

This avoids `gcloud run deploy --source .` entirely, so the local Windows file scanning / source deploy path is not used.

If the build describe output does not clearly show the image, list the images in the source deploy repository and use the newest one:

```powershell
gcloud artifacts docker images list `
  asia-northeast1-docker.pkg.dev/naomi-rapid-agent/cloud-run-source-deploy `
  --include-tags `
  --sort-by="~UPDATE_TIME" `
  --limit=10
```

Use the full `IMAGE` or digest value from that list with `gcloud run deploy --image`.

If `--image=...:latest` also fails with `Container import failed`, avoid mutable tags and deploy the exact digest:

```powershell
$PROJECT_ID = "naomi-rapid-agent"
$REGION = "asia-northeast1"
$REPO = "cloud-run-source-deploy"
$IMAGE_NAME = "naomi"

gcloud artifacts docker images list `
  "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE_NAME" `
  --include-tags `
  --sort-by="~UPDATE_TIME" `
  --limit=5

$IMAGE_DIGEST = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE_NAME@sha256:PASTE_DIGEST_HERE"

gcloud run deploy naomi `
  --image=$IMAGE_DIGEST `
  --region=$REGION `
  --allow-unauthenticated `
  --memory=2Gi `
  --cpu=1 `
  --max-instances=2 `
  --port=8080 `
  --project=$PROJECT_ID
```

Also grant Artifact Registry Reader at the repository level, not only the project level:

```powershell
$PROJECT_ID = "naomi-rapid-agent"
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
$REGION = "asia-northeast1"
$REPO = "cloud-run-source-deploy"

gcloud artifacts repositories add-iam-policy-binding $REPO `
  --location=$REGION `
  --project=$PROJECT_ID `
  --member="serviceAccount:service-$PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com" `
  --role="roles/artifactregistry.reader"

gcloud artifacts repositories add-iam-policy-binding $REPO `
  --location=$REGION `
  --project=$PROJECT_ID `
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
  --role="roles/artifactregistry.reader"
```

To inspect the control-plane failure:

```powershell
gcloud run revisions describe naomi-00002-64h `
  --region=asia-northeast1 `
  --project=naomi-rapid-agent `
  --format="yaml(metadata.name,metadata.annotations,status.conditions,status.imageDigest,spec.containers)"

gcloud logging read `
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"naomi\" AND resource.labels.revision_name=\"naomi-00002-64h\"" `
  --project=naomi-rapid-agent `
  --limit=50 `
  --format="value(timestamp,severity,textPayload,jsonPayload.message,protoPayload.status.message)"
```

If asia-northeast1 continues to fail at image import, create a clean Artifact Registry repository in us-central1 and deploy from there. The safest path is Cloud Shell or another Linux environment so Windows gcloud local scanning is bypassed.

```bash
PROJECT_ID=naomi-rapid-agent
REGION=us-central1
REPO=naomi-cloudrun
IMAGE=naomi

gcloud config set project $PROJECT_ID
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="NAOMI Cloud Run images" || true

gcloud builds submit \
  --tag "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE:latest" \
  --region=$REGION

gcloud run deploy naomi \
  --image="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE:latest" \
  --region=$REGION \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=1 \
  --max-instances=2 \
  --port=8080
```

If Docker is available locally, another option is to retag/push the existing image into a clean repository:

```powershell
$PROJECT_ID = "naomi-rapid-agent"
gcloud auth configure-docker us-central1-docker.pkg.dev

docker pull asia-northeast1-docker.pkg.dev/naomi-rapid-agent/cloud-run-source-deploy/naomi:latest
docker tag asia-northeast1-docker.pkg.dev/naomi-rapid-agent/cloud-run-source-deploy/naomi:latest us-central1-docker.pkg.dev/naomi-rapid-agent/naomi-cloudrun/naomi:latest
docker push us-central1-docker.pkg.dev/naomi-rapid-agent/naomi-cloudrun/naomi:latest

gcloud run deploy naomi `
  --image=us-central1-docker.pkg.dev/naomi-rapid-agent/naomi-cloudrun/naomi:latest `
  --region=us-central1 `
  --allow-unauthenticated `
  --memory=2Gi `
  --cpu=1 `
  --max-instances=2 `
  --port=8080 `
  --project=$PROJECT_ID
```

Source deploy command, only if the Windows `--source` crash is resolved:

```bash
gcloud run deploy naomi \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 2
```

If deployment fails with `Container import failed` while Cloud Build is `SUCCESS`, inspect the failed revision and Artifact Registry image:

```bash
gcloud run services describe naomi --region asia-northeast1
gcloud run revisions list --service naomi --region asia-northeast1
gcloud run revisions describe REVISION_NAME --region asia-northeast1
gcloud artifacts repositories list --location=asia-northeast1
gcloud artifacts docker images list asia-northeast1-docker.pkg.dev/naomi-rapid-agent/cloud-run-source-deploy
```

If Cloud Run cannot import or pull the image, grant Artifact Registry Reader to the Cloud Run service agent and Compute default service account:

```bash
PROJECT_ID=naomi-rapid-agent
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

PowerShell equivalent:

```powershell
$PROJECT_ID = "naomi-rapid-agent"
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:service-$PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com" `
  --role="roles/artifactregistry.reader"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
  --role="roles/artifactregistry.reader"
```

Then redeploy:

```bash
gcloud run deploy naomi \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --max-instances 2
```

Fallback region:

```bash
gcloud run deploy naomi \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 2
```

## Safety Note

NAOMI is not a diagnosis tool. It is a state-organization and low-pressure communication assistant. It does not provide medical diagnosis, treatment instructions, or clinical assessment.
