from fastapi import FastAPI
from kubernetes import client, config
import requests
import os

app = FastAPI(
    title="Kubernetes MCP Server",
    description="AI agents access to kubernetes cluster",
    version="2.0"
)

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

@app.get("/pods/unhealthy")
def unhealthy_pods():
    result = []

    for pod in v1.list_pod_for_all_namespaces().items:

        if pod.status.phase != "Running":

            result.append({
                "namespace": pod.metadata.namespace,
                "pod": pod.metadata.name,
                "phase": pod.status.phase
            })

        if pod.status.container_statuses:

            for c in pod.status.container_statuses:

                if c.state.waiting:

                   result.append({
                       "namespace": pod.metadata.namespace,
                       "pod": pod.metadata.name,
                       "container": c.name,
                       "reason": c.state.waiting.reason

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


@app.get("/events")
def events():
    result = []

    events = v1.list_event_for_all_namespaces()

    for event in events.items[:50]:
        result.append({
            "namespace": event.metadata.namespace,
            "resource": event.involved_object.name,
            "reason": event.reason,
            "message": event.message
        })

    return result


@app.get("/falco/status")
def falco_status():

    pods = v1.list_namespaced_pod("falco")

    result = []


    for pod in pods.items:
        result.append({
            "name": pod.metadata.name,
            "phase": pod.status.phase

        })

    return result


@app.get("/ceph/health")
def ceph_health():

    pods = v1.list_namespaced_pod("rook-ceph")

    result = []


    for pod in pods.items:
        result.append({
            "name": pod.metadata.name,
            "phase": pod.status.phase 

        })

    return result



@app.get("/argocd/apps")
def argocd_apps():

    custom_api = client.CustomObjectsApi()

    apps = custom_api.list_cluster_custom_object(
         group="argoproj.io",
         version="v1alpha1",
         plural="applications"
    )

    result = []


    for app_item in apps["items"]:
        result.append({
            "name": app_item["metadata"]["name"],
            "health": app_item["status"]["health"]["status"],
            "sync": app_item["status"]["sync"]["status"] 

        })

    return result


@app.get("/wazuh/agents")
def wazuh_agents():


    return {
         "message":
         "Implement API Integration"
    }
