"""
Quick API connectivity checker for the LLM Evaluation platform.

Usage (examples):
  python api_connectivity_check.py                         # run safe GET checks
  python api_connectivity_check.py --run-create            # include light write ops with temp files
  python api_connectivity_check.py --qa-task-id abc123     # also probe QA task/status endpoints
  python api_connectivity_check.py --base-url http://127.0.0.1:8000/api

Notes:
- Only minimal, low-impact requests run by default (mostly GET).
- Write operations (upload/create) are executed only when --run-create is set.
- Optional IDs enable deeper checks for specific tasks/projects/questionnaires.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


def shorten(obj: Any, length: int = 320) -> str:
    try:
        payload = json.dumps(obj, ensure_ascii=False)
    except Exception:
        payload = str(obj)
    return textwrap.shorten(payload, width=length, placeholder=" ...")


def format_response(resp: requests.Response) -> str:
    try:
        body = resp.json()
    except Exception:
        body = resp.text.strip()
    return shorten(body)


def run_request(
    session: requests.Session,
    base_url: str,
    name: str,
    method: str,
    path: str,
    *,
    timeout: float,
    **kwargs: Any,
) -> Tuple[bool, Dict[str, Any]]:
    url = base_url.rstrip("/") + path
    started = time.time()
    try:
        resp = session.request(method, url, timeout=timeout, **kwargs)
        ok = resp.ok
        detail = {
            "status_code": resp.status_code,
            "duration_ms": round((time.time() - started) * 1000, 1),
            "preview": format_response(resp),
        }
        return ok, detail
    except Exception as exc:
        return False, {
            "status_code": None,
            "duration_ms": round((time.time() - started) * 1000, 1),
            "preview": f"{type(exc).__name__}: {exc}",
        }


def load_file(path: Optional[str]) -> Optional[Tuple[str, bytes]]:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return file_path.name, file_path.read_bytes()


def build_tests(args: argparse.Namespace) -> List[Dict[str, Any]]:
    tests: List[Dict[str, Any]] = []

    def add(name: str, method: str, path: str, *, run: bool = True, **kwargs: Any) -> None:
        if run:
            tests.append({"name": name, "method": method, "path": path, "kwargs": kwargs})

    # Safe, read-only checks
    add("Health", "GET", "/health")
    add("Upload allowed types", "GET", "/upload/allowed-types")
    add("QA stats", "GET", "/qa/stats")
    add("QA tasks", "GET", "/qa/tasks/all")
    add("Eval stats", "GET", "/eval/stats")
    add("Eval tasks", "GET", "/eval/tasks")
    add("Eval models", "GET", "/eval/models")
    add("Eval files", "GET", "/eval/files")
    add("Eval history", "GET", "/eval/history")
    add("FLMM stats", "GET", "/flmm/stats")
    add("FLMM questionnaire structure", "GET", "/flmm/structure/questionnaire")
    add("FLMM evidence structure", "GET", "/flmm/structure/evidence")
    add("FLMM projects", "GET", "/flmm/projects")
    add("FLMM questionnaires", "GET", "/flmm/questionnaires")
    add("FLMM analysis projects", "GET", "/flmm/analysis/projects")

    # ID-based optional checks
    add(
        "QA task detail",
        "GET",
        f"/qa/task/{args.qa_task_id}",
        run=bool(args.qa_task_id),
    )
    add(
        "QA preview",
        "GET",
        f"/qa/preview/{args.qa_task_id}?limit=5",
        run=bool(args.qa_task_id),
    )
    add(
        "QA evaluate-task",
        "POST",
        "/qa/evaluate-task",
        run=bool(args.qa_task_id),
        json={
          "source_task_id": args.qa_task_id,
          "min_factual_score": 7,
          "min_overall_score": 7,
          "sample_percentage": 100,
        },
    )

    add(
        "Eval task detail",
        "GET",
        f"/eval/task/{args.eval_task_id}",
        run=bool(args.eval_task_id),
    )
    add(
        "Eval results",
        "GET",
        f"/eval/results/{args.eval_task_id}",
        run=bool(args.eval_task_id),
    )
    add(
        "Eval downloads metadata",
        "GET",
        f"/eval/downloads/{args.eval_task_id}",
        run=bool(args.eval_task_id),
    )

    add(
        "FLMM project detail",
        "GET",
        f"/flmm/project/{args.project_id}",
        run=bool(args.project_id),
    )
    add(
        "FLMM questionnaire detail",
        "GET",
        f"/flmm/questionnaire/{args.questionnaire_id}",
        run=bool(args.questionnaire_id),
    )
    add(
        "FLMM project statistics",
        "GET",
        f"/flmm/analysis/project/{args.project_folder}/statistics",
        run=bool(args.project_folder),
    )
    add(
        "FLMM project questions",
        "GET",
        f"/flmm/analysis/project/{args.project_folder}/questions",
        run=bool(args.project_folder),
    )
    add(
        "FLMM project ratings",
        "GET",
        f"/flmm/analysis/project/{args.project_folder}/ratings",
        run=bool(args.project_folder),
    )

    # Write operations (opt-in)
    if args.run_create:
        # Generic upload with provided file or a small temp fallback
        file_single = load_file(args.upload_file)
        if not file_single:
            temp_name = "api_check_placeholder.txt"
            file_single = (temp_name, b"api connectivity smoke test\n")

        add(
            "Upload single file",
            "POST",
            "/upload/file",
            files={"file": file_single},
        )
        add(
            "Upload multiple files",
            "POST",
            "/upload/files",
            files={
                "files": [
                    file_single,
                    (file_single[0].replace(".", "_2."), file_single[1]),
                ]
            },
        )

        # QA generate (lightweight) if a file is available
        qa_file = load_file(args.qa_file) or file_single
        add(
            "QA generate",
            "POST",
            "/qa/generate?num_pairs_per_section=3&use_suggested_count=false&include_reason=false"
            "&suggest_qa_count=false&min_density_score=5&min_quality_score=5"
            "&skip_extract=false&skip_evaluate=false&skip_qa=false&skip_qa_evaluate=false"
            "&min_factual_score=7&min_overall_score=7&qa_sample_percentage=100",
            files={"files": qa_file},
        )

        # Eval upload (if a file is provided)
        if args.eval_upload_file:
            eval_file = load_file(args.eval_upload_file)
            if eval_file:
                add(
                    "Eval upload",
                    "POST",
                    "/eval/upload",
                    files={"files": eval_file},
                )

        # Eval create task using server-side file paths if provided
        if args.eval_create_paths:
            form_data = {
                "llm_name": args.eval_llm_name or "api-check-llm",
                "evaluation_type": args.evaluation_type or "both",
                "description": "API connectivity quick test",
                "file_paths": json.dumps(args.eval_create_paths),
                "stage1_answer_threshold": "70",
                "stage1_reasoning_threshold": "70",
                "stage2_answer_threshold": "70",
                "stage2_reasoning_threshold": "70",
                "evaluation_rounds": "1",
            }
            add(
                "Eval create task",
                "POST",
                "/eval/create",
                data=form_data,
            )

        # FLMM: create questionnaire and project with minimal payloads
        add(
            "FLMM create questionnaire",
            "POST",
            "/flmm/questionnaire",
            json={
                "title": "API连通性测试问卷",
                "description": "Automatically created for connectivity check",
                "questions": [
                    {
                        "question_id": "q1",
                        "question_text": "连通性测试问题",
                        "question_type": "text",
                        "required": True,
                    }
                ],
            },
        )
        add(
            "FLMM create project",
            "POST",
            "/flmm/project/create",
            json={
                "company_name": "API测试公司",
                "scenario_name": "连通性检查",
                "scenario_description": "触发API创建以验证写接口可用",
                "functions_list": [{"name": "示例功能", "description": "仅供测试"}],
                "selected_questionnaire_items": [],
                "selected_evidence_items": [],
                "enable_questionnaire": False,
                "enable_evidence": False,
                "auto_generate_account": True,
            },
        )

    return tests


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="API connectivity smoke tester")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/api",
        help="Backend base URL (default: http://localhost:8000/api)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout seconds")

    # Optional IDs for deeper checks
    parser.add_argument("--qa-task-id", default="", help="Existing QA task id for detail/preview/evaluate checks")
    parser.add_argument("--eval-task-id", default="", help="Existing eval task id for detail/results/download checks")
    parser.add_argument("--project-id", default="", help="Existing FLMM project id")
    parser.add_argument("--project-folder", default="", help="Existing FLMM project folder name")
    parser.add_argument("--questionnaire-id", default="", help="Existing FLMM questionnaire id")

    # Optional files and create toggles
    parser.add_argument("--run-create", action="store_true", help="Execute write/create endpoints with placeholder data")
    parser.add_argument("--upload-file", default="", help="Local file for generic upload tests")
    parser.add_argument("--qa-file", default="", help="Local file for QA generate test")
    parser.add_argument("--eval-upload-file", default="", help="Local file for eval upload test")
    parser.add_argument(
        "--eval-create-paths",
        nargs="+",
        help="Server-side file paths for eval create task (e.g., data/evaluation/uploads/demo.xlsx)",
    )
    parser.add_argument("--eval-llm-name", default="api-check-llm", help="LLM name used for eval create task")
    parser.add_argument("--evaluation-type", default="both", help="Evaluation type for eval create task")

    args = parser.parse_args(argv)

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    tests = build_tests(args)
    results: List[Tuple[str, bool, Dict[str, Any]]] = []

    print(f"Base URL: {args.base_url}")
    print(f"Running {len(tests)} checks (create endpoints {'enabled' if args.run_create else 'disabled'})\n")

    for test in tests:
        name = test["name"]
        method = test["method"]
        path = test["path"]
        kwargs = test["kwargs"]
        ok, detail = run_request(
            session,
            args.base_url,
            name,
            method,
            path,
            timeout=args.timeout,
            **kwargs,
        )
        status = "OK" if ok else "FAIL"
        results.append((name, ok, detail))
        print(f"[{status:4}] {name:32} {method} {path}  -> {detail['status_code']} ({detail['duration_ms']} ms)")
        print(f"       preview: {detail['preview']}")

    total = len(results)
    passed = sum(1 for (_, ok, _) in results if ok)
    failed = total - passed
    print("\nSummary")
    print(f"  Passed: {passed}/{total}")
    if failed:
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name} failed ({detail['status_code']}): {detail['preview']}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
