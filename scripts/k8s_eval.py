"""Kubernetes structure experiment with the original bge model.

Thin wrapper kept for compatibility: runs structure_eval.py --corpus k8s --model bge.
Output: results/structure-k8s-bge.json (formerly k8s-structure.json).
Usage: k8s_eval.py
"""
from structure_eval import main

if __name__ == "__main__":
    main(["--corpus", "k8s", "--model", "bge"])
