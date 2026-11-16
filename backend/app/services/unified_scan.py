"""One upload door for the three scanners.

``execute_unified_scan`` takes the bytes a visitor uploaded plus the ``kind``
they chose (``spec`` / ``deps`` / ``code``), writes them into a temporary
directory, calls the existing engine, normalises the findings and persists the
scan and its findings.

The engines are NOT refactored here: both accept a path (file or directory) and
that is exactly what they are given. This module is the adapter.

Archive handling is deliberately strict, because an uploaded zip is
untrusted input:

* absolute paths, ``..`` components and symlink entries are rejected (422)
* more than 10 000 entries, or an overall compression ratio above 100:1, is
  rejected (422)
* a single entry larger than 2 MB is rejected (422)
* only the allowed extensions are scanned, at most 200 files, at most 2 MB each
* if those caps truncate the work the response says ``partial: true``
* nothing is ever opened outside the temporary directory
"""

from __future__ import annotations

import io
import os
import posixpath
import stat
import tempfile
import zipfile
from pathlib import PurePosixPath

from sqlalchemy.orm import Session

from app.core.dep_scanner.scanner import run_dep_scan
from app.core.risk_engine.scorer import calculate_risk_score
from app.core.sast_engine.scanner import run_sast_scan
from app.models.models import Scan
from app.repositories.findings import FindingRepository
from app.repositories.scans import ScanRepository
from app.services.audit_service import record_scan_event
from app.services.finding_normalizer import (
    dedupe_findings,
    normalize_dep,
    normalize_sast,
    strip_internal,
)
from app.services.risk_engine import compute_risk_assessment
from app.utils.logger import logger

SPEC_KIND = "spec"
DEPS_KIND = "deps"
CODE_KIND = "code"
VALID_KINDS = (SPEC_KIND, DEPS_KIND, CODE_KIND)

# What each kind may be uploaded as. Order is what the 422 message lists.
ALLOWED_EXTENSIONS: dict[str, tuple[str, ...]] = {
    SPEC_KIND: (".json", ".yaml", ".yml"),
    DEPS_KIND: (".txt", ".json", ".xml", ".zip"),
    CODE_KIND: (".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php", ".zip"),
}

# What gets scanned once an archive is open.
SCANNABLE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    # A dependency archive may contain several manifests side by side.
    DEPS_KIND: (".txt", ".json", ".xml", ".in", ".lock"),
    CODE_KIND: (".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php"),
}

MAX_ARCHIVE_ENTRIES = 10_000
MAX_COMPRESSION_RATIO = 100.0
MAX_ENTRY_BYTES = 2 * 1024 * 1024
MAX_SCAN_FILES = 200
MAX_FILE_BYTES = 2 * 1024 * 1024


class UploadRejected(Exception):
    """Upload that must be answered with a 4xx instead of a 500."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def allowed_extensions_message(kind: str) -> str:
    return ", ".join(ALLOWED_EXTENSIONS[kind])


def validate_kind(kind: str) -> str:
    normalized = (kind or SPEC_KIND).strip().lower()
    if normalized not in VALID_KINDS:
        raise UploadRejected(
            422,
            f"Invalid kind '{kind}'. Allowed: {', '.join(VALID_KINDS)}",
        )
    return normalized


def validate_filename(kind: str, filename: str | None) -> str:
    """Reject an extension that does not belong to the chosen kind."""
    if not filename:
        raise UploadRejected(422, "No file provided")
    lowered = filename.lower()
    if not lowered.endswith(ALLOWED_EXTENSIONS[kind]):
        raise UploadRejected(
            422,
            f"Invalid file type for kind '{kind}'. Allowed: " f"{allowed_extensions_message(kind)}",
        )
    return filename


def _reject_unsafe_entry(name: str) -> None:
    """Raise if an archive entry name could escape the extraction directory."""
    if not name or name.endswith("/"):
        return
    normalized = name.replace("\\", "/")
    if posixpath.isabs(normalized) or PurePosixPath(normalized).is_absolute():
        raise UploadRejected(422, "archive rejected: absolute path entry")
    if normalized.startswith("~"):
        raise UploadRejected(422, "archive rejected: absolute path entry")
    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        raise UploadRejected(422, "archive rejected: path traversal entry")
    # Windows drive letter, e.g. "C:/windows/system32"
    if len(normalized) > 1 and normalized[1] == ":":
        raise UploadRejected(422, "archive rejected: absolute path entry")


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def _safe_target(dest_dir: str, name: str) -> str:
    """Resolve an entry name inside ``dest_dir`` and prove it stays there."""
    target = os.path.realpath(os.path.join(dest_dir, name.replace("\\", "/")))
    root = os.path.realpath(dest_dir)
    if target != root and not target.startswith(root + os.sep):
        raise UploadRejected(422, "archive rejected: path traversal entry")
    return target


def extract_archive_safely(data: bytes, dest_dir: str, kind: str) -> tuple[list[str], bool, int]:
    """Extract ``data`` into ``dest_dir``.

    Returns ``(written_paths, partial, eligible_count)``. ``partial`` is True
    when the per-scan caps stopped us before every eligible file was written;
    ``eligible_count`` is how many entries passed the extension filter, so the
    caller can say exactly how much of the archive was left unscanned.
    """
    extensions = SCANNABLE_EXTENSIONS[kind]
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise UploadRejected(422, "archive rejected: not a valid zip file") from None

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise UploadRejected(
                422,
                f"archive rejected: {len(infos)} entries exceeds the "
                f"{MAX_ARCHIVE_ENTRIES} entry limit",
            )

        uncompressed = sum(i.file_size for i in infos)
        compressed = sum(i.compress_size for i in infos) or 1
        if uncompressed / compressed > MAX_COMPRESSION_RATIO:
            raise UploadRejected(
                422,
                "archive rejected: compression ratio "
                f"{uncompressed / compressed:.0f}:1 exceeds {MAX_COMPRESSION_RATIO:.0f}:1",
            )

        eligible = sum(
            1 for info in infos if not info.is_dir() and info.filename.lower().endswith(extensions)
        )
        written: list[str] = []
        partial = False
        for info in infos:
            if info.is_dir():
                continue
            _reject_unsafe_entry(info.filename)
            if _is_symlink(info):
                raise UploadRejected(422, "archive rejected: symlink entry")
            if info.file_size > MAX_ENTRY_BYTES:
                raise UploadRejected(
                    422,
                    f"archive rejected: entry '{info.filename}' is larger than "
                    f"{MAX_ENTRY_BYTES // (1024 * 1024)} MB",
                )
            if not info.filename.lower().endswith(extensions):
                continue
            if len(written) >= MAX_SCAN_FILES:
                partial = True
                break

            target = _safe_target(dest_dir, info.filename)
            os.makedirs(os.path.dirname(target) or dest_dir, exist_ok=True)
            with archive.open(info) as src, open(target, "wb") as dst:
                payload = src.read(MAX_FILE_BYTES + 1)
                if len(payload) > MAX_FILE_BYTES:
                    raise UploadRejected(
                        422,
                        f"archive rejected: entry '{info.filename}' exceeds "
                        f"{MAX_FILE_BYTES // (1024 * 1024)} MB",
                    )
                dst.write(payload)
            written.append(target)

    if not written:
        raise UploadRejected(
            422,
            f"archive rejected: no scannable file found " f"(allowed: {', '.join(extensions)})",
        )
    return written, partial, eligible


def _write_upload(filename: str, data: bytes, dest_dir: str) -> str:
    """Write a single (non-archive) upload into ``dest_dir`` and return its path."""
    base = os.path.basename(filename.replace("\\", "/"))
    if not base or base in {".", ".."}:
        raise UploadRejected(422, "Invalid file name")
    target = os.path.realpath(os.path.join(dest_dir, base))
    if not target.startswith(os.path.realpath(dest_dir) + os.sep):
        raise UploadRejected(422, "Invalid file name")
    with open(target, "wb") as handle:
        handle.write(data)
    return target


def _relative_to_root(path: str, root: str) -> str:
    """Return ``path`` relative to ``root``, or ``path`` when it cannot be.

    The SAST engine reports absolute paths inside the temporary extraction
    directory. Those host paths must not reach the API response, the UI or the
    PDF report: a client should read ``app.py:9``, not the analyst's temp folder.
    """
    if not path:
        return path
    try:
        relative = os.path.relpath(os.path.abspath(path), os.path.abspath(root))
    except ValueError:  # different drive on Windows
        return path
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return path
    return relative.replace(os.sep, "/")


def _run_engine(kind: str, target: str, root: str) -> list[dict]:
    """Call the existing engine and return normalized, deduped finding dicts."""
    if kind == DEPS_KIND:
        result = run_dep_scan(target)
        normalized = [normalize_dep(f.to_dict()) for f in result.findings]
    elif kind == CODE_KIND:
        sast_result = run_sast_scan(target)
        normalized = []
        for finding in sast_result.findings:
            raw = dict(finding.to_dict())
            raw["file_path"] = _relative_to_root(str(raw.get("file_path") or ""), root)
            normalized.append(normalize_sast(raw))
    else:  # pragma: no cover - guarded by validate_kind
        raise UploadRejected(422, f"Unsupported kind '{kind}'")

    return dedupe_findings(normalized)


def execute_unified_scan(
    db: Session,
    user_id: int,
    kind: str,
    filename: str,
    data: bytes,
) -> tuple[Scan, bool]:
    """Run one scan of ``kind`` over an uploaded file and persist the result.

    Returns the persisted Scan and whether the work was truncated (``partial``).
    """
    kind = validate_kind(kind)
    validate_filename(kind, filename)

    scan_repo = ScanRepository(db)
    finding_repo = FindingRepository(db)

    partial = False
    files_scanned = 1
    files_eligible = 1
    with tempfile.TemporaryDirectory(prefix="sentinelai_upload_") as workdir:
        if filename.lower().endswith(".zip"):
            files, partial, files_eligible = extract_archive_safely(data, workdir, kind)
            files_scanned = len(files)
            target: str = workdir
            logger.info("Unified %s scan: %d files from %s", kind, len(files), filename)
        else:
            target = _write_upload(filename, data, workdir)

        findings = _run_engine(kind, target, workdir)

    scan = scan_repo.create_scan(
        user_id=user_id,
        api_name=filename,
        source_spec={
            "kind": kind,
            "filename": filename,
            "partial": partial,
            "files_scanned": files_scanned,
            "files_eligible": files_eligible,
        },
    )
    scan.kind = kind
    scan_repo.add(scan)
    db.commit()
    db.refresh(scan)

    record_scan_event(
        db,
        "scan.started",
        user_id=user_id,
        scan_id=scan.id,
        detail={"kind": kind, "filename": filename},
    )
    db.commit()

    try:
        # Full dicts to storage and risk engine; only the AI prompt is trimmed.
        finding_repo.bulk_add_from_scan(scan.id, [strip_internal(f) for f in findings])
        risk = calculate_risk_score(findings)
        try:
            assessment = compute_risk_assessment(findings)
            risk["security_grade"] = assessment.security_grade
            risk["confidence_score"] = assessment.confidence_score
            risk["priority"] = assessment.priority
            risk["top_cwes"] = assessment.top_cwes
            risk["top_owasp"] = assessment.top_owasp
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Risk assessment failed for scan %s: %s", scan.id, exc)

        scan_repo.complete(scan, risk, scan.transition_history)
        scan.status = "completed"
        from datetime import UTC, datetime

        scan.completed_at = datetime.now(UTC)
        db.commit()

        record_scan_event(
            db,
            "scan.completed",
            user_id=user_id,
            scan_id=scan.id,
            detail={
                "kind": kind,
                "total_vulnerabilities": risk["total_vulnerabilities"],
                "risk_score": risk["score"],
            },
        )
        db.commit()
        logger.info(
            "Unified %s scan %s completed: %d findings",
            kind,
            scan.id,
            len(findings),
        )
    except Exception as exc:
        db.rollback()
        logger.error("Unified %s scan %s failed: %s", kind, scan.id, exc)
        scan_repo.fail(scan)
        db.commit()
        raise

    return scan, partial
