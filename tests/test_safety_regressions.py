"""Regression checks for HMAC tamper detection, API and standalone browser asset."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from agents.base import AuditTrail
from agents.api import index, api_audit_logs
from agents.models import SystemTaskPayload
from agents.llm_factory import LLMFactory


def test_audit_verifies_signatures_not_only_links():
    trail = AuditTrail(secret_key="unit-test-secret")
    trail.log("supervisor", "system", "evaluation", {"result": "safe"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "tampered"
    assert not trail.verify_integrity()


def test_audit_returns_defensive_copies():
    trail = AuditTrail(secret_key="unit-test-secret")
    trail.log("supervisor", "system", "evaluation", {"result": "safe"})
    leaked = trail.get_trail()
    leaked[0]["actor"] = "tampered"
    assert trail.verify_integrity()


def test_audit_logs_not_public_by_default(monkeypatch):
    monkeypatch.delenv("DIGOXIN_AUDIT_ADMIN_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        api_audit_logs(x_audit_key=None)
    assert exc.value.status_code == 403


def test_payload_disallows_nonfinite_metrics():
    with pytest.raises(ValidationError):
        SystemTaskPayload(
            task_id="TEST", target_identifier="PSEUDONYM",
            primary_metric=float("nan")
        )


def test_unimplemented_model_provider_is_not_silently_mocked():
    with pytest.raises(ValueError):
        LLMFactory.create("nonexistent-provider")


def test_static_calculator_exists_and_server_uses_it():
    path = Path(index().path)
    assert path.exists()
    page = path.read_text(encoding="utf-8")
    assert 'id="calculator"' in page
    assert 'id="result-css"' in page
    assert 'fetch("/api/audit"' not in page
    assert "HMAC_SHA256_e83f9" not in page


class _ScriptCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script = []
        self.inside = False

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.inside = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.script.append(data)


def test_embedded_javascript_is_valid():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    collector = _ScriptCollector()
    collector.feed(Path(index().path).read_text(encoding="utf-8"))
    assert collector.script
    checked = subprocess.run(
        [node, "--check", "-"], input="\n".join(collector.script),
        text=True, capture_output=True, check=False
    )
    assert checked.returncode == 0, checked.stderr
