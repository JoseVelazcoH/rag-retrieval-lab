# Runbook: Pods that keep restarting

## Symptom

The `CrashLoopBackOff` status appears in `kubectl get pods`.

## Steps

Read the logs of the previous container with `kubectl logs --previous`.
Check `kubectl describe pod` and look for the reason of the last
termination. An `OOMKilled` means the memory limit is too low.

## Probes

If the container starts fine but Kubernetes restarts it, the
`livenessProbe` is too strict. Increase `initialDelaySeconds`
for applications with a slow start. A container that crashes only
on the first request usually needs a readiness probe instead.
