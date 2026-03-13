# Air‑Gapped Deployment for IBM Project AI Services with OCI‑Packaged Models

This version expands the design in four key ways:

1.  **Create OCI‑compatible model images for every model in each AI‑Services application template.**
2.  **Enable external route for the OpenShift internal registry** so we can push images from an external machine into the isolated cluster.
3.  **Create a dedicated OpenShift user with cluster-admin** so we can generate an authentication token for Podman/Skopeo pushes.
4.  **Push model and runtime images into the internal registry** following a reproducible and secure workflow.

# 1. Creating OCI‑Compatible Images for All Models per Application

### 🎯 Goal

For each **application template** packaged in a given release of *IBM Project AI Services*, build a complete **set of OCI‑compliant model images**, one per model, and version them according to the AI‑Services release.

### ✔ Recommended Approach

### **A. Build standard OCI container images for all models**

OCI images are natively supported by OpenShift, Podman, and standard registries. Using containers for models avoids special tooling and aligns with Kubernetes pull semantics.

This aligns with OCI image specification support for container registries.   
It also matches established practice of storing artifacts (models, configs) in OCI registries. [\[oneuptime.com\]](https://oneuptime.com/blog/post/2025-12-08-oci-artifacts-explained/view) [\[oras.land\]](https://oras.land/docs/concepts/artifact/)

### **B. Automation suggestion**

Create a `Makefile` or GitHub Actions workflow inside the `IBM/project-ai-services` repo that:

    models/
      modelA/
         weights/
         config.json
         Dockerfile.model
      modelB/
      ...
    templates/
      app1/
        models.txt
      app2/
        models.txt

Then generate images:

```bash
make build-model-images APP=app1 VERSION=1.2.0
```

Resulting images (example):

    <registry>/ai-services/app1-modelA:1.2.0
    <registry>/ai-services/app1-modelB:1.2.0

All are **OCI-compliant** and can be pushed into the OpenShift internal registry.

# **2. OpenShift – Enable External Route for Internal Image Registry**

OpenShift allows exposing the built‑in registry via a route.  
This is documented in OpenShift registry configuration:  
✔ Exposing the registry by enabling the defaultRoute is the supported method.   
✔ This is also referenced in post‑install steps for air‑gapped clusters. [\[all.docs.genesys.com\]](https://all.docs.genesys.com/PrivateEdition/Current/PEGuide/OCR) [\[kubernetes.day\]](https://kubernetes.day/openshift-4-19-day2-airgapped-disconnected-cluster-post-installation-steps/)

### **Command**

```bash
oc patch configs.imageregistry.operator.openshift.io/cluster \
  --type merge \
  -p '{"spec":{"defaultRoute":true}}'
```

Retrieve the public hostname:

```bash
REGISTRY=$(oc get route default-route -n openshift-image-registry \
  -o jsonpath='{.spec.host}')
echo $REGISTRY
```

Example result:

    default-route-openshift-image-registry.apps.ocp.mycompany.com

***

# **3. Create a User with cluster-admin for Secure Registry Login**

To push images using Podman/Skopeo from your **local machine**, you need an OpenShift token.  
The correct roles for pushing are **registry-editor** or full **cluster-admin**.  
OpenShift explicitly documents registry role requirements. [\[docs.redhat.com\]](https://docs.redhat.com/en/documentation/openshift_container_platform/4.9/html/registry/accessing-the-registry)

### **A. Create a new service account**

```bash
oc create sa ai-registry-pusher -n openshift-image-registry
```

### **B. Grant cluster-admin**

```bash
oc adm policy add-cluster-role-to-user cluster-admin \
  -z ai-registry-pusher -n openshift-image-registry
```

### **C. Retrieve token**

```bash
TOKEN=$(oc sa get-token ai-registry-pusher -n openshift-image-registry)
echo $TOKEN
```

### **D. Podman login**

```bash
podman login -u ai-registry-pusher -p $TOKEN \
  $REGISTRY
```

This pattern is supported—OpenShift registry login uses OAuth tokens for authentication. [\[cookbook.o...nshift.org\]](https://cookbook.openshift.org/image-registry-and-image-streams/how-do-i-push-an-image-to-the-internal-image-registry.html)

# **4. Push the OCI Model Images into the Internal Registry**

Once the registry is exposed and you can authenticate, push the model images.

### **A. Tag image for the internal registry**

```bash
podman tag app1-modelA:1.2.0 \
  $REGISTRY/ai-services/app1-modelA:1.2.0
```

### **B. Push**

```bash
podman push $REGISTRY/ai-services/app1-modelA:1.2.0
```

This workflow matches OpenShift‑documented internal registry usage via Podman/Docker push.    [\[cookbook.o...nshift.org\]](https://cookbook.openshift.org/image-registry-and-image-streams/how-do-i-push-an-image-to-the-internal-image-registry.html)

### **C. (Optional) Create imagestreams**

```bash
oc new-project ai-services
oc create imagestream app1-modelA
```

***

# **📦 End‑to‑End Build & Push Workflow (Summary)**

### **Step 1 — Build OCI model images**

```bash
podman build -t app1-modelA:1.2.0 -f Dockerfile.model .
```

### **Step 2 — Enable internal registry route**

```bash
oc patch configs.imageregistry.operator.openshift.io/cluster \
  --type merge -p '{"spec":{"defaultRoute":true}}'
```

### **Step 3 — Create cluster-admin pusher**

```bash
oc create sa ai-registry-pusher -n openshift-image-registry
oc adm policy add-cluster-role-to-user cluster-admin \
  -z ai-registry-pusher -n openshift-image-registry
TOKEN=$(oc sa get-token ai-registry-pusher -n openshift-image-registry)
```

### **Step 4 — Podman login & push**

```bash
podman login -u ai-registry-pusher -p $TOKEN $REGISTRY
podman tag app1-modelA:1.2.0 $REGISTRY/ai-services/app1-modelA:1.2.0
podman push $REGISTRY/ai-services/app1-modelA:1.2.0
```

***

# Want me to produce:

✅ A **scripted automation bundle (Makefile + build scripts + YAML)** for all these steps?  
✅ A **GitHub Actions pipeline** that automatically builds OCI model images per release and prepares air‑gap export bundles?  
Or both?

Just tell me your preferred format.
