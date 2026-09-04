"""End-to-end NEXUS pipeline for Phases 1-2 (detection + scoring + eval).

Reusable by the FastAPI layer later:
  run_detection(world) -> (clusters, world_index)
  build_training_set(world) -> (feats, labels, cluster_labels)
"""
from __future__ import annotations
from dataclasses import asdict

from nexus.schema import World
from nexus.graph.loader import load_world
from nexus.graph.entity_graph import EntityGraphBuilder, ClusterDetector, Cluster
from nexus.ml.features import extract_features, WorldIndex
from nexus.ml.labeling import label_cluster, ClusterLabel


def run_detection(world: World):
    G = EntityGraphBuilder(world).build()
    clusters = ClusterDetector(G, world).detect()
    return clusters, WorldIndex(world), G


def build_training_set(world: World):
    clusters, widx, _ = run_detection(world)
    feats, labels, clabels = [], [], []
    for c in clusters:
        feats.append(extract_features(c, widx))
        cl = label_cluster(c, world)
        labels.append(cl.is_ring)
        clabels.append(cl)
    return clusters, feats, labels, clabels
