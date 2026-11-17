from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config
from pydantic import BaseModel
import requests
import os

app = FastAPI(
    title="Kubernetes MCP Server",
    description="AI agents access to kubernetes cluster",
    version="2.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Use Service account
config.load_incluster_config()

v1 = client.CoreV1Api()
apps =  client.AppsV1Api()

class HealthResponse(BaseModel):
    status: str

class NodeResponse(BaseModel):
    name: str

class PodResponse(BaseModel):
    namespace: str
    name: str
    phase: str

class UnhealthyPodResponse(BaseModel):
    namespace: str
    pod: str
    reason: str

class DeploymentResponse(BaseModel):
    namespace: str
    name: str
    ready: int
    desired: int

class EventResponse(BaseModel):
    namespace: str
    resource: str
    reason: str
    message: str

class StatusSummary(BaseModel):
    running: int
    failed: int
    total: int

class ArgoCDApp(BaseModel):
    name: str
    sync: str
    health: str

class ClusterSummary(BaseModel):
    nodes: int
    pods: int
    unhealthyPods: int
    argocdDegraded: int
    argocdOutOfSync: int



@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}

@app.get("/pods", response_model=list[PodResponse])
def pods():
    result = []

    for pod in v1.list_pod_for_all_namespaces().items:
        result.append({
            "namespace": pod.metadata.namespace,
            "name": pod.metadata.name,
            "phase": pod.status.phase
        })

    return result

@app.get("/pods/unhealthy", response_model=list[UnhealthyPodResponse])
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


@app.get("/nodes", response_model=list[NodeResponse])
def nodes():
    result = []

    for node in v1.list_node().items:
        result.append({
            "name": node.metadata.name
        })

    return result

@app.get("/deployments", response_model=list[DeploymentResponse])
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


@app.get("/events", response_model=list[EventResponse])
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


@app.get("/falco/status", response_model=StatusSummary)
def falco_status():

    pods = v1.list_namespaced_pod("falco")

    running = 0
    failed = 0


    for pod in pods.items:
        if pod.status.phase == "Running":
           running += 1
        else:
           failed += 1

    return {
        "running": running,
        "failed": failed,
        "total": len(pods.items)
        }

@app.get("/ceph/health", response_model=StatusSummary)
def ceph_health():

    pods = v1.list_namespaced_pod("rook-ceph")

    running = 0
    failed = 0


    for pod in pods.items:
        if pod.status.phase == "Running":
           running += 1
        else:
           failed += 1

    return {
        "running": running,
        "failed": failed,
        "total": len(pods.items)
        }

@app.get("/argocd/apps", response_model=list[ArgoCDApp])
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


@app.get("/cluster/summary", response_model=ClusterSummary)
def cluster_summary():

    nodes = len(v1.list_node().items)

    pods = v1.list_pod_for_all_namespaces().items

    unhealthy = 0


    for pod in pods:

        if pod.status.phase != "Running":
           unhealthy += 1


    custom_api = client.CustomObjectsApi()

    apps = custom_api.list_namespaced_custom_object(
         "argoproj.io",
         "v1alpha1",
         "argocd",
         "applications"
    )

    out_of_sync = 0
    degraded = 0

    for app_item in apps["items"]:

         sync_status = app_item["status"]["sync"]["status"]

         health_status = app_item["status"]["health"]["status"]


         if sync_status != "Synced":
           out_of_sync += 1

         if health_status != "Healthy":
           degrade += 1


    return {
        "nodes": nodes,
        "pods": len(pods),
        "unhealthyPods": unhealthy,
        "argocdDegraded": degraded,
        "argocdOutOfSync": out_of_sync

        }
