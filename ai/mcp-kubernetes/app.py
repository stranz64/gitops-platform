from fastapi import Fastapi
from kubernetes import client, config

app = FastAPI(title="Kubernetes MCP Server")

# Use Service account
config.load_incluster_config()

v1 = client.CoreV1Api()
apps =  client.AppsV1Api()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/pods")
def pods():
    result = []

    for pod in v1.list_pod_for_all_namespaces().items:
        result.append({
            "namespace": pod.metadata.namespace,
            "name": pod.metadata.name,
            "phase": pod.status.phase
        })

    return result

@app.get("/nodes")
def nodes():
    result = []

    for node in v1.list_node().items:
        result.append({
            "name": node.metadata.name
        })

    return result

@app.get("/deployments")
def deployments():
    result = []

    for deploy in apps.list_deployment_for_all_namespaces().items:
        result.append({
            "namespace": deploy.metadata.namespace,
            "name": deploy.metadata.name,
            "ready": deploy.status.ready_replicas or 0,
            "desired": deploy.spec.replicas
        })

    return result
