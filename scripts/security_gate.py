"""Bloqueia vulnerabilidades HIGH/CRITICAL com correcao disponivel."""
import json
import sys
from collections import Counter
from pathlib import Path


def summarize(report):
    if report.get("SchemaVersion") != 2 or not isinstance(report.get("Results"), list):
        raise ValueError("Relatorio Trivy ausente ou invalido")
    counts = Counter()
    blocked = []
    for result in report["Results"]:
        for vulnerability in result.get("Vulnerabilities") or []:
            severity = vulnerability.get("Severity", "UNKNOWN")
            counts[severity] += 1
            if severity in ("HIGH", "CRITICAL") and vulnerability.get("FixedVersion"):
                blocked.append({"id": vulnerability["VulnerabilityID"],
                                "package": vulnerability["PkgName"],
                                "severity": severity, "fixed": vulnerability["FixedVersion"]})
    return {"counts": dict(counts), "blocked": blocked,
            "policy": "HIGH e CRITICAL com correcao disponivel bloqueiam a entrega"}


if __name__ == "__main__":
    result = summarize(json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(1 if result["blocked"] else 0)
